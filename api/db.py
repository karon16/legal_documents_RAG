import os
import psycopg2
from psycopg2.extras import RealDictCursor
from pgvector.psycopg2 import register_vector
from dotenv import load_dotenv

load_dotenv()

DB_CONN = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5433/justicecongo"
)

def get_db():
    conn = psycopg2.connect(DB_CONN, cursor_factory=RealDictCursor)
    register_vector(conn)
    try:
        yield conn
    finally:
        conn.close()
