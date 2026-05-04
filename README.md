# JusticeCongo AI

JusticeCongo AI is a comprehensive, AI-powered Retrieval-Augmented Generation (RAG) platform designed to ingest, process, and analyze the legal corpus of the Democratic Republic of Congo (via leganet.cd). The project aims to make French legal documents accessible, searchable, and understandable through modern natural language processing techniques.

## Purpose

The primary goal of JusticeCongo AI is to democratize access to Congolese legal texts. By leveraging state-of-the-art multilingual machine learning models (such as CamemBERT and multilingual embeddings), the platform provides advanced semantic search, automated document summarization, and interactive Question-Answering (QA) capabilities over complex legal documents. It serves as a tool for legal professionals, researchers, and NGOs to efficiently navigate the legal landscape.

## Features

- **Automated Web Scraping**: A robust Python-based scraper that crawls leganet.cd, downloading existing legal PDFs and converting HTML laws into clean, searchable PDFs.
- **Hybrid Search Architecture**: Combines traditional keyword search (BM25) with semantic vector search (pgvector) in PostgreSQL for highly accurate legal document retrieval.
- **French NLP Pipeline**: Utilizes Hugging Face transformers (CamemBERT, mDeBERTa) for zero-shot classification, named entity recognition, and RAG tailored specifically to the French legal domain.
- **Modern Web Interface**: A responsive frontend built with Next.js to provide users with an intuitive search and reading experience.
- **Asynchronous Processing**: Uses Celery and Redis to handle long-running document ingestion and processing tasks in the background.

## Project Architecture

The project is structured into several core components:

- **`/scraper`**: The web scraping module. Handles crawling, PDF downloading, and HTML-to-PDF conversion.
- **`/api`**: The FastAPI backend. Serves the search endpoints, handles user authentication, and coordinates the RAG pipeline.
- **`/frontend`**: The Next.js web application for end-users to interact with the system.
- **`/pipeline`**: Scripts and modules for the core NLP tasks, chunking, embedding generation, and vector indexing.
- **`/db`**: Database schemas, migrations, and PostgreSQL/pgvector configurations.
- **`/workers`**: Celery tasks for background processing of documents.
- **`/data`**: Local storage directory for downloaded and generated legal PDFs.

## Getting Started

### Prerequisites

- Python 3.x
- Node.js (for the frontend)
- Docker & Docker Compose
- PostgreSQL with `pgvector` extension

### Local Development

1. **Clone the repository** and navigate to the project root.
2. **Start the infrastructure**:
   ```bash
   docker-compose up -d
   ```
   This will start PostgreSQL, Redis, and any other required services.
3. **Run the Scraper**:
   See `scraper.md` for detailed instructions on setting up the Python environment and running the initial ingestion of the leganet.cd corpus.
4. **Start the API**:
   Navigate to the `/api` directory, install dependencies, and start the FastAPI server.
5. **Start the Frontend**:
   Navigate to the `/frontend` directory, run `npm install`, and start the Next.js development server.

## Roadmap

The project development is mapped across 4 phases:
1. **Corpus Ingestion**: Building the scraper, downloading documents, and converting HTML to PDF.
2. **French NLP Pipeline**: Setting up the vector database, testing multilingual embedding models, and building the RAG retrieval flow.
3. **Frontend & Features**: Developing the Next.js interface and interactive document QA features.
4. **Polish & Handoff**: Securing endpoints, writing tests, and deploying the platform.

For a detailed breakdown of learning resources and references, see `Resources/JusticeCongo_AI_Resources.md`.
