import logging
import warnings
import json
import math
import psycopg2
from psycopg2.extras import RealDictCursor, execute_values
from pgvector.psycopg2 import register_vector

import torch
from sentence_transformers import SentenceTransformer

# Suppress harmless MPS float64 warning on Apple Silicon
warnings.filterwarnings("ignore", message=".*MPS.*float64.*")

logger = logging.getLogger(__name__)

# ─── Constants ────────────────────────────────────────────────────────────────
MODEL_NAME     = "intfloat/multilingual-e5-large"
VECTOR_DIM     = 1024
BATCH_SIZE     = 32       # Per model.encode() call — reduce to 16 if OOM
PASSAGE_PREFIX = "passage: "

# ─── Device selection ─────────────────────────────────────────────────────────
if torch.backends.mps.is_available():
    device = "mps"
elif torch.cuda.is_available():
    device = "cuda"
else:
    device = "cpu"

logger.info(f"Using device: {device}")

# --- model loading
_model = None

def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        logger.info(f"Loading {MODEL_NAME} on {device}...")
        _model = SentenceTransformer(MODEL_NAME, device=device)
        logger.info("Model loaded.")
    return _model


def embed_passages(texts: list[str]) ->list[list[float]]:
    if not texts:
        return []

    prefixed = [f"{PASSAGE_PREFIX}{t}" for t in texts]

    embeddings = get_model().encode(
        prefixed,
        batch_size = BATCH_SIZE,
        normalize_embeddings = True,
        show_progress_bar = False,
        convert_to_numpy=True
    )

    return embeddings.tolist()

def get_unembedded_chunks(conn, batch_size: int = 200) -> list[dict]:
    """
    Fetches chunks that haven't been embedded yet.
    WHERE embedding IS NULL makes this safe to resume after interruption.
    """
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT id, text
            FROM document_chunks
            WHERE embedding IS NULL
            ORDER BY created_at ASC
            LIMIT %s
        """, (batch_size,))
        return [dict(row) for row in cur.fetchall()]


def save_embeddings(
    conn,
    chunk_ids:  list[str],
    embeddings: list[list[float]],
    model_name: str = MODEL_NAME
) -> None:
    """
    Batch-updates the embedding column for a list of chunks.
    Converts embeddings to the '[x, y, z, ...]' string format
    that pgvector accepts via ::vector cast.
    """
    rows = [
        (str(cid), str(emb), model_name)
        for cid, emb in zip(chunk_ids, embeddings)
    ]

    with conn.cursor() as cur:
        execute_values(cur, """
            UPDATE document_chunks AS dc
            SET
                embedding       = data.embedding::vector,
                embedding_model = data.model,
                embedded_at     = NOW()
            FROM (VALUES %s) AS data(id, embedding, model)
            WHERE dc.id = data.id::uuid
        """, rows, template="(%s, %s, %s)", page_size=200)

    conn.commit()


def get_embedding_progress(conn) -> dict:
    """Returns current embedding progress stats."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT
                COUNT(*)                                      AS total_chunks,
                COUNT(*) FILTER (WHERE embedding IS NOT NULL) AS embedded_chunks,
                COUNT(*) FILTER (WHERE embedding IS NULL)     AS remaining_chunks
            FROM document_chunks
        """)
        return dict(cur.fetchone())

def embed_query(text: str) -> list[float]:
    """
    Embeds a single user question for retrieval.
    Uses 'query: ' prefix — distinct from 'passage: ' used for documents.
    This asymmetry is required by multilingual-e5-large.
    """
    embedding = get_model().encode(
        f"query: {text}",
        normalize_embeddings=True,
        convert_to_numpy=True,
    )
    return embedding.tolist()