import os
import psycopg2
from psycopg2.extras import register_uuid, execute_values
from pgvector.psycopg2 import register_vector
from dotenv import load_dotenv

load_dotenv()

class Database:
    def __init__(self, connection_string: str = None):
        if not connection_string:
            connection_string = os.getenv("DATABASE_URL")
            
        self.conn = psycopg2.connect(connection_string)
        self.conn.autocommit = False
        
        # Register adapters
        register_uuid()
        register_vector(self.conn)
        
    def close(self) -> None:
        self.conn.close()

    # ── Document methods ──

    def upsert_document(self, doc: dict) -> str:
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO legal_documents (
                    source_url, title, domain, doc_type, date_enacted, 
                    file_path, raw_text, was_ocr, quality, word_count, status
                ) VALUES (
                    %(source_url)s, %(title)s, %(domain)s, %(doc_type)s, %(date_enacted)s,
                    %(file_path)s, %(raw_text)s, %(was_ocr)s, %(quality)s, %(word_count)s, %(status)s
                )
                ON CONFLICT (source_url) DO UPDATE SET
                    title = EXCLUDED.title,
                    domain = EXCLUDED.domain,
                    doc_type = EXCLUDED.doc_type,
                    date_enacted = EXCLUDED.date_enacted,
                    file_path = EXCLUDED.file_path,
                    raw_text = EXCLUDED.raw_text,
                    was_ocr = EXCLUDED.was_ocr,
                    quality = EXCLUDED.quality,
                    word_count = EXCLUDED.word_count,
                    status = EXCLUDED.status,
                    updated_at = NOW()
                RETURNING id;
            """, doc)
            inserted_id = cur.fetchone()[0]
        self.conn.commit()
        return inserted_id

    def get_document_by_url(self, url: str) -> dict | None:
        with self.conn.cursor() as cur:
            cur.execute("SELECT * FROM legal_documents WHERE source_url = %s;", (url,))
            row = cur.fetchone()
            if row:
                col_names = [desc[0] for desc in cur.description]
                return dict(zip(col_names, row))
            return None

    def get_documents_by_status(self, status: str) -> list[dict]:
        with self.conn.cursor() as cur:
            cur.execute("SELECT * FROM legal_documents WHERE status = %s ORDER BY scraped_at;", (status,))
            col_names = [desc[0] for desc in cur.description]
            return [dict(zip(col_names, row)) for row in cur.fetchall()]

    def update_document_status(self, document_id: str, status: str) -> None:
        with self.conn.cursor() as cur:
            cur.execute("UPDATE legal_documents SET status = %s WHERE id = %s;", (status, document_id))
        self.conn.commit()

    def get_all_scraped_urls(self) -> set[str]:
        with self.conn.cursor() as cur:
            cur.execute("SELECT source_url FROM legal_documents;")
            return {row[0] for row in cur.fetchall()}

    # ── Chunk methods ──

    def insert_chunks(self, chunks: list[dict]) -> None:
        if not chunks:
            return
            
        rows = [
            (
                c['document_id'], c['chunk_index'], c['text'], c.get('article_number'),
                c.get('chapter_heading'), c.get('section_heading'), c.get('page_number'),
                c.get('metadata', '{}')
            )
            for c in chunks
        ]
        
        with self.conn.cursor() as cur:
            execute_values(cur, """
                INSERT INTO document_chunks (
                    document_id, chunk_index, text, article_number, 
                    chapter_heading, section_heading, page_number, metadata
                ) VALUES %s
                ON CONFLICT (document_id, chunk_index) DO UPDATE SET
                    text = EXCLUDED.text,
                    article_number = EXCLUDED.article_number,
                    chapter_heading = EXCLUDED.chapter_heading,
                    section_heading = EXCLUDED.section_heading,
                    page_number = EXCLUDED.page_number,
                    metadata = EXCLUDED.metadata;
            """, rows)
        self.conn.commit()

    def update_chunk_embedding(self, chunk_id: str, embedding: list[float], model: str) -> None:
        with self.conn.cursor() as cur:
            cur.execute("""
                UPDATE document_chunks 
                SET embedding = %s, embedding_model = %s, embedded_at = NOW()
                WHERE id = %s;
            """, (embedding, model, chunk_id))
        self.conn.commit()

    def batch_update_embeddings(self, updates: list[tuple[str, list[float]]]) -> None:
        if not updates:
            return
            
        with self.conn.cursor() as cur:
            execute_values(cur, """
                UPDATE document_chunks AS dc
                SET embedding = v.embedding::vector, embedded_at = NOW()
                FROM (VALUES %s) AS v(id, embedding)
                WHERE dc.id = v.id::uuid;
            """, updates)
        self.conn.commit()

    def get_unembedded_chunks(self, limit: int = 500) -> list[dict]:
        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT id, text FROM document_chunks
                WHERE embedding IS NULL
                ORDER BY created_at
                LIMIT %s;
            """, (limit,))
            col_names = [desc[0] for desc in cur.description]
            return [dict(zip(col_names, row)) for row in cur.fetchall()]

    # ── Retrieval methods ──

    def semantic_search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        domain_filter: str = None,
        doc_type_filter: str = None,
        min_date: str = None,
        max_date: str = None
    ) -> list[dict]:
        
        base_query = """
            SELECT 
                dc.id,
                dc.text,
                dc.article_number,
                dc.chapter_heading,
                dc.metadata,
                ld.title AS document_title,
                ld.domain,
                ld.doc_type,
                ld.date_enacted,
                ld.source_url,
                1 - (dc.embedding <=> %s::vector) AS similarity_score
            FROM document_chunks dc
            JOIN legal_documents ld ON dc.document_id = ld.id
            WHERE dc.embedding IS NOT NULL
        """
        
        filters = []
        params = [query_embedding]
        
        if domain_filter:
            filters.append("ld.domain = %s")
            params.append(domain_filter)
        if doc_type_filter:
            filters.append("ld.doc_type = %s")
            params.append(doc_type_filter)
        if min_date:
            filters.append("ld.date_enacted >= %s")
            params.append(min_date)
        if max_date:
            filters.append("ld.date_enacted <= %s")
            params.append(max_date)
            
        if filters:
            base_query += " AND " + " AND ".join(filters)
            
        base_query += "\n ORDER BY dc.embedding <=> %s::vector LIMIT %s;"
        params.extend([query_embedding, top_k])
        
        with self.conn.cursor() as cur:
            cur.execute(base_query, tuple(params))
            col_names = [desc[0] for desc in cur.description]
            return [dict(zip(col_names, row)) for row in cur.fetchall()]

    def fulltext_search(
        self,
        query: str,
        top_k: int = 10,
        domain_filter: str = None
    ) -> list[dict]:
        
        base_query = """
            SELECT 
                dc.id,
                dc.text,
                dc.article_number,
                ld.title AS document_title,
                ld.domain,
                ld.doc_type,
                ld.date_enacted,
                ts_rank(to_tsvector('french', dc.text),
                        plainto_tsquery('french', %s)) AS bm25_score
            FROM document_chunks dc
            JOIN legal_documents ld ON dc.document_id = ld.id
            WHERE to_tsvector('french', dc.text) @@ plainto_tsquery('french', %s)
        """
        
        params = [query, query]
        
        if domain_filter:
            base_query += " AND ld.domain = %s"
            params.append(domain_filter)
            
        base_query += "\n ORDER BY bm25_score DESC LIMIT %s;"
        params.append(top_k)
        
        with self.conn.cursor() as cur:
            cur.execute(base_query, tuple(params))
            col_names = [desc[0] for desc in cur.description]
            return [dict(zip(col_names, row)) for row in cur.fetchall()]

    # ── QA logging methods ──

    def log_qa(self, log_entry: dict) -> str:
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO qa_logs (
                    question, question_hash, answer, sources, domain_filter, 
                    retrieval_count, was_cache_hit, retrieval_ms, generation_ms, 
                    model_used, had_citations, user_session
                ) VALUES (
                    %(question)s, %(question_hash)s, %(answer)s, %(sources)s, %(domain_filter)s,
                    %(retrieval_count)s, %(was_cache_hit)s, %(retrieval_ms)s, %(generation_ms)s,
                    %(model_used)s, %(had_citations)s, %(user_session)s
                ) RETURNING id;
            """, log_entry)
            inserted_id = cur.fetchone()[0]
        self.conn.commit()
        return inserted_id

    def get_cached_answer(self, question_hash: str) -> dict | None:
        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM qa_logs
                WHERE question_hash = %s
                  AND was_cache_hit = FALSE
                  AND created_at > NOW() - INTERVAL '6 hours'
                ORDER BY created_at DESC
                LIMIT 1;
            """, (question_hash,))
            row = cur.fetchone()
            if row:
                col_names = [desc[0] for desc in cur.description]
                return dict(zip(col_names, row))
            return None

    def log_feedback(self, qa_log_id: str, rating: int, comment: str = None, flagged_reason: str = None) -> None:
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO user_feedback (qa_log_id, rating, comment, flagged_reason)
                VALUES (%s, %s, %s, %s);
            """, (qa_log_id, rating, comment, flagged_reason))
        self.conn.commit()

    # ── Cache methods ──

    def get_search_cache(self, question_hash: str) -> list[str] | None:
        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT top_chunk_ids FROM chunk_search_cache
                WHERE question_hash = %s AND expires_at > NOW();
            """, (question_hash,))
            row = cur.fetchone()
            return row[0] if row else None

    def set_search_cache(self, question_hash: str, question: str, chunk_ids: list[str]) -> None:
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO chunk_search_cache (question_hash, question, top_chunk_ids)
                VALUES (%s, %s, %s)
                ON CONFLICT (question_hash) DO UPDATE
                SET top_chunk_ids = EXCLUDED.top_chunk_ids,
                    cached_at = NOW(),
                    expires_at = NOW() + INTERVAL '6 hours';
            """, (question_hash, question, chunk_ids))
        self.conn.commit()

    def purge_expired_cache(self) -> int:
        with self.conn.cursor() as cur:
            cur.execute("DELETE FROM chunk_search_cache WHERE expires_at < NOW();")
            deleted_count = cur.rowcount
        self.conn.commit()
        return deleted_count

    # ── Analytics methods ──

    def get_corpus_stats(self) -> dict:
        stats = {}
        with self.conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM legal_documents;")
            stats["total_documents"] = cur.fetchone()[0]
            
            cur.execute("SELECT domain, COUNT(*) FROM legal_documents GROUP BY domain ORDER BY COUNT(*) DESC;")
            stats["by_domain"] = dict(cur.fetchall())
            
            cur.execute("SELECT quality, COUNT(*) FROM legal_documents GROUP BY quality;")
            stats["by_quality"] = dict(cur.fetchall())
            
            # Since some tables might not exist yet if init scripts haven't run, handle gracefully
            try:
                cur.execute("SELECT COUNT(*) FROM document_chunks;")
                stats["total_chunks"] = cur.fetchone()[0]
                
                cur.execute("SELECT COUNT(*) FROM document_chunks WHERE embedding IS NOT NULL;")
                stats["embedded_chunks"] = cur.fetchone()[0]
                
                cur.execute("SELECT COUNT(*) FROM qa_logs;")
                stats["total_qa_interactions"] = cur.fetchone()[0]
                
                cur.execute("SELECT AVG(rating) FROM user_feedback;")
                avg = cur.fetchone()[0]
                stats["avg_rating"] = float(avg) if avg is not None else None
            except psycopg2.Error:
                # If chunk/qa tables aren't set up yet
                self.conn.rollback()
                
        return stats


# REFERENCE QUERIES
# 
# -- Find all high-risk chunks (for the risk dashboard)
# SELECT dc.text, dc.article_number, ld.title, cc.risk_score
# FROM document_chunks dc
# JOIN legal_documents ld ON dc.document_id = ld.id
# JOIN chunk_classifications cc ON cc.chunk_id = dc.id
# WHERE cc.risk_score = 'potentially_adverse'
# ORDER BY ld.date_enacted DESC;
# 
# -- Find similar chunks to a given chunk (for "Find Similar" feature)
# SELECT dc2.text, dc2.article_number, ld2.title,
#        1 - (dc2.embedding <=> dc1.embedding) AS similarity
# FROM document_chunks dc1
# JOIN document_chunks dc2 ON dc2.id != dc1.id
# JOIN legal_documents ld2 ON dc2.document_id = ld2.id
# WHERE dc1.id = '<target_chunk_id>'
#   AND 1 - (dc2.embedding <=> dc1.embedding) > 0.80
# ORDER BY dc2.embedding <=> dc1.embedding
# LIMIT 10;
# 
# -- Most common questions (for analytics dashboard)
# SELECT question, COUNT(*) AS frequency,
#        AVG(generation_ms) AS avg_generation_ms
# FROM qa_logs
# GROUP BY question
# ORDER BY frequency DESC
# LIMIT 20;
# 
# -- Cache hit rate (monitoring metric)
# SELECT 
#   COUNT(*) FILTER (WHERE was_cache_hit) AS cache_hits,
#   COUNT(*) AS total,
#   ROUND(100.0 * COUNT(*) FILTER (WHERE was_cache_hit) / COUNT(*), 1) 
#     AS hit_rate_pct
# FROM qa_logs
# WHERE created_at > NOW() - INTERVAL '24 hours';
# 
# -- Documents ready for embedding (status = 'chunked' but no embeddings)
# SELECT ld.id, ld.title, COUNT(dc.id) AS chunk_count
# FROM legal_documents ld
# JOIN document_chunks dc ON dc.document_id = ld.id
# WHERE ld.status = 'chunked'
#   AND dc.embedding IS NULL
# GROUP BY ld.id, ld.title;
