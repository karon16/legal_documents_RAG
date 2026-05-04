# JusticeCongo AI - RAG Implementation Roadmap

## Phase 2A: Data Structuring
- [ ] **Legal Semantic Chunking (Pipeline Step 1)**
  - Read `raw_text` from `legal_documents`.
  - Implement regex-based chunking that respects Congolese legal structure (splitting by "Article 1", "Chapitre II", etc.) rather than blind token splitting.
  - Fallback to fixed-size chunking (with overlap) for documents without clear article markers.
  - Insert the resulting chunks into the `document_chunks` table.

## Phase 2B: Embeddings & Vector Search
- [ ] **Multilingual Embedding Generation (Pipeline Step 2)**
  - Integrate `sentence-transformers` with the `intfloat/multilingual-e5-large` model.
  - Prepend the required `"passage: "` prefix to each chunk.
  - Generate embeddings and save them to the `embedding VECTOR(1024)` column in PostgreSQL.
- [ ] **Database Indexing**
  - Create the `HNSW` index on the `embedding` column for fast approximate nearest neighbor search.
  - Create a `GIN (to_tsvector('french', text))` index for BM25/keyword search capability.

## Phase 2C: NLP Enrichment (Optional but Recommended)
- [ ] **Zero-Shot Domain Classification**
  - Use `MoritzLaurer/mDeBERTa-v3-base-mnli-xnli` to classify chunks into detailed legal topics and clause types without training data.

## Phase 3: The RAG Engine
- [ ] **Hybrid Retrieval Module**
  - Implement semantic search (pgvector) + keyword search (BM25).
  - Implement Reciprocal Rank Fusion (RRF) to merge and rerank the results from both searches.
- [ ] **Generation Module (LLM Integration)**
  - Integrate the LLM API (Anthropic Claude or local Ollama).
  - Build the strict legal system prompt to ensure grounding, exact article citation, and safety disclaimers.

## Phase 4: API & Frontend
- [ ] **FastAPI Backend**
  - Build endpoints: `/api/search` (hybrid search), `/api/ask` (full RAG response), `/api/documents/{id}`.
- [ ] **Next.js Frontend UI**
  - Build the chat interface and the document browser.
