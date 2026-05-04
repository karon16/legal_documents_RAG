# JusticeCongo AI Database Module

This directory contains the complete database layer for the JusticeCongo AI RAG pipeline. The database is powered by PostgreSQL with the `pgvector` extension for storing and querying 1024-dimensional embeddings of French legal documents.

## Initialization & Running

The database runs inside a Docker container, making setup quick and consistent across environments.

### 1. Start Docker
Ensure that the Docker daemon is running on your system (e.g., open Docker Desktop on macOS).

### 2. Start the Database
Navigate to the `db/` directory and run the `docker-compose` command to start the PostgreSQL service in detached mode:

```bash
cd db
docker-compose up -d
```

### 3. Automatic Schema Initialization
When the `postgres` container starts for the very first time, it will automatically execute all SQL scripts located in the `init/` folder in numerical order:
- `00_extensions.sql` (enables `vector`, `uuid-ossp`, `pg_trgm`)
- `01_documents.sql` (creates `legal_documents` table)
- `02_chunks.sql` (creates `document_chunks` table)
- `03_rag.sql` (creates RAG specific logging and caching tables)
- `04_features.sql` (creates UI feature tables like summaries and feedback)
- `05_indexes.sql` (creates performance and HNSW vector indexes)

*Note: If you need to completely wipe the database and re-initialize the schema from scratch, run `docker-compose down -v` to delete the volume, and then run `docker-compose up -d` again.*

### 4. Verify Database Status
Check if the container is healthy:
```bash
docker-compose ps
```

## Validation & Testing

You can easily validate that the schema and extensions were installed correctly.

**Test 1: Verify all tables exist**
```bash
docker exec -it justicecongo_postgres psql -U justicecongo -d justicecongo -c "\dt"
```
*(Expected: 9 tables listed)*

**Test 2: Verify `pgvector` works**
```bash
docker exec -it justicecongo_postgres psql -U justicecongo -d justicecongo -c "SELECT '[1,2,3]'::vector;"
```
*(Expected: returns the vector string without error)*

**Test 3: Verify French full-text search (Stemming)**
```bash
docker exec -it justicecongo_postgres psql -U justicecongo -d justicecongo -c "SELECT to_tsvector('french', 'Le locataire peut résilier le bail');"
```
*(Expected: `'bail':6 'locatair':2 'résili':5`)*

## Viewing the Database (GUI)

You can easily inspect the database using visual tools like **pgAdmin**, **DBeaver**, **TablePlus**, or **Postico**. 

Use the following connection details:
- **Host**: `localhost`
- **Port**: `5433` *(We use 5433 to avoid conflicts with your Mac's default Postgres)*
- **User**: `justicecongo`
- **Password**: `justicecongo_dev`
- **Database**: `justicecongo`

## Interacting via Python

The `db.py` file provides a fully featured `Database` class that registers UUID and Vector adapters natively via `psycopg2`.

Test your Python connection:
```bash
# Make sure your virtual environment is activated
python -c "
from db.db import Database
db = Database()
stats = db.get_corpus_stats()
print('Connection OK:', stats)
db.close()
"
```

The application connects to the database via:
`postgresql://justicecongo:justicecongo_dev@localhost:5433/justicecongo`
