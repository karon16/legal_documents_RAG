# JusticeCongo AI — FastAPI Backend

This is the FastAPI backend for JusticeCongo AI, an AI legal assistant built on the LEGANET.CD corpus. It connects the NLP/RAG pipeline to a standard HTTP interface so it can be consumed by the frontend.

## 🚀 Features
- **Semantic + BM25 Hybrid Search**: Query the legal database using pgvector.
- **RAG Generation**: Answers legal questions in French using Anthropic (or local Ollama) models with strict grounding.
- **HyDE & Semantic Caching**: Advanced RAG features to improve relevance and performance.
- **Feedback Loop**: Endpoints to collect user thumbs up/down for continuous quality monitoring.

## 📋 Prerequisites
- Python 3.10+
- PostgreSQL database with `pgvector` enabled (running on port 5433 by default via Docker).
- Anthropic API Key (or a local Ollama instance running `llama3.1`).

## 🛠️ Installation & Setup

1. **Activate your virtual environment** (from the project root):
   ```bash
   source .venv/bin/activate
   ```

2. **Install dependencies**:
   *(Assuming you are in the project root)*
   ```bash
   uv pip install fastapi "uvicorn[standard]" psycopg2-binary pgvector pydantic "httpx<0.28.0"
   ```

3. **Configure Environment Variables**:
   Create or edit the `.env` file in the project root:
   ```env
   DATABASE_URL=postgresql://postgres:postgres@localhost:5433/justicecongo
   ALLOWED_ORIGINS=http://localhost:3000
   ```

## 🏃‍♂️ Running the Server

Start the API with `uvicorn` from the project root:

```bash
uvicorn api.main:app --reload --port 8000
```

*Note: The app uses a FastAPI lifespan to preload the embedding model into memory on startup. It may take 5–10 seconds before the server is ready.*

## 📖 API Documentation (Swagger UI)

FastAPI automatically generates interactive API documentation.
Once the server is running, open your browser and go to:
- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

You can test all endpoints directly from these pages!

## 🧪 Running Tests

To run the full test suite for the API endpoints, ensure you are in the virtual environment and execute:

```bash
PYTHONPATH=$(pwd) pytest api/tests/test_api.py -v
```

## 📡 Endpoints Overview

- `GET /health` & `GET /` — Basic health checks.
- `POST /api/ask` — The main RAG endpoint. Takes a question, retrieves context, and generates a grounded answer.
- `GET /api/search` — Performs hybrid search and returns ranked chunks (without LLM generation).
- `GET /api/documents` — Lists documents in the corpus, with optional filtering.
- `GET /api/documents/{id}` — Gets details of a specific document.
- `GET /api/stats` — Returns overall database usage and RAG statistics.
- `POST /api/feedback` — Accepts user ratings (-1/1) on specific QA logs.
