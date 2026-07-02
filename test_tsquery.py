import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()
conn = psycopg2.connect(os.getenv("DATABASE_URL"))
cur = conn.cursor()

query = "Mon bailleur peut-il me deguerpir sans preavis?"
cur.execute("SELECT plainto_tsquery('french', %s)", (query,))
print(f"plainto_tsquery: {cur.fetchone()[0]}")

cur.execute("SELECT websearch_to_tsquery('french', %s)", (query,))
print(f"websearch_to_tsquery: {cur.fetchone()[0]}")

conn.close()
