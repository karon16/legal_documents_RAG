import argparse
import logging
import time
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

import psycopg2
from pgvector.psycopg2 import register_vector
from pipeline.embedder import (
    get_model, get_unembedded_chunks,
    embed_passages, save_embeddings,
    get_embedding_progress
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("./logs/embedder.log")
    ]
)
logger = logging.getLogger(__name__)

DB_CONN = os.getenv("DATABASE_URL")


def run(batch_size: int = 200, dry_run: bool = False):
    conn = psycopg2.connect(DB_CONN)
    register_vector(conn)

    progress = get_embedding_progress(conn)
    logger.info(
        f"Starting: {progress['embedded_chunks']} / "
        f"{progress['total_chunks']} embedded. "
        f"{progress['remaining_chunks']} remaining."
    )

    if progress['remaining_chunks'] == 0:
        logger.info("All chunks already embedded. Nothing to do.")
        conn.close()
        return

    # Force model load before the loop
    get_model()

    total_embedded = 0
    batch_num      = 0
    start_time     = time.time()

    while True:
        chunks = get_unembedded_chunks(conn, batch_size)
        if not chunks:
            break

        batch_num += 1
        ids   = [c['id']   for c in chunks]
        texts = [c['text'] for c in chunks]

        t0         = time.time()
        embeddings = embed_passages(texts)
        encode_ms  = int((time.time() - t0) * 1000)

        if not dry_run:
            t1       = time.time()
            save_embeddings(conn, ids, embeddings)
            write_ms = int((time.time() - t1) * 1000)
        else:
            write_ms = 0

        total_embedded += len(chunks)
        throughput      = len(chunks) / max(time.time() - t0, 0.001)

        logger.info(
            f"Batch {batch_num}: {len(chunks)} chunks | "
            f"encode={encode_ms}ms | write={write_ms}ms | "
            f"{throughput:.1f} chunks/sec"
            + (" [DRY RUN]" if dry_run else "")
        )

    elapsed = time.time() - start_time
    logger.info(
        f"Done. {total_embedded} chunks in {elapsed:.1f}s "
        f"({total_embedded / max(elapsed, 1):.1f} chunks/sec overall)"
    )

    progress = get_embedding_progress(conn)
    logger.info(
        f"Final: {progress['embedded_chunks']} / "
        f"{progress['total_chunks']} embedded."
    )
    conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-size", type=int, default=200)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run(batch_size=args.batch_size, dry_run=args.dry_run)