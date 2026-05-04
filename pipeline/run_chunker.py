import argparse
import logging
import psycopg2
import time
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv

load_dotenv()

from pipeline.chunker import chunk_document
from pipeline.chunk_db import (
    get_documents_to_chunk,
    save_chunks,
    mark_document_chunked
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("./logs/chunker.log")
    ]
)

DB_CONN = os.getenv("DATABASE_URL")

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
                if not dry_run:
                    conn.rollback()
                continue
        
        if dry_run:
            break

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
