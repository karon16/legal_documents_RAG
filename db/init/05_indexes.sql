-- pgvector HNSW index (most important)
CREATE INDEX IF NOT EXISTS idx_chunks_embedding_hnsw
ON document_chunks
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- French full-text search index (for BM25 hybrid retrieval)
CREATE INDEX IF NOT EXISTS idx_chunks_fts_french
ON document_chunks
USING GIN (to_tsvector('french', text));

-- Trigram index for fuzzy title/article search
CREATE INDEX IF NOT EXISTS idx_documents_title_trgm
ON legal_documents
USING GIN (title gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_chunks_article_trgm
ON document_chunks
USING GIN (article_number gin_trgm_ops);

-- Standard B-tree indexes for legal_documents
CREATE INDEX IF NOT EXISTS idx_documents_domain ON legal_documents(domain);
CREATE INDEX IF NOT EXISTS idx_documents_doc_type ON legal_documents(doc_type);
CREATE INDEX IF NOT EXISTS idx_documents_date ON legal_documents(date_enacted);
CREATE INDEX IF NOT EXISTS idx_documents_status ON legal_documents(status);
CREATE INDEX IF NOT EXISTS idx_documents_quality ON legal_documents(quality);
CREATE INDEX IF NOT EXISTS idx_documents_scraped ON legal_documents(scraped_at DESC);

-- Standard B-tree indexes for document_chunks
CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON document_chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_chunks_domain ON document_chunks(document_id) WHERE embedding IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_chunks_embedded ON document_chunks(embedded_at DESC) WHERE embedded_at IS NOT NULL;

-- Standard B-tree indexes for chunk_classifications
CREATE INDEX IF NOT EXISTS idx_classifications_chunk ON chunk_classifications(chunk_id);
CREATE INDEX IF NOT EXISTS idx_classifications_domain ON chunk_classifications(domain_label);
CREATE INDEX IF NOT EXISTS idx_classifications_clause ON chunk_classifications(clause_type);
CREATE INDEX IF NOT EXISTS idx_classifications_risk ON chunk_classifications(risk_score) WHERE risk_score IS NOT NULL;

-- Standard B-tree indexes for qa_logs
CREATE INDEX IF NOT EXISTS idx_qa_question_hash ON qa_logs(question_hash);
CREATE INDEX IF NOT EXISTS idx_qa_created ON qa_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_qa_session ON qa_logs(user_session) WHERE user_session IS NOT NULL;

-- Standard B-tree indexes for chunk_search_cache
CREATE INDEX IF NOT EXISTS idx_cache_expires ON chunk_search_cache(expires_at);

-- Standard B-tree indexes for document_summaries
CREATE INDEX IF NOT EXISTS idx_summaries_document ON document_summaries(document_id);
CREATE INDEX IF NOT EXISTS idx_summaries_type ON document_summaries(document_id, summary_type);

-- Standard B-tree indexes for search_logs
CREATE INDEX IF NOT EXISTS idx_search_hash ON search_logs(query_hash);
CREATE INDEX IF NOT EXISTS idx_search_created ON search_logs(created_at DESC);

-- Standard B-tree indexes for user_feedback
CREATE INDEX IF NOT EXISTS idx_feedback_qa ON user_feedback(qa_log_id);
CREATE INDEX IF NOT EXISTS idx_feedback_rating ON user_feedback(rating);
