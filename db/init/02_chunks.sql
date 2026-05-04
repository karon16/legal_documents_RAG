-- Table for document chunks and their embeddings
CREATE TABLE IF NOT EXISTS document_chunks (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id      UUID NOT NULL REFERENCES legal_documents(id) ON DELETE CASCADE,
  chunk_index      INTEGER NOT NULL,
  text             TEXT NOT NULL,
  article_number   TEXT,
  chapter_heading  TEXT,
  section_heading  TEXT,
  page_number      INTEGER,
  token_count      INTEGER,
  embedding        VECTOR(1024),
  embedding_model  VARCHAR(100) DEFAULT 'intfloat/multilingual-e5-large',
  embedded_at      TIMESTAMPTZ,
  metadata         JSONB NOT NULL DEFAULT '{}',
  created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(document_id, chunk_index)
);
