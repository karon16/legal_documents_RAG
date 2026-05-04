-- Create generic trigger function for updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Table for legal documents (scraper output)
CREATE TABLE IF NOT EXISTS legal_documents (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source_url      TEXT UNIQUE NOT NULL,
  title           TEXT,
  domain          VARCHAR(50) CHECK (domain IN (
    'droit_civil', 'droit_penal', 'droit_commercial', 'droit_fiscal', 
    'droit_du_travail', 'droit_public', 'droit_social', 'jurisprudence', 
    'doctrine', 'journal_officiel', 'modeles', 'general'
  )),
  doc_type        VARCHAR(30) CHECK (doc_type IN (
    'loi', 'decret', 'arrete', 'ordonnance', 'jurisprudence', 
    'doctrine', 'modele', 'document'
  )),
  date_enacted    DATE,
  file_path       TEXT,
  raw_text        TEXT,
  was_ocr         BOOLEAN NOT NULL DEFAULT FALSE,
  quality         VARCHAR(20) NOT NULL DEFAULT 'unknown' CHECK (quality IN (
    'good', 'low', 'ocr_failed', 'unknown'
  )),
  word_count      INTEGER,
  scraped_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  status          VARCHAR(20) NOT NULL DEFAULT 'scraped' CHECK (status IN (
    'scraped', 'chunked', 'embedded', 'failed'
  ))
);

-- Apply trigger for updated_at
DROP TRIGGER IF EXISTS update_legal_documents_updated_at ON legal_documents;
CREATE TRIGGER update_legal_documents_updated_at
BEFORE UPDATE ON legal_documents
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();
