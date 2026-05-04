You are an expert Python ML engineer. Your task is to implement the embedding 
generation pipeline for JusticeCongo AI — a RAG-based French legal aid assistant.

The chunker is already done. The document_chunks table is fully populated with 
text, article_number, chapter_heading, section_heading, token_count, and metadata.
The embedding column (VECTOR(1024)) exists but is NULL for all rows.

Your job: load every chunk, generate its embedding with 
intfloat/multilingual-e5-large, write it back to PostgreSQL, then create 
the HNSW and GIN indexes.

═══════════════════════════════════════════════════════════
ENVIRONMENT
═══════════════════════════════════════════════════════════

Runtime:  Python venv on Apple Silicon Mac (arm64)
Database: PostgreSQL + pgvector in Docker
Connection string:
  postgresql://justicecongo:justicecongo_dev@localhost:5432/justicecongo

Install these packages:
  pip install sentence-transformers torch psycopg2-binary pgvector

APPLE SILICON NOTE:
  PyTorch ships with MPS (Metal Performance Shaders) support for Apple 
  Silicon. The embedder must detect and use MPS when available — it gives 
  3–5x speedup over CPU for this model.

  Device selection logic (use exactly this):
    import torch
    if torch.backends.mps.is_available():
        device = "mps"
    elif torch.cuda.is_available():
        device = "cuda"
    else:
        device = "cpu"

  Known Apple Silicon issue: sentence-transformers may emit a warning about
  "MPS does not support float64" — this is harmless. Suppress it with:
    import warnings
    warnings.filterwarnings("ignore", message=".*MPS.*float64.*")

═══════════════════════════════════════════════════════════
DELIVERABLES
═══════════════════════════════════════════════════════════

  pipeline/
  ├── embedder.py        ← main implementation
  ├── run_embedder.py    ← CLI entry point
  └── tests/
      └── test_embedder.py

═══════════════════════════════════════════════════════════
FILE: pipeline/embedder.py
═══════════════════════════════════════════════════════════

─────────────────────────────────────────
SECTION 1: Constants
─────────────────────────────────────────

MODEL_NAME    = "intfloat/multilingual-e5-large"
VECTOR_DIM    = 1024       # multilingual-e5-large output dimension
BATCH_SIZE    = 32         # Chunks per model.encode() call
                           # Safe for 16GB unified memory on M1/M2/M3
                           # Reduce to 16 if you see OOM errors
PASSAGE_PREFIX = "passage: "
  # CRITICAL: multilingual-e5 requires this prefix on all documents
  # to be indexed. Queries use "query: " prefix (handled in retriever).
  # Omitting this prefix silently degrades retrieval quality by ~15-20%.

─────────────────────────────────────────
SECTION 2: Model loader (singleton)
─────────────────────────────────────────

Implement a module-level singleton pattern:

  _model = None

  def get_model() -> SentenceTransformer:
      global _model
      if _model is None:
          logger.info(f"Loading {MODEL_NAME} on device: {device}")
          _model = SentenceTransformer(MODEL_NAME, device=device)
          logger.info("Model loaded successfully")
      return _model

Why singleton: the model is ~2GB. Loading it once per process and 
reusing it is critical. Never instantiate SentenceTransformer() 
inside a loop or per-batch function.

─────────────────────────────────────────
SECTION 3: Core embedding function
─────────────────────────────────────────

Implement:

  def embed_passages(texts: list[str]) -> list[list[float]]

Algorithm:
  1. Prepend PASSAGE_PREFIX to every text:
       prefixed = [f"{PASSAGE_PREFIX}{t}" for t in texts]

  2. Call model.encode() with these exact parameters:
       embeddings = get_model().encode(
           prefixed,
           batch_size=BATCH_SIZE,
           normalize_embeddings=True,
           show_progress_bar=False,
           convert_to_numpy=True,
       )
     
     normalize_embeddings=True is mandatory:
       - Normalizes each vector to unit length (L2 norm = 1)
       - This makes cosine similarity equivalent to dot product
       - pgvector's <=> operator (cosine distance) requires this
       - Without normalization, similarity scores are meaningless

  3. Convert to Python list of lists:
       return embeddings.tolist()

  4. Wrap the entire function in try/except:
       On exception: log the error and raise (do not silently return 
       empty — a failed batch must halt the pipeline so you can fix it)

─────────────────────────────────────────
SECTION 4: Database fetch function
─────────────────────────────────────────

Implement:

  def get_unembedded_chunks(
      conn,
      batch_size: int = 200
  ) -> list[dict]

  SELECT id, text
  FROM document_chunks
  WHERE embedding IS NULL
  ORDER BY created_at ASC
  LIMIT %s

  Returns list of dicts with keys: id (str), text (str)

  Why ORDER BY created_at ASC:
    Processes documents in ingestion order. If the pipeline is 
    interrupted and restarted, it picks up where it left off because 
    already-embedded chunks are excluded by WHERE embedding IS NULL.

─────────────────────────────────────────
SECTION 5: Database write function
─────────────────────────────────────────

Implement:

  def save_embeddings(
      conn,
      chunk_ids:  list[str],
      embeddings: list[list[float]],
      model_name: str = MODEL_NAME
  ) -> None

  Use psycopg2's execute_values for a single batch UPDATE.

  The pgvector Python adapter requires registering the vector type.
  Do this ONCE when the connection is first used:
    from pgvector.psycopg2 import register_vector
    register_vector(conn)

  SQL:
    UPDATE document_chunks AS dc
    SET
      embedding       = data.embedding::vector,
      embedding_model = %s,
      embedded_at     = NOW()
    FROM (VALUES %s) AS data(id, embedding)
    WHERE dc.id = data.id::uuid

  Build the values list as:
    [(str(chunk_id), str(embedding)) for chunk_id, embedding
     in zip(chunk_ids, embeddings)]

  Why convert embedding to str: pgvector accepts the array literal 
  format '[0.1, 0.2, ...]' as a string and casts it via ::vector.
  This avoids needing a custom psycopg2 adapter for lists.

  Commit after each batch. Never batch across multiple commits — if 
  a write fails, you want to know exactly which batch failed.

─────────────────────────────────────────
SECTION 6: Progress tracking
─────────────────────────────────────────

Implement:

  def get_embedding_progress(conn) -> dict

  Run this single query:
    SELECT
      COUNT(*)                                      AS total_chunks,
      COUNT(*) FILTER (WHERE embedding IS NOT NULL) AS embedded_chunks,
      COUNT(*) FILTER (WHERE embedding IS NULL)     AS remaining_chunks,
      MIN(embedded_at)                              AS first_embedded_at,
      MAX(embedded_at)                              AS last_embedded_at
    FROM document_chunks

  Return as dict. Used by run_embedder.py to show progress on startup
  and to print a final summary.

═══════════════════════════════════════════════════════════
FILE: pipeline/run_embedder.py
═══════════════════════════════════════════════════════════

Implement:

  import argparse, logging, time, psycopg2
  from pgvector.psycopg2 import register_vector
  from pipeline.embedder import (
      get_model, get_unembedded_chunks,
      embed_passages, save_embeddings,
      get_embedding_progress, BATCH_SIZE
  )

  DB_CONN = "postgresql://justicecongo:justicecongo_dev@localhost:5432/justicecongo"

  Configure logging:
    Level: INFO
    Format: "%(asctime)s [%(levelname)s] %(message)s"
    Handlers: StreamHandler + FileHandler("embedder.log")

  def run(batch_size: int = 200, dry_run: bool = False):

    conn = psycopg2.connect(DB_CONN)
    register_vector(conn)   ← must be called before any vector operations

    # Show starting state
    progress = get_embedding_progress(conn)
    logger.info(
        f"Starting: {progress['embedded_chunks']} / "
        f"{progress['total_chunks']} chunks already embedded. "
        f"{progress['remaining_chunks']} remaining."
    )

    if progress['remaining_chunks'] == 0:
        logger.info("All chunks already embedded. Nothing to do.")
        conn.close()
        return

    # Force model load before the loop (avoid loading mid-run)
    get_model()

    total_embedded = 0
    batch_num      = 0
    start_time     = time.time()

    while True:
        chunks = get_unembedded_chunks(conn, batch_size)
        if not chunks:
            break

        batch_num += 1
        ids   = [c['id']   for c in chunks]
        texts = [c['text'] for c in chunks]

        t0 = time.time()
        embeddings = embed_passages(texts)
        encode_ms  = int((time.time() - t0) * 1000)

        if not dry_run:
            t1 = time.time()
            save_embeddings(conn, ids, embeddings)
            write_ms = int((time.time() - t1) * 1000)
        else:
            write_ms = 0

        total_embedded += len(chunks)
        throughput      = len(chunks) / max((time.time() - t0), 0.001)

        logger.info(
            f"Batch {batch_num}: {len(chunks)} chunks | "
            f"encode={encode_ms}ms | write={write_ms}ms | "
            f"{throughput:.1f} chunks/sec"
            + (" [DRY RUN]" if dry_run else "")
        )

    elapsed = time.time() - start_time
    logger.info(
        f"Done. Embedded {total_embedded} chunks in {elapsed:.1f}s "
        f"({total_embedded / max(elapsed, 1):.1f} chunks/sec overall)"
    )

    # Final state
    progress = get_embedding_progress(conn)
    logger.info(
        f"DB state: {progress['embedded_chunks']} / "
        f"{progress['total_chunks']} chunks embedded."
    )

    conn.close()

  if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-size", type=int, default=200,
        help="Chunks per DB fetch (not per model.encode call)")
    parser.add_argument("--dry-run", action="store_true",
        help="Generate embeddings but do not write to database")
    args = parser.parse_args()
    run(batch_size=args.batch_size, dry_run=args.dry_run)

═══════════════════════════════════════════════════════════
FILE: pipeline/tests/test_embedder.py
═══════════════════════════════════════════════════════════

Write pytest tests. No database connection required.
The model WILL be loaded for embedding tests — this is intentional.
Mark slow tests with @pytest.mark.slow.

  SAMPLE_TEXTS = [
      "Le bailleur est tenu de délivrer la chose louée en bon état.",
      "Tout locataire peut résilier le bail avec un préavis de trois mois.",
      "L'expulsion ne peut avoir lieu sans décision judiciaire préalable.",
  ]

  test_passage_prefix_applied():
    # Verify prefix logic without calling the model
    from pipeline.embedder import PASSAGE_PREFIX
    texts = ["test"]
    prefixed = [f"{PASSAGE_PREFIX}{t}" for t in texts]
    assert prefixed[0] == "passage: test"

  @pytest.mark.slow
  test_embed_passages_returns_correct_shape():
    embeddings = embed_passages(SAMPLE_TEXTS)
    assert len(embeddings) == 3
    assert len(embeddings[0]) == 1024   # VECTOR_DIM
    assert len(embeddings[1]) == 1024
    assert len(embeddings[2]) == 1024

  @pytest.mark.slow
  test_embeddings_are_normalized():
    import math
    embeddings = embed_passages(SAMPLE_TEXTS)
    for emb in embeddings:
        norm = math.sqrt(sum(x ** 2 for x in emb))
        assert abs(norm - 1.0) < 1e-4, f"Embedding not normalized: norm={norm}"

  @pytest.mark.slow
  test_similar_texts_have_higher_similarity():
    import numpy as np
    texts = [
        "Le locataire doit payer le loyer chaque mois.",
        "Le preneur est tenu de verser le loyer mensuellement.",  # Similar
        "La procédure pénale est régie par le code pénal.",       # Different
    ]
    embs = embed_passages(texts)
    a, b, c = [np.array(e) for e in embs]
    sim_similar  = float(np.dot(a, b))   # Should be high (same concept)
    sim_different = float(np.dot(a, c))  # Should be lower
    assert sim_similar > sim_different, (
        f"Expected similar texts to score higher: "
        f"sim_similar={sim_similar:.4f}, sim_different={sim_different:.4f}"
    )

  @pytest.mark.slow
  test_empty_list_returns_empty():
    result = embed_passages([])
    assert result == []

═══════════════════════════════════════════════════════════
FILE: db/create_indexes.sql
═══════════════════════════════════════════════════════════

Create this file separately. Run it AFTER all embeddings are populated.

Reason: HNSW builds a static graph over existing vectors. Building it 
on a partially-filled table produces a suboptimal index. Always embed 
first, index after.

-- ─── 1. HNSW index for semantic search ──────────────────────────────────────
-- Enables fast approximate nearest neighbor search via pgvector's <=> operator.
-- m=16: connections per node (higher = better recall, more memory)
-- ef_construction=64: search depth at build time (higher = better recall, slower build)
-- These are the standard recommended values for corpora under 1M vectors.
CREATE INDEX IF NOT EXISTS idx_chunks_embedding_hnsw
ON document_chunks
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- ─── 2. GIN index for French full-text search (BM25) ─────────────────────────
-- Enables: WHERE to_tsvector('french', text) @@ plainto_tsquery('french', $1)
-- PostgreSQL's built-in French dictionary handles:
--   - Stopwords: le, la, les, de, du, des, un, une, et, en...
--   - Stemming:  loyer→louer, expulsion→expuls, résiliation→résili...
-- This is what powers the keyword half of hybrid retrieval.
CREATE INDEX IF NOT EXISTS idx_chunks_fts_french
ON document_chunks
USING GIN (to_tsvector('french', text));

-- ─── 3. Supporting B-tree indexes ────────────────────────────────────────────
-- For filtering by domain/doc_type in hybrid search queries.
CREATE INDEX IF NOT EXISTS idx_chunks_document_id
ON document_chunks (document_id);

CREATE INDEX IF NOT EXISTS idx_chunks_embedded_at
ON document_chunks (embedded_at DESC)
WHERE embedded_at IS NOT NULL;

-- ─── 4. Verify indexes were created ──────────────────────────────────────────
-- Run this after the file to confirm:
-- SELECT indexname, indexdef FROM pg_indexes
-- WHERE tablename = 'document_chunks'
-- ORDER BY indexname;

═══════════════════════════════════════════════════════════
VALIDATION SEQUENCE
═══════════════════════════════════════════════════════════

Run in this exact order:

  # 1. Fast tests (no model load)
  pytest pipeline/tests/test_embedder.py -v -m "not slow"

  # 2. Full tests including model load (takes ~30s first run)
  pytest pipeline/tests/test_embedder.py -v

  # 3. Dry run — generates embeddings but does NOT write to DB
  #    Check that encode speed is reasonable (target: >20 chunks/sec on MPS)
  python pipeline/run_embedder.py --dry-run --batch-size 32

  # 4. Full embedding run
  #    Expected time: depends on corpus size
  #    At 30 chunks/sec on MPS: 10,000 chunks ≈ 5 min
  python pipeline/run_embedder.py --batch-size 200

  # 5. Create indexes (run AFTER embedding is complete)
  docker exec -it justicecongo_postgres psql \
    -U justicecongo -d justicecongo \
    -f /path/to/db/create_indexes.sql

  # Or directly:
  docker exec -it justicecongo_postgres psql \
    -U justicecongo -d justicecongo \
    -c "CREATE INDEX IF NOT EXISTS idx_chunks_embedding_hnsw
        ON document_chunks
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64);"

  docker exec -it justicecongo_postgres psql \
    -U justicecongo -d justicecongo \
    -c "CREATE INDEX IF NOT EXISTS idx_chunks_fts_french
        ON document_chunks
        USING GIN (to_tsvector('french', text));"

  # 6. Verify everything
  docker exec -it justicecongo_postgres psql \
    -U justicecongo -d justicecongo -c "
    SELECT
      COUNT(*)                                      AS total_chunks,
      COUNT(*) FILTER (WHERE embedding IS NOT NULL) AS embedded,
      COUNT(*) FILTER (WHERE embedding IS NULL)     AS missing,
      ROUND(AVG(token_count))                       AS avg_tokens
    FROM document_chunks;
  "

  # 7. Verify indexes exist
  docker exec -it justicecongo_postgres psql \
    -U justicecongo -d justicecongo -c "
    SELECT indexname FROM pg_indexes
    WHERE tablename = 'document_chunks'
    ORDER BY indexname;
  "

  # 8. Test semantic search actually works (run in psql)
  # Replace the vector below with a real one from your DB:
  docker exec -it justicecongo_postgres psql \
    -U justicecongo -d justicecongo -c "
    SELECT
      article_number,
      left(text, 100) AS preview,
      1 - (embedding <=> (
        SELECT embedding FROM document_chunks
        WHERE embedding IS NOT NULL LIMIT 1
      )) AS similarity
    FROM document_chunks
    WHERE embedding IS NOT NULL
    ORDER BY embedding <=> (
      SELECT embedding FROM document_chunks
      WHERE embedding IS NOT NULL LIMIT 1
    )
    LIMIT 5;
  "
  -- Expected: the first result is the chunk itself (similarity ≈ 1.0),
  -- followed by semantically related chunks.

═══════════════════════════════════════════════════════════
IMPORTANT NOTES
═══════════════════════════════════════════════════════════

1. PASSAGE PREFIX IS MANDATORY.
   intfloat/multilingual-e5-large was trained with asymmetric prefixes:
     Documents: "passage: {text}"
     Queries:   "query: {text}"
   Omitting the prefix on passages degrades retrieval quality silently.
   The run_embedder adds "passage: " here.
   The retriever (next step) will add "query: " to user questions.

2. NORMALIZE_EMBEDDINGS=TRUE IS MANDATORY.
   pgvector's <=> operator computes cosine distance.
   Cosine distance on unnormalized vectors gives wrong results.
   Always pass normalize_embeddings=True to model.encode().

3. IDEMPOTENT RUNS.
   WHERE embedding IS NULL in get_unembedded_chunks() means the 
   embedder is safe to stop and restart at any time. Already-embedded 
   chunks are skipped automatically.

4. INDEX AFTER EMBEDDING.
   Build the HNSW index only after all embeddings are written.
   Building incrementally on a live table works but produces a 
   less optimal graph structure than building once on the full dataset.

5. BATCH SIZE TUNING FOR APPLE SILICON.
   BATCH_SIZE=32 in model.encode() is the per-GPU-call batch.
   batch_size=200 in run_embedder is the per-DB-fetch batch.
   These are independent. If you see MPS out-of-memory errors,
   reduce BATCH_SIZE in embedder.py to 16.

6. WHAT NOT TO BUILD HERE.
   Do NOT implement in this module:
     - BM25 retrieval logic (next step: retriever.py)
     - Hybrid search (next step: retriever.py)
     - The RAG pipeline (pipeline.py)
     - Any FastAPI routes
   This module's only job:
     NULL embedding columns → populated VECTOR(1024) columns + indexes