You are an expert Python NLP engineer. Your task is to implement the chunking 
module for JusticeCongo AI — a RAG-based French legal aid assistant built on 
the LEGANET.CD corpus. The chunker reads raw legal text from the PostgreSQL 
legal_documents table and produces article-level chunks stored in the 
document_chunks table.

═══════════════════════════════════════════════════════════
ENVIRONMENT
═══════════════════════════════════════════════════════════

Runtime: Python venv on Apple Silicon Mac (arm64)
Database: PostgreSQL + pgvector running in Docker
Connection string: postgresql://justicecongo:justicecongo_dev@localhost:5432/justicecongo

Install these packages into the venv:
  pip install psycopg2-binary spacy
  python -m spacy download fr_core_news_sm

DO NOT install torch, transformers, or sentence-transformers here.
Those are for the embedder in the next step.

═══════════════════════════════════════════════════════════
CONTEXT: WHAT EXISTS
═══════════════════════════════════════════════════════════

The legal_documents table is already populated. Each row has:
  id            UUID
  raw_text      TEXT    ← full cleaned French legal text, UTF-8
  title         TEXT
  domain        VARCHAR(50)
  doc_type      VARCHAR(30)
  date_enacted  DATE
  source_url    TEXT
  status        VARCHAR(20)  ← currently 'scraped' for all rows
  word_count    INTEGER

The document_chunks table exists and is empty. Its schema:
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid()
  document_id      UUID NOT NULL REFERENCES legal_documents(id) ON DELETE CASCADE
  chunk_index      INTEGER NOT NULL
  text             TEXT NOT NULL
  article_number   TEXT
  chapter_heading  TEXT
  section_heading  TEXT
  page_number      INTEGER
  token_count      INTEGER
  embedding        VECTOR(1024)   ← NULL until embedder runs
  embedding_model  VARCHAR(100)
  embedded_at      TIMESTAMPTZ
  metadata         JSONB NOT NULL DEFAULT '{}'
  created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
  UNIQUE (document_id, chunk_index)

═══════════════════════════════════════════════════════════
DELIVERABLES
═══════════════════════════════════════════════════════════

  pipeline/
  ├── __init__.py
  ├── chunker.py      ← main implementation
  ├── run_chunker.py  ← CLI entry point
  └── tests/
      ├── __init__.py
      └── test_chunker.py

═══════════════════════════════════════════════════════════
FILE: pipeline/chunker.py
═══════════════════════════════════════════════════════════

Implement the following, in order:

─────────────────────────────────────────
SECTION 1: Constants
─────────────────────────────────────────

ARTICLE_PATTERN = re.compile(
    r'(?:^|\n)\s*'
    r'(?:ARTICLE|Article|ART\.|Art\.)\s+'
    r'(premier|PREMIER|unique|UNIQUE|\d+|[IVXLCDM]{1,6})'
    r'(?:\s*[.:\-\—\s])',
    re.MULTILINE
)

CHAPTER_PATTERN = re.compile(
    r'(?:^|\n)\s*'
    r'(?:CHAPITRE|Chapitre|TITRE|Titre|PARTIE|Partie)\s+'
    r'([IVXLCDM]{1,6}|\d+)'
    r'(?:\s*[.:\-\—])?\s*(.{0,80})',
    re.MULTILINE
)

SECTION_PATTERN = re.compile(
    r'(?:^|\n)\s*'
    r'(?:SECTION|Section|Paragraphe|PARAGRAPHE)\s+'
    r'([IVXLCDM]{1,6}|\d+)'
    r'(?:\s*[.:\-\—])?\s*(.{0,80})',
    re.MULTILINE
)

MAX_CHUNK_TOKENS = 500    # Hard ceiling — chunks larger than this get split
OVERLAP_TOKENS   = 50     # Token overlap between sub-chunks of a split article
MIN_CHUNK_WORDS  = 10     # Chunks below this are too small — merged or skipped

─────────────────────────────────────────
SECTION 2: Dataclass
─────────────────────────────────────────

@dataclass
class Chunk:
    document_id:     str
    chunk_index:     int
    text:            str
    article_number:  str | None
    chapter_heading: str | None
    section_heading: str | None
    token_count:     int
    metadata:        dict

─────────────────────────────────────────
SECTION 3: Token counting (no transformers)
─────────────────────────────────────────

Implement:

  def count_tokens(text: str) -> int

Use a simple word-based approximation:
  - Split on whitespace
  - Multiply by 1.3 to account for subword tokenization overhead
  - Return as integer
  
This avoids loading a tokenizer just for counting. It is accurate 
enough for chunking decisions. The real token count from the 
embedding model will differ slightly but stays within safe margins.

─────────────────────────────────────────
SECTION 4: Structure detection
─────────────────────────────────────────

Implement:

  def extract_structure(text: str) -> dict

Scans the full document text once and returns:
{
  "article_positions": [
      {"match": re.Match, "number": str, "start": int, "end": int},
      ...
  ],
  "chapter_positions": [
      {"heading": str, "start": int},
      ...
  ],
  "section_positions": [
      {"heading": str, "start": int},
      ...
  ],
  "has_article_structure": bool  ← True if >= 2 articles found
}

For chapter_positions: concatenate CHAPTER_PATTERN group(1) + " — " + 
group(2).strip() as the heading string.

For section_positions: same pattern with SECTION_PATTERN.

─────────────────────────────────────────
SECTION 5: Context prefix
─────────────────────────────────────────

Implement:

  def build_context_prefix(prev_chunk_text: str | None) -> str

If prev_chunk_text is None: return ""

Otherwise:
  1. Split prev_chunk_text into sentences using a simple regex:
       re.split(r'(?<=[.!?;])\s+', prev_chunk_text)
  2. Take the last 2 sentences
  3. Return: "[Contexte: {last_2_sentences}]\n\n"

The prefix gives the embedding model awareness of definitions or 
context established in the previous article without duplicating 
the full prior chunk.

─────────────────────────────────────────
SECTION 6: Fixed-size fallback splitter
─────────────────────────────────────────

Implement:

  def split_by_tokens(
      text: str,
      max_tokens: int = MAX_CHUNK_TOKENS,
      overlap: int = OVERLAP_TOKENS
  ) -> list[str]

Used when:
  a) A document has no article structure (no ARTICLE_PATTERN matches)
  b) A single article is longer than MAX_CHUNK_TOKENS

Algorithm:
  1. Split text into words (text.split())
  2. Estimate words per chunk: max_words = int(max_tokens / 1.3)
  3. Estimate overlap in words: overlap_words = int(overlap / 1.3)
  4. Slide a window across the word list:
       start = 0
       while start < len(words):
           end = min(start + max_words, len(words))
           chunks.append(' '.join(words[start:end]))
           if end == len(words): break
           start = end - overlap_words
  5. Return list of text strings

─────────────────────────────────────────
SECTION 7: Main chunking function
─────────────────────────────────────────

Implement:

  def chunk_document(
      document_id: str,
      raw_text:    str,
      domain:      str,
      doc_type:    str
  ) -> list[Chunk]

Full algorithm:

STEP 1 — Detect structure:
  structure = extract_structure(raw_text)

STEP 2 — Choose chunking path:

  PATH A: Document has article structure
    (structure["has_article_structure"] is True)

    Iterate over article_positions with index i:

    a) Determine text span for this article:
         start = article_positions[i]["start"]
         end   = article_positions[i+1]["start"] if i+1 < len(...)
                 else len(raw_text)
         article_text = raw_text[start:end].strip()

    b) Find the active chapter_heading:
         The chapter whose start position is the largest value
         that is still <= this article's start position.
         If none: chapter_heading = None

    c) Find the active section_heading:
         Same logic as chapter but for section_positions.

    d) Check token count of article_text:
         If count_tokens(article_text) <= MAX_CHUNK_TOKENS:
           → Single chunk. Add context prefix from previous chunk.
             final_text = build_context_prefix(prev_text) + article_text
             Create one Chunk with:
               article_number  = article_positions[i]["number"]
               chapter_heading = (active chapter heading or None)
               section_heading = (active section heading or None)
               token_count     = count_tokens(article_text)
               metadata        = {"has_context_prefix": prev_text is not None,
                                  "domain": domain,
                                  "doc_type": doc_type}
         Else:
           → Article too long. Split with split_by_tokens(article_text).
             For each sub-chunk at index j:
               final_text = build_context_prefix(prev_text if j==0 else sub_chunks[j-1])
                            + sub_chunks[j]
               Create Chunk with:
                 article_number  = f"{article_number}.{j+1}"
                 (same chapter/section as parent article)
                 metadata["is_split"] = True
                 metadata["split_index"] = j

    e) Track prev_text = article_text (the original, without prefix)
       for the next iteration's context prefix.

    f) Skip any chunk where len(chunk.text.split()) < MIN_CHUNK_WORDS

  PATH B: Document has NO article structure
    (structure["has_article_structure"] is False)

    sub_texts = split_by_tokens(raw_text)
    For each sub_text at index i:
      Create Chunk with:
        article_number  = None
        chapter_heading = None
        section_heading = None
        token_count     = count_tokens(sub_text)
        metadata        = {"domain": domain, "doc_type": doc_type,
                           "no_article_structure": True}

STEP 3 — Assign sequential chunk_index values (0-based) across all
          chunks produced for this document.

STEP 4 — Return list[Chunk]

─────────────────────────────────────────
SECTION 8: Database operations
─────────────────────────────────────────

Implement:

  def get_documents_to_chunk(conn, batch_size: int = 50) -> list[dict]

    SELECT id, raw_text, domain, doc_type, title
    FROM legal_documents
    WHERE status = 'scraped'
      AND raw_text IS NOT NULL
      AND raw_text != ''
    ORDER BY scraped_at ASC
    LIMIT %s

    Returns list of dicts.

───

  def save_chunks(conn, chunks: list[Chunk]) -> int

    Uses psycopg2's execute_values for a single batch INSERT.
    
    INSERT INTO document_chunks
      (document_id, chunk_index, text, article_number,
       chapter_heading, section_heading, token_count, metadata)
    VALUES %s
    ON CONFLICT (document_id, chunk_index) DO UPDATE SET
      text            = EXCLUDED.text,
      article_number  = EXCLUDED.article_number,
      chapter_heading = EXCLUDED.chapter_heading,
      section_heading = EXCLUDED.section_heading,
      token_count     = EXCLUDED.token_count,
      metadata        = EXCLUDED.metadata

    Returns the number of rows inserted/updated.
    Commits after the batch.

───

  def mark_document_chunked(conn, document_id: str) -> None

    UPDATE legal_documents
    SET status = 'chunked', updated_at = NOW()
    WHERE id = %s

    Commits.

═══════════════════════════════════════════════════════════
FILE: pipeline/run_chunker.py
═══════════════════════════════════════════════════════════

CLI entry point. Implement:

  import argparse, logging, psycopg2, time
  from pipeline.chunker import (
      get_documents_to_chunk, chunk_document,
      save_chunks, mark_document_chunked
  )

  Configure logging:
    Level: INFO
    Format: "%(asctime)s [%(levelname)s] %(message)s"
    Handlers: StreamHandler + FileHandler("chunker.log")

  DB_CONN = "postgresql://justicecongo:justicecongo_dev@localhost:5432/justicecongo"

  def run(batch_size: int = 50, dry_run: bool = False):

    conn = psycopg2.connect(DB_CONN)

    total_docs     = 0
    total_chunks   = 0
    failed_docs    = 0
    no_structure   = 0

    while True:
      docs = get_documents_to_chunk(conn, batch_size)
      if not docs:
        break

      for doc in docs:
        try:
          t0 = time.time()
          chunks = chunk_document(
              document_id = doc['id'],
              raw_text    = doc['raw_text'],
              domain      = doc['domain'],
              doc_type    = doc['doc_type']
          )

          has_structure = any(
              not c.metadata.get('no_article_structure')
              for c in chunks
          )
          if not has_structure:
            no_structure += 1

          if not dry_run:
            saved = save_chunks(conn, chunks)
            mark_document_chunked(conn, doc['id'])
          else:
            saved = len(chunks)

          elapsed = (time.time() - t0) * 1000
          logging.info(
            f"[{'DRY' if dry_run else 'OK'}] {doc['title'][:50]!r} "
            f"→ {len(chunks)} chunks "
            f"({'no article structure' if not has_structure else 'article-level'}) "
            f"({elapsed:.0f}ms)"
          )

          total_docs   += 1
          total_chunks += len(chunks)

        except Exception as e:
          logging.error(f"FAILED: {doc['id']} — {doc['title'][:50]!r}: {e}")
          failed_docs += 1
          continue

    conn.close()

    logging.info("─" * 60)
    logging.info(f"Done. Documents: {total_docs} | Chunks: {total_chunks} | "
                 f"No-structure: {no_structure} | Failed: {failed_docs}")

  if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-size", type=int, default=50)
    parser.add_argument("--dry-run", action="store_true",
        help="Run chunking logic but do not write to the database")
    args = parser.parse_args()
    run(batch_size=args.batch_size, dry_run=args.dry_run)

═══════════════════════════════════════════════════════════
FILE: pipeline/tests/test_chunker.py
═══════════════════════════════════════════════════════════

Write pytest tests using ONLY the sample strings below.
No database connection, no file I/O in these tests.

SAMPLE_WITH_ARTICLES = """
CHAPITRE I — Des baux à loyer

Article 1: Le présent texte régit les baux à loyer des immeubles 
situés sur le territoire de la République Démocratique du Congo.

Article 2: Au sens du présent texte, on entend par bail à loyer, 
toute convention par laquelle une personne, le bailleur, s'oblige 
à procurer à une autre personne, le preneur, la jouissance d'un 
immeuble ou d'une partie d'immeuble moyennant un loyer.

CHAPITRE II — De la durée

Article 3: La durée du bail est fixée librement par les parties. 
À défaut de convention écrite, le bail est réputé conclu pour 
une durée indéterminée.

Article 4: Le bail à durée déterminée prend fin de plein droit 
à l'expiration du terme convenu, sans qu'il soit nécessaire 
de donner congé.
"""

SAMPLE_NO_ARTICLES = """
Les dispositions générales concernant la propriété foncière 
en République Démocratique du Congo sont régies par les textes 
suivants. La loi Bakajika établit le principe de la domanialité 
de toutes les terres. Les terres appartiennent à l'État.
"""

SAMPLE_LONG_ARTICLE = """
Article 1: """ + ("Ce texte est très long et contient de nombreuses dispositions. " * 40) + """

Article 2: Court article suivant.
"""

Tests to write (use assert statements, not unittest.TestCase):

  test_article_pattern_detects_french_markers():
    Test that ARTICLE_PATTERN matches all of:
      "Article 1:"
      "Article premier:"
      "Art. 12 —"
      "ARTICLE 15."
      "Article unique:"
    And does NOT match:
      "L'article 5 dispose que..."   ← mid-sentence, should not match
      "Article de presse"             ← not a legal article marker

  test_chunk_document_with_articles():
    chunks = chunk_document("test-id", SAMPLE_WITH_ARTICLES, "droit_civil", "loi")
    assert len(chunks) == 4
    assert chunks[0].article_number == "1"
    assert chunks[1].article_number == "2"
    assert chunks[2].chapter_heading is not None
    assert "CHAPITRE II" in chunks[2].chapter_heading or "II" in chunks[2].chapter_heading
    assert chunks[3].article_number == "4"
    assert all(c.document_id == "test-id" for c in chunks)
    assert all(c.chunk_index == i for i, c in enumerate(chunks))

  test_chunk_document_no_articles():
    chunks = chunk_document("test-id", SAMPLE_NO_ARTICLES, "general", "document")
    assert len(chunks) >= 1
    assert all(c.article_number is None for c in chunks)
    assert all(c.metadata.get("no_article_structure") for c in chunks)

  test_context_prefix_on_second_chunk():
    chunks = chunk_document("test-id", SAMPLE_WITH_ARTICLES, "droit_civil", "loi")
    assert chunks[0].metadata.get("has_context_prefix") == False
    assert chunks[1].metadata.get("has_context_prefix") == True
    assert "[Contexte:" in chunks[1].text

  test_long_article_is_split():
    chunks = chunk_document("test-id", SAMPLE_LONG_ARTICLE, "droit_civil", "loi")
    article_1_chunks = [c for c in chunks if c.article_number and c.article_number.startswith("1")]
    assert len(article_1_chunks) > 1
    assert all(c.metadata.get("is_split") for c in article_1_chunks)

  test_token_count_is_positive():
    chunks = chunk_document("test-id", SAMPLE_WITH_ARTICLES, "droit_civil", "loi")
    assert all(c.token_count > 0 for c in chunks)

  test_min_chunk_words_filter():
    tiny_text = "Article 1: Oui.\n\nArticle 2: " + ("mot " * 20)
    chunks = chunk_document("test-id", tiny_text, "droit_civil", "loi")
    assert all(len(c.text.split()) >= 10 for c in chunks)

═══════════════════════════════════════════════════════════
VALIDATION SEQUENCE
═══════════════════════════════════════════════════════════

Run these in order after implementation:

  # 1. Run tests (no DB needed)
  pytest pipeline/tests/test_chunker.py -v

  # 2. Dry run on real data (no DB writes)
  python pipeline/run_chunker.py --dry-run --batch-size 10

  # 3. Inspect dry-run log output
  # Expected lines like:
  # [DRY] 'Loi relative aux baux à loyer' → 47 chunks (article-level) (12ms)
  # [DRY] 'Décret du 20 juin 1960' → 8 chunks (no article structure) (3ms)

  # 4. Full run (writes to DB)
  python pipeline/run_chunker.py --batch-size 50

  # 5. Verify in PostgreSQL
  docker exec -it justicecongo_postgres psql \
    -U justicecongo -d justicecongo -c "
    SELECT
      COUNT(*)                                    AS total_chunks,
      COUNT(*) FILTER (WHERE article_number IS NOT NULL) AS with_articles,
      COUNT(*) FILTER (WHERE chapter_heading IS NOT NULL) AS with_chapters,
      AVG(token_count)::int                       AS avg_tokens
    FROM document_chunks;
  "

  # 6. Spot-check one document
  docker exec -it justicecongo_postgres psql \
    -U justicecongo -d justicecongo -c "
    SELECT chunk_index, article_number, chapter_heading,
           token_count, left(text, 80) AS preview
    FROM document_chunks
    WHERE document_id = (
      SELECT id FROM legal_documents
      WHERE status = 'chunked' LIMIT 1
    )
    ORDER BY chunk_index
    LIMIT 10;
  "

═══════════════════════════════════════════════════════════
APPLE SILICON NOTE
═══════════════════════════════════════════════════════════

spacy's fr_core_news_sm downloads an arm64-native wheel on Apple 
Silicon — no Rosetta issues. If sentence splitting with regex proves 
unreliable on edge cases, the build_context_prefix function may 
optionally use spacy's sentencizer instead:

  import spacy
  nlp = spacy.load("fr_core_news_sm", disable=["ner", "parser"])
  nlp.add_pipe("sentencizer")
  doc = nlp(text)
  sentences = [s.text for s in doc.sents]

But the regex approach (re.split on [.!?;]) is sufficient and 
faster for this use case. Use spacy only if you see garbled 
context prefixes during the dry run.

═══════════════════════════════════════════════════════════
WHAT NOT TO BUILD HERE
═══════════════════════════════════════════════════════════

Do NOT implement in this module:
  - Embedding generation (next step: pipeline/embedder.py)
  - Any FastAPI routes
  - Any Celery tasks
  - Zero-shot classification
  - The RAG pipeline

This module's only job:
  raw_text in legal_documents → structured chunks in document_chunks