import json
import psycopg2
from psycopg2.extras import execute_values, RealDictCursor
from pipeline.chunker import Chunk

def get_documents_to_chunk(conn, batch_size: int = 50) -> list[dict]:
    """Fetches documents with status='scraped' that have raw_text."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT id, raw_text, domain, doc_type, title
            FROM legal_documents
            WHERE status = 'scraped'
              AND raw_text IS NOT NULL
              AND raw_text != ''
            ORDER BY scraped_at ASC
            LIMIT %s
        """, (batch_size,))
        return [dict(row) for row in cur.fetchall()]


def save_chunks(conn, chunks: list[Chunk]) -> int:
    """Batch-inserts chunks using execute_values. Returns count saved."""
    if not chunks:
        return 0

    rows = [
        (
            c.document_id,
            c.chunk_index,
            c.text,
            c.article_number,
            c.chapter_heading,
            c.section_heading,
            c.page_number,
            c.token_count,
            json.dumps(c.metadata),
        )
        for c in chunks
    ]

    with conn.cursor() as cur:
        execute_values(cur, """
            INSERT INTO document_chunks
              (document_id, chunk_index, text, article_number,
               chapter_heading, section_heading, page_number, token_count, metadata)
            VALUES %s
            ON CONFLICT (document_id, chunk_index) DO UPDATE SET
              text            = EXCLUDED.text,
              article_number  = EXCLUDED.article_number,
              chapter_heading = EXCLUDED.chapter_heading,
              section_heading = EXCLUDED.section_heading,
              page_number     = EXCLUDED.page_number,
              token_count     = EXCLUDED.token_count,
              metadata        = EXCLUDED.metadata
        """, rows)
    conn.commit()
    return len(chunks)


def mark_document_chunked(conn, document_id: str) -> None:
    """Updates document status to 'chunked' after successful processing."""
    with conn.cursor() as cur:
        cur.execute("""
            UPDATE legal_documents
            SET status = 'chunked', updated_at = NOW()
            WHERE id = %s
        """, (document_id,))
    conn.commit()
