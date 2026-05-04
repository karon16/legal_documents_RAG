-- Table for document summaries
CREATE TABLE IF NOT EXISTS document_summaries (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id      UUID NOT NULL REFERENCES legal_documents(id) ON DELETE CASCADE,
  summary_type     VARCHAR(30) NOT NULL CHECK (summary_type IN ('executive', 'citizen', 'section', 'article')),
  summary_text     TEXT NOT NULL,
  target_article   TEXT,
  target_section   TEXT,
  model_used       VARCHAR(100),
  generated_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Table for legal templates
CREATE TABLE IF NOT EXISTS legal_templates (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id      UUID REFERENCES legal_documents(id) ON DELETE SET NULL,
  title            TEXT NOT NULL,
  template_type    VARCHAR(50),
  fields           JSONB NOT NULL DEFAULT '[]',
  template_text    TEXT,
  requires_notary  BOOLEAN NOT NULL DEFAULT FALSE,
  requires_stamp   BOOLEAN NOT NULL DEFAULT FALSE,
  disclaimer       TEXT NOT NULL DEFAULT 'Ce modèle est fourni à titre informatif uniquement. Consultez un avocat avant de signer tout document juridique.',
  created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Apply trigger for updated_at
DROP TRIGGER IF EXISTS update_legal_templates_updated_at ON legal_templates;
CREATE TRIGGER update_legal_templates_updated_at
BEFORE UPDATE ON legal_templates
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- Table for search logs (semantic search, not Q&A)
CREATE TABLE IF NOT EXISTS search_logs (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  query            TEXT NOT NULL,
  query_hash       VARCHAR(64) NOT NULL,
  filters_applied  JSONB NOT NULL DEFAULT '{}',
  result_count     INTEGER,
  top_document_ids UUID[],
  retrieval_ms     INTEGER,
  user_session     VARCHAR(100),
  created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Table for user feedback
CREATE TABLE IF NOT EXISTS user_feedback (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  qa_log_id        UUID NOT NULL REFERENCES qa_logs(id) ON DELETE CASCADE,
  rating           SMALLINT NOT NULL CHECK (rating IN (-1, 1)),
  comment          TEXT,
  flagged_reason   VARCHAR(50) CHECK (flagged_reason IN ('incorrect_law', 'wrong_article', 'not_found', 'unclear', 'outdated') OR flagged_reason IS NULL),
  created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
