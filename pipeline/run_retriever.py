import argparse
import logging
import time
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from dotenv import load_dotenv
    # Explicitly point to the .env file in the root directory
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
    load_dotenv(env_path)
except ImportError:
    pass

import psycopg2
from pgvector.psycopg2 import register_vector
from pipeline.retriever import retrieve

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
    ]
)
logger = logging.getLogger(__name__)

DB_CONN = os.getenv("DATABASE_URL")

def run(query: str, top_k: int = 5):
    conn = psycopg2.connect(DB_CONN)
    register_vector(conn)
    
    logger.info(f"Retrieving top {top_k} results for: '{query}'")
    start_time = time.time()
    
    results = retrieve(conn, query, top_k=top_k)
    
    elapsed = time.time() - start_time
    logger.info(f"Retrieved {len(results)} results in {elapsed:.3f}s")
    
    for i, res in enumerate(results, 1):
        print(f"\n--- Result {i} (Score: {res.rrf_score:.3f}) ---")
        print(f"Document: {res.document_title} (Domain: {res.domain})")
        print(f"Article: {res.article_number} | Chapter: {res.chapter_heading}")
        print(f"Scores -> Semantic: {res.semantic_score:.3f} | BM25: {res.bm25_score:.3f}")
        print(f"Text Snippet: {res.text[:300]}...")
        
    conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test the hybrid search retriever.")
    parser.add_argument("query", type=str, help="The query string to search for in French")
    parser.add_argument("--top-k", type=int, default=5, help="Number of results to return")
    args = parser.parse_args()
    
    if not DB_CONN:
        logger.error("DATABASE_URL environment variable is not set.")
        sys.exit(1)
        
    run(query=args.query, top_k=args.top_k)
