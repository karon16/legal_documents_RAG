-- Table for chunk classifications (zero-shot mDeBERTa)
CREATE TABLE IF NOT EXISTS chunk_classifications (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  chunk_id            UUID NOT NULL UNIQUE REFERENCES document_chunks(id) ON DELETE CASCADE,
  domain_label        VARCHAR(80),
  domain_confidence   FLOAT CHECK (domain_confidence BETWEEN 0 AND 1),
  clause_type         VARCHAR(80),
  clause_confidence   FLOAT CHECK (clause_confidence BETWEEN 0 AND 1),
  risk_score          VARCHAR(20) CHECK (risk_score IN ('standard', 'unusual', 'potentially_adverse') OR risk_score IS NULL),
  classified_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  model_used          VARCHAR(100) DEFAULT 'MoritzLaurer/mDeBERTa-v3-base-mnli-xnli'
);

-- Table for Q&A logs
CREATE TABLE IF NOT EXISTS qa_logs (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  question         TEXT NOT NULL,
  question_hash    VARCHAR(64) NOT NULL,
  answer           TEXT,
  sources          JSONB NOT NULL DEFAULT '[]',
  domain_filter    VARCHAR(50),
  retrieval_count  INTEGER,
  was_cache_hit    BOOLEAN NOT NULL DEFAULT FALSE,
  retrieval_ms     INTEGER,
  generation_ms    INTEGER,
  model_used       VARCHAR(100),
  had_citations    BOOLEAN,
  user_session     VARCHAR(100),
  created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Table for chunk search cache
CREATE TABLE IF NOT EXISTS chunk_search_cache (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  question_hash    VARCHAR(64) NOT NULL UNIQUE,
  question         TEXT NOT NULL,
  top_chunk_ids    UUID[] NOT NULL,
  cached_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  expires_at       TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '6 hours')
);
