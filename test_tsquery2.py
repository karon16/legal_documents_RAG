import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()
conn = psycopg2.connect(os.getenv("DATABASE_URL"))
cur = conn.cursor()

query = "Mon bailleur peut-il me deguerpir sans preavis?"
or_query = ' | '.join(query.split())
print(f"or_query string: {or_query}")
cur.execute("SELECT to_tsquery('french', %s)", (or_query,))
print(f"to_tsquery OR: {cur.fetchone()[0]}")

conn.close()
