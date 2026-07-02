import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()
conn = psycopg2.connect(os.getenv("DATABASE_URL"))
conn.autocommit = True
cur = conn.cursor()
try:
    cur.execute("ALTER TABLE legal_documents DROP CONSTRAINT legal_documents_doc_type_check;")
except Exception as e:
    print(f"Drop error: {e}")
cur.execute("""
ALTER TABLE legal_documents ADD CONSTRAINT legal_documents_doc_type_check CHECK (doc_type IN (
    'loi', 'decret', 'arrete', 'ordonnance', 'jurisprudence', 
    'doctrine', 'modele', 'document', 'journal_officiel'
));
""")
print("Database constraint updated.")
conn.close()
