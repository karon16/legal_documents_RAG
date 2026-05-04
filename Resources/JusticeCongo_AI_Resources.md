# JusticeCongo AI — Free Learning Resources
## Mapped to the 12-Week Roadmap

---

## Phase 1: Corpus Ingestion (Weeks 1–3)

### Web Scraping with Python

**Start here — freeCodeCamp YouTube crash course**
- "Web Scraping with Python and BeautifulSoup" — freeCodeCamp channel
  - https://www.youtube.com/watch?v=XVv6mJpFOb0
  - Covers requests, BeautifulSoup parsing, navigating HTML trees, saving data. 1 hour.

**Deep tutorial for LEGANET specifically**
- Real Python — "Beautiful Soup: Build a Web Scraper with Python"
  - https://realpython.com/beautiful-soup-web-scraper-python/
  - The best written tutorial. Covers `.content` vs `.text` (important for ISO-8859-1 encoding on leganet.cd), CSS selectors, and error handling.

**Official docs (bookmark)**
- BeautifulSoup4 Documentation: https://www.crummy.com/software/BeautifulSoup/bs4/doc/
- requests Documentation: https://requests.readthedocs.io/

**Specific to leganet.cd:**
The site uses ISO-8859-1 encoding (French legacy encoding). You'll need:
```python
response.encoding = 'iso-8859-1'  # Must set before accessing response.text
```
This is a gotcha not in most tutorials — the BeautifulSoup docs explain it under "Encodings."

---

### PDF Text Extraction (for Journal Officiel PDFs)

**pdfplumber GitHub + Docs (primary reference)**
- https://github.com/jsvine/pdfplumber
  - Excellent README with working examples for text extraction, page iteration, and table extraction. More reliable than PyPDF2 for French legal PDFs.

**Written tutorial**
- "Extract Text from PDF Files with Python" — Towards Data Science
  - Search for this on Medium/Towards Data Science for current examples.

---

### FastAPI (Backend)

**Start here — Official Tutorial**
- https://fastapi.tiangolo.com/learn/
  - The single best resource. Written by the creator. Covers everything you need for the API layer.

**YouTube**
- freeCodeCamp — FastAPI for Beginners: https://www.youtube.com/watch?v=tLKKmouUams

---

### PostgreSQL + pgvector

**pgvector (primary reference)**
- Official GitHub README: https://github.com/pgvector/pgvector
  - Everything you need: installation, vector column setup, HNSW indexing, cosine similarity queries.

**Practical tutorial**
- DataCamp — pgvector Tutorial: https://www.datacamp.com/tutorial/pgvector-tutorial
  - Free written tutorial: installation, basic ops, Python integration.

**French full-text search in PostgreSQL (critical for hybrid retrieval)**
- PostgreSQL Docs — Text Search: https://www.postgresql.org/docs/current/textsearch.html
  - Focus on the `french` dictionary: `to_tsvector('french', text)` and `plainto_tsquery('french', query)`.
  - French stopwords and stemming are built into PostgreSQL — no extra setup needed.

---

### Docker & Celery + Redis

**Docker Compose** — Official Getting Started: https://docs.docker.com/compose/gettingstarted/

**Celery + FastAPI** (exact stack you're using)
- TestDriven.io — Celery and FastAPI Guide: https://testdriven.io/courses/fastapi-celery/getting-started/
  - Free first chapter covers setup, broker config, and your first async task.

---

## Phase 2: French NLP Pipeline (Weeks 4–6)

### Hugging Face Transformers — Core Knowledge

**Start here — Official Free Course**
- Hugging Face LLM Course: https://huggingface.co/learn/llm-course/chapter1/1
  - Completely free. Chapters 1–4 teach the `pipeline()` API, tokenizers, and how to load any model. You'll use this throughout the project.

**Specific to French:**
- CamemBERT on Hugging Face: https://huggingface.co/camembert-base
  - Official model card. Shows how to load and use the model.
- CamemBERT paper (background reading): https://arxiv.org/abs/1911.03894
  - 8 pages, easy read. Useful for understanding why CamemBERT outperforms multilingual BERT on French tasks — good to mention in portfolio write-ups.

---

### Multilingual Embeddings for French Legal RAG

**The exact experiment you should study**
- Harvard Law School — "Open French Law RAG"
  - https://lil.law.harvard.edu/blog/2025/01/21/open-french-law-rag/
  - Harvard's Library Innovation Lab built a RAG pipeline over 800,000 French legal articles using `intfloat/multilingual-e5-large` + ChromaDB + Ollama. This is your closest reference implementation.
  - Read this carefully. Their architecture is almost identical to what you're building.

**Model cards to read**
- `intfloat/multilingual-e5-large`: https://huggingface.co/intfloat/multilingual-e5-large
  - Explains the "query: " and "passage: " prefix convention — critical for correct usage.
- `maastrichtlawtech/legal-camembert`: https://huggingface.co/maastrichtlawtech/legal-camembert
  - French legal-domain fine-tuned CamemBERT. Alternative embedding model.

**Choosing your multilingual embedding model**
- Towards Data Science — "How to Find the Best Multilingual Embedding Model for Your RAG"
  - https://towardsdatascience.com/how-to-find-the-best-multilingual-embedding-model-for-your-rag-40325c308ebb/
  - Compares top multilingual models on French retrieval benchmarks. Concrete evaluation methodology.

**Sentence Transformers library docs**
- https://sbert.net/
  - Primary reference for loading, encoding, and comparing embeddings.

---

### Zero-Shot Classification in French

**Model to use:** `MoritzLaurer/mDeBERTa-v3-base-mnli-xnli`
- Model card: https://huggingface.co/MoritzLaurer/mDeBERTa-v3-base-mnli-xnli
  - Multilingual, handles French natively, no training data needed.

**Hugging Face Pipeline Docs**
- Zero-Shot Classification: https://huggingface.co/docs/transformers/tasks/zero_shot_classification
  - Shows exactly how to define candidate labels and run inference.

---

### Building the RAG Pipeline

**Best single free resource**
- DeepLearning.AI — RAG Course: https://learn.deeplearning.ai/courses/retrieval-augmented-generation/
  - Free. Covers chunking strategy, retrieval, generation, and grounding — everything you need for Week 6.

**Hybrid retrieval (BM25 + vector) — key concept for legal text**
- "RAG Is More Than Just Vector Search" — Timescale/Tiger Data blog
  - Search for this article on tigerdata.com or timescale.com
  - Explains why pure semantic search fails on legal documents (exact article numbers, legal citations need keyword matching) and how to combine BM25 + pgvector.

**Advanced: How Harvard did French Legal RAG (technical details)**
- https://lil.law.harvard.edu/open-french-law-rag/
  - Technical companion page to the blog post above. Includes the full pipeline architecture and lessons learned.

---

### French NLP — Additional References

**Named Entity Recognition in French**
- `Jean-Baptiste/camembert-ner`: https://huggingface.co/Jean-Baptiste/camembert-ner
  - Fine-tuned CamemBERT for French NER (persons, organizations, locations, dates). Useful for extracting parties and dates from legal documents.

**French Summarization**
- `facebook/mbart-large-cc25` model card: https://huggingface.co/facebook/mbart-large-cc25
  - Multilingual summarization model. Or use the Anthropic API for higher quality.
- Alternatively, prompt-based summarization via Claude API is simpler and produces better French summaries.

**CamemBERT 2.0 (latest, if you want cutting-edge)**
- Paper: https://huggingface.co/papers/2411.08868
  - CamemBERTv2 and CamemBERTav2 — significantly better than the original. Available on Hugging Face.

---

## Phase 3: Features for PPDS (Weeks 7–9)

### Next.js (Frontend)

**Start here — Official Course (free)**
- https://nextjs.org/learn
  - Covers App Router, server-side rendering, API routes, data fetching. The canonical way to learn Next.js.

**YouTube**
- freeCodeCamp has full Next.js courses — search "freeCodeCamp Next.js" for the latest version.

**Interactive**
- Scrimba — Learn Next.js: https://scrimba.com/learn-nextjs-c02moisq6a
  - Code alongside the instructor in-browser. Free tier available.

---

### Document QA (for Template Assistant)

**Hugging Face — Document QA**
- https://huggingface.co/docs/transformers/tasks/document_question_answering
  - Covers LayoutLM-family models for structured document understanding. Useful for the template assistant feature.

**Extractive QA (simpler approach)**
- https://huggingface.co/docs/transformers/tasks/question_answering
  - Using `deepset/roberta-base-squad2`. Simpler than LayoutLM, sufficient for clean text templates.

---

## Phase 4: Polish & Handoff (Weeks 10–12)

### Authentication & Security

**FastAPI Security Docs**
- https://fastapi.tiangolo.com/tutorial/security/
  - JWT tokens, OAuth2, bcrypt hashing. All free, official, complete.

---

### Deployment on a Budget

**Railway.app Docs**: https://docs.railway.com/
- Simplest Docker deployment. Free tier covers your needs.

**Render.com Docs**: https://docs.render.com/
- Alternative. Both Railway and Render support Docker Compose deployments.

**Ollama (for running models locally/on server)**
- https://ollama.com/
- Run Mistral 7B or Llama 3 locally for free generation. Works well for a low-traffic NGO tool.
- Installation: `curl -fsSL https://ollama.com/install.sh | sh`

---

### Testing

**pytest**: https://docs.pytest.org/
**FastAPI testing**: https://fastapi.tiangolo.com/tutorial/testing/

---

## Bonus: Research-Grade Resources (for grad school applications)

These connect your project to academic NLP research — useful for KAIST/POSTECH applications.

**Legal NLP survey papers (read abstracts at minimum)**
- "Legal Judgment Prediction" survey on arXiv — search "legal NLP survey 2024 arXiv"
- "A Survey on Legal Large Language Models" — arXiv 2024

**Multilingual NLP fundamentals**
- Sebastian Ruder — "Multi-domain Multilingual Question Answering": https://www.ruder.io/multi-qa-tutorial/
  - Excellent overview of cross-lingual transfer, zero-shot QA, and multilingual model evaluation. Written by one of the field's key researchers.

**Stanford CS224N — NLP with Deep Learning (free lectures)**
- https://www.youtube.com/playlist?list=PLoROMvodv4rMFqRtEuo6SGjY4XbRIVRd4
  - The gold standard NLP course. Lectures 8 (attention) and 9-11 (transformers, pretraining) are most relevant. Watch these before your KAIST/POSTECH interviews.

**French NLP community**
- TALN (Traitement Automatique du Langage Naturel) — French ACL equivalent: https://taln2025.lirmm.fr/
  - Following this community's work positions you in French NLP research, a genuinely underserved area in the global NLP community.

---

## Suggested Learning Order

| Week | What to Learn | Primary Resource |
|------|---------------|-----------------|
| 1 | Docker Compose + FastAPI basics | FastAPI docs + Docker getting started |
| 2 | BeautifulSoup web scraping | freeCodeCamp YouTube + Real Python tutorial |
| 3 | PDF extraction + text processing | pdfplumber GitHub README |
| 4 | Hugging Face Transformers + multilingual embeddings | HF LLM Course Ch.1–4 + Harvard French Law RAG post |
| 5 | Zero-shot classification (French) | HF zero-shot docs + mDeBERTa model card |
| 6 | RAG pipeline + hybrid retrieval | DeepLearning.AI RAG course + Timescale hybrid search post |
| 7 | French summarization | Anthropic API docs + mBART model card |
| 8 | Document QA for templates | HF document QA docs |
| 9 | Next.js + search UI | nextjs.org/learn |
| 10 | JWT auth + safety features | FastAPI security docs |
| 11 | Testing + performance | pytest docs + FastAPI testing docs |
| 12 | Deployment + documentation | Railway/Render docs + Ollama |

---

*All resources listed above are free or have free access tiers. No paid courses required.*
*The Harvard Law School French Legal RAG post (Week 4) is the single most important reading for this specific project.*
