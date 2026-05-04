# JusticeCongo AI — 12-Week Implementation Roadmap
## A Legal Aid Intelligence Platform for LEGANET.CD / PPDS

**Mission:** Build and donate a free, open-source AI assistant that makes Congolese law understandable and searchable for ordinary citizens, lawyers, and magistrates — grounded entirely in the LEGANET.CD corpus.

**Language:** French throughout (UI, NLP models, RAG answers)
**Donation target:** PPDS / leganet.cd (contact: ppds@ppds.be)

---

## What You're Building

A web application where anyone can:
1. Ask legal questions in French and get grounded, cited answers drawn from actual Congolese laws
2. Search across 140+ years of legislation by meaning, not just keywords
3. Read plain-language summaries of complex decrees and ordinances
4. Browse legal templates (contrats de bail, actes d'état civil) with AI-generated explanations

The entire knowledge base comes from leganet.cd — no hallucinated law, no generic legal advice.

---

## Corpus Overview (from leganet.cd)

| Section | Content |
|--------|---------|
| Législation | Laws, decrees, ordinances from 1883–2023 across 8 legal domains |
| Jurisprudence | Constitutional court, Supreme Court, and criminal rulings |
| Doctrine | Legal commentary and analysis |
| Journal Officiel | Official government publications |
| Modèles | Legal form templates (bail, état civil, foncier) |

---

## Phase 1: Corpus Ingestion (Weeks 1–3)
### Build the data pipeline before touching any ML

---

### Week 1 — Contact PPDS & Project Setup

**First action (before writing code):**
Send an email to ppds@ppds.be. Introduce yourself as a CS student building a free legal AI tool using their corpus as a donation. Ask for:
- Permission to scrape and use their content programmatically
- Any offline data dumps they may already have
- Their blessing to build on their work

Then initialize the project:

**Project structure:**
```
justicecongo/
├── scraper/          # leganet.cd ingestion pipeline
├── pipeline/         # NLP processing (chunking, embedding, classification)
├── api/              # FastAPI backend
├── workers/          # Celery async tasks
├── frontend/         # Next.js UI
├── db/               # PostgreSQL + pgvector migrations
└── docs/             # Donation handoff documentation
```

**Infrastructure (Docker Compose):**
- PostgreSQL 16 with pgvector extension
- Redis (Celery broker + result backend)
- API container (FastAPI + Uvicorn)
- Worker container (Celery)

**Database schema (set up now, populate later):**
```sql
CREATE TABLE legal_documents (
  id UUID PRIMARY KEY,
  source_url TEXT UNIQUE,
  title TEXT,
  domain VARCHAR(50),       -- droit_civil, droit_penal, etc.
  doc_type VARCHAR(30),     -- loi, decret, arrete, jurisprudence, doctrine
  date_enacted DATE,
  raw_html TEXT,
  raw_text TEXT,
  status VARCHAR(20) DEFAULT 'scraped'
);

CREATE TABLE document_chunks (
  id UUID PRIMARY KEY,
  document_id UUID REFERENCES legal_documents(id),
  chunk_index INTEGER,
  text TEXT,
  article_number TEXT,      -- "Article 12", "Section 3", etc.
  embedding VECTOR(768),    -- for CamemBERT-based embeddings
  metadata JSONB
);

CREATE TABLE qa_logs (
  id UUID PRIMARY KEY,
  question TEXT,
  answer TEXT,
  sources JSONB,
  timestamp TIMESTAMPTZ DEFAULT NOW()
);
```

**Deliverable:** Running Docker environment, empty database with schema, first contact with PPDS sent.

---

### Week 2 — Web Scraper for leganet.cd

The site is static HTML — ideal for scraping. Build a respectful, rate-limited crawler.

**Scraping strategy:**
1. Start at `legislation.htm` — parse the chronological index to collect all law URLs
2. Visit each law page — extract title, date, domain, full HTML text
3. Repeat for `jurisprudence.htm`, `doctrine.htm`, `Modeles.htm`
4. Handle PDFs separately (pdfplumber for text extraction)
5. Store raw HTML + extracted text in PostgreSQL

**Key technical decisions:**
- Use `requests` + `BeautifulSoup4` for HTML parsing
- Rate limit: 1 request per 2 seconds (respectful of their server)
- Detect encoding issues (the site uses ISO-8859-1 for accented French characters)
- Store canonical URL as unique key to avoid re-scraping

```python
# Example scraper structure
import requests
from bs4 import BeautifulSoup
import time

BASE_URL = "https://www.leganet.cd"
HEADERS = {"User-Agent": "JusticeCongo-AI-Bot/1.0 (academic research, ppds@ppds.be)"}

def scrape_legislation_index():
    resp = requests.get(f"{BASE_URL}/legislation.htm", headers=HEADERS)
    resp.encoding = 'iso-8859-1'
    soup = BeautifulSoup(resp.text, 'html.parser')
    # Extract all [Texte] links → collect document URLs
    ...

def scrape_document(url):
    time.sleep(2)  # Rate limiting
    resp = requests.get(url, headers=HEADERS)
    resp.encoding = 'iso-8859-1'
    # Extract text, title, date, domain
    ...
```

**PDF handling:**
- Download PDFs linked from the site (Journal Officiel, some jurisprudence)
- Extract text with `pdfplumber`
- Flag as `doc_type = 'journal_officiel'`

**Deliverable:** Database populated with raw text of the entire leganet.cd corpus.

---

### Week 3 — Text Processing & Intelligent Chunking

French legal text has a specific structure. Your chunker must respect it.

**Legal document anatomy (Congolese law):**
```
[Title / Intitulé]
[Preamble / Préambule]
[CHAPITRE I — ...]
  [Article 1: ...]
  [Article 2: ...]
[CHAPITRE II — ...]
  [Article 3: ...]
```

**Chunking strategy:**
- Primary split: by Article number (`Article 1`, `Art. 12`, `ARTICLE PREMIER`)
- Fallback: by paragraph with 100-token overlap
- Preserve metadata per chunk: article_number, chapter_heading, document_title, date, domain

**French text normalization:**
- Handle encoding artifacts from ISO-8859-1 → UTF-8 conversion
- Normalize legal abbreviations: `J.O.`, `B.O.`, `M.C.`, `O.L.`
- Strip HTML artifacts while preserving structure markers

**Quality checks:**
- Flag chunks under 50 words (probably headers or artifacts)
- Flag documents with no article structure detected (likely PDFs needing OCR review)
- Log extraction quality metrics

**Deliverable:** All documents chunked, stored in `document_chunks` table with rich metadata. Ready for embedding.

---

## Phase 2: French NLP Pipeline (Weeks 4–6)

---

### Week 4 — Multilingual Embeddings + pgvector Population

This is the core retrieval infrastructure for the entire system.

**Model choice for French legal embeddings:**

Option A (recommended): `intfloat/multilingual-e5-large`
- Proven on French legal text (used by Harvard Law School's Open French Law RAG experiment)
- 768 dimensions, strong multilingual retrieval
- Run: `pip install sentence-transformers`

Option B (French-specialized): `maastrichtlawtech/legal-camembert`
- Fine-tuned CamemBERT on French legal corpus
- Better domain specificity but English retrieval queries won't work
- Use if your user base is exclusively French-speaking

**Embedding pipeline (Celery task):**
```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('intfloat/multilingual-e5-large')

@celery.task
def embed_chunks(document_id):
    chunks = db.query(Chunk).filter_by(document_id=document_id).all()
    texts = [f"passage: {c.text}" for c in chunks]  # e5 requires prefix
    embeddings = model.encode(texts, batch_size=32, show_progress_bar=True)
    for chunk, embedding in zip(chunks, embeddings):
        chunk.embedding = embedding.tolist()
    db.commit()
```

**pgvector indexes:**
```sql
-- HNSW index for fast approximate nearest neighbor search
CREATE INDEX ON document_chunks
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Full-text search index for hybrid retrieval
CREATE INDEX ON document_chunks USING GIN(to_tsvector('french', text));
```

**Deliverable:** All ~50,000+ chunks embedded and indexed. Semantic search working in a test script.

---

### Week 5 — Zero-Shot Legal Domain Classification

Without any labeled training data, classify every legal chunk by its function. This powers the "filter by topic" feature in the UI.

**Model:** `MoritzLaurer/mDeBERTa-v3-base-mnli-xnli` (multilingual, handles French natively)

**Candidate labels (French):**
```python
LEGAL_DOMAINS = [
    "droit civil", "droit pénal", "droit commercial",
    "droit fiscal", "droit du travail", "droit foncier",
    "droit de la famille", "droit public", "droit social",
    "procédure judiciaire", "droit constitutionnel"
]

CLAUSE_TYPES = [
    "définition", "obligation", "interdiction", "sanction pénale",
    "procédure", "compétence juridictionnelle", "délai",
    "droit accordé aux citoyens", "disposition transitoire"
]
```

**Why this matters for the donation:**
A citizen asking "puis-je être expulsé de ma maison sans préavis?" needs the system to find both the *Bail* sections (droit civil) and the *Procédure d'expulsion* (droit judiciaire). Zero-shot classification of chunks enables multi-domain retrieval.

**Store results:**
```sql
ALTER TABLE document_chunks
ADD COLUMN domain_label VARCHAR(50),
ADD COLUMN clause_type VARCHAR(50),
ADD COLUMN classification_confidence FLOAT;
```

**Deliverable:** Every chunk classified. Build a simple stats page showing corpus distribution by domain (pie chart using recharts).

---

### Week 6 — RAG Pipeline: The Heart of the System

This is what citizens actually interact with. The architecture must be:
- **Grounded:** Every answer cites specific articles by name and date
- **Honest:** If the answer isn't in leganet.cd, say so explicitly
- **Simple:** Answers must be understandable by non-lawyers

**Retrieval (hybrid BM25 + semantic):**
```python
def retrieve(question: str, top_k: int = 5):
    # 1. Semantic search via pgvector
    query_embedding = model.encode(f"query: {question}")
    semantic_results = db.execute("""
        SELECT *, 1 - (embedding <=> %s) as score
        FROM document_chunks
        ORDER BY embedding <=> %s
        LIMIT %s
    """, [query_embedding, query_embedding, top_k * 2])

    # 2. BM25 full-text search
    keyword_results = db.execute("""
        SELECT *, ts_rank(to_tsvector('french', text),
                         plainto_tsquery('french', %s)) as score
        FROM document_chunks
        WHERE to_tsvector('french', text) @@ plainto_tsquery('french', %s)
        ORDER BY score DESC
        LIMIT %s
    """, [question, question, top_k * 2])

    # 3. Merge and deduplicate (reciprocal rank fusion)
    return merge_results(semantic_results, keyword_results, top_k)
```

**Generation prompt (critical for the donation purpose):**
```
Tu es un assistant juridique spécialisé dans le droit congolais.
Tu dois répondre UNIQUEMENT en te basant sur les extraits de loi fournis.
Si la réponse n'est pas dans les extraits, dis clairement :
"Cette information ne figure pas dans les textes disponibles sur LEGANET.CD."

NE DONNE PAS de conseils juridiques personnalisés.
Oriente toujours l'utilisateur vers un avocat ou un magistrat pour sa situation spécifique.

Extraits pertinents :
{context}

Question : {question}

Réponds en français simple et clair. Cite toujours les articles de loi.
```

**Generator options (pick one):**
- Free: Local `mistral-7b-instruct` via Ollama (runs on CPU, slower)
- Best quality: Anthropic API (Claude) — generous free tier for NGO/education use

**Deliverable:** End-to-end: ask a question in French → receive a grounded French answer with citations to actual Congolese law articles.

---

## Phase 3: Features for PPDS (Weeks 7–9)

Build features specifically designed for the NGO's mission — citizen access to law.

---

### Week 7 — Plain-Language Summaries ("Vulgarisation Juridique")

This directly serves PPDS's stated mission of making law accessible.

**Two summary types:**

**Type 1: Document summary** (generated once per document, stored)
- Input: Full text of a law/decree
- Output: 3-paragraph summary:
  - Paragraph 1: "Ce texte concerne..." (what this law is about)
  - Paragraph 2: "Ce que ça change pour les citoyens..." (practical impact)
  - Paragraph 3: "Les points importants à retenir..." (key obligations/rights)

**Type 2: Article explainer** (on-demand)
- User clicks any article → gets plain-language explanation
- Example: Article 15 of the Code de la Famille → "En termes simples, cet article dit que..."

**Model:** `facebook/mbart-large-cc25` (multilingual summarization) or prompt-based with the Anthropic API

**Store summaries:**
```sql
CREATE TABLE document_summaries (
  id UUID PRIMARY KEY,
  document_id UUID REFERENCES legal_documents(id),
  summary_type VARCHAR(20),  -- 'executive', 'citizen', 'article'
  summary_text TEXT,
  target_article TEXT,       -- NULL for full-doc summaries
  generated_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Deliverable:** Every major law on leganet.cd has a citizen-readable summary. This alone is a massive donation to PPDS.

---

### Week 8 — Legal Template Assistant

PPDS has legal form templates (contrat de bail, actes d'état civil). Make them interactive.

**Features:**
- Upload or select a model document from the site
- AI explains each field: "Ce champ demande..." → tells user what info to provide
- Guided fill-out: ask user for their information, generate a completed draft
- Warn about fields that require a notary or official stamp

**Why this matters:** In DRC, many citizens sign contracts they don't understand. An interactive guide to a standard bail contract could prevent thousands of legal disputes.

**Implementation:**
- Parse the Word/PDF templates from leganet.cd (`Modeles.htm`)
- Extract field structure using document QA
- Build a step-by-step form UI in Next.js
- Generate filled preview (not legally binding — always add a disclaimer)

**Deliverable:** Working interactive assistant for the contrat de bail template, which is the most commonly needed document.

---

### Week 9 — Search Interface & Document Browser

Build the primary interface for lawyers and researchers who need to navigate the corpus.

**Search features:**
- Semantic search across all 140 years of legislation
- Filters: domain, document type, date range, province
- "Find similar articles" — given an article, find related provisions in other laws
- Highlight matched passages in results

**Document browser:**
- Replicate leganet.cd's chronological index but with AI enhancements
- Each document card shows: title, date, domain tag, citizen summary preview
- Full text view with article-level navigation sidebar

**Deliverable:** A search UI that works better than the current keyword search on leganet.cd.

---

## Phase 4: Polish & Handoff (Weeks 10–12)

Build for sustainability — this is a donation, so PPDS must be able to maintain it.

---

### Week 10 — Safety, Disclaimers & Responsible AI

This is non-negotiable for a legal aid tool.

**Required safety features:**
- Every answer includes: "Ceci est une information juridique générale. Pour votre situation spécifique, consultez un avocat ou un magistrat."
- System refuses to give specific legal strategy advice ("Dois-je plaider coupable?")
- All answers clearly cite their sources with links back to leganet.cd
- Log all queries for review (with privacy: no PII stored)
- Rate limiting to prevent abuse

**User trust features:**
- Show the exact legal text retrieved alongside every answer
- Allow users to flag incorrect or misleading answers
- "Je ne sais pas" fallback when no relevant law is found

**Localization notes:**
- Primary language: French
- Consider adding Lingala or Swahili interface labels (not full translation — just UI text)
- Right-to-left is not needed (French is LTR)

---

### Week 11 — Deployment on a Budget

The system must run cheaply so PPDS doesn't need server expertise.

**Recommended free/cheap deployment:**

Option A (easiest): Railway.app
- Deploys Docker Compose directly
- Free tier: 5GB RAM, enough for the API + worker + pgvector
- PostgreSQL plugin: $5/month after free tier

Option B (more control): Render.com
- Similar to Railway, Docker-native
- Free PostgreSQL for 90 days, then $7/month

**Model hosting:**
- Do NOT run heavy models (7B+) on the same server as the API
- Use the Anthropic API for generation (free tier is generous)
- Run `multilingual-e5-large` for embeddings locally (384MB, CPU-feasible)
- Pre-compute all embeddings during setup — no inference at query time for retrieval

**Estimated monthly cost for PPDS:** $7–15/month for the database. API generation is free under normal NGO usage.

---

### Week 12 — Donation Handoff

This week is entirely about documentation and handing off something PPDS can actually use and maintain.

**Handoff package:**
1. **README.md** in French: What this is, how to use it, who to contact for help
2. **SETUP.md**: How to deploy from scratch in under 1 hour using Docker
3. **SCRAPER.md**: How to re-run the scraper when PPDS adds new laws (they can do this monthly)
4. **MODELS.md**: Which models are used and why — so future volunteers can upgrade them
5. **Demo video** (3 minutes): Screen recording showing a citizen question → grounded legal answer
6. **Contact email** to you for 3 months of post-donation support

**What to ask PPDS for in return:**
- A mention on their "Nos partenaires" page (great for your portfolio)
- Permission to publish your architecture and approach as a blog post or research preprint
- Feedback from their users so you can improve it

---

## Appendix A: Key Technical Decisions Summary

| Decision | Choice | Reason |
|----------|--------|--------|
| Embedding model | `intfloat/multilingual-e5-large` | Proven on French legal RAG (Harvard experiment) |
| French NLP base | CamemBERT / mDeBERTa | State-of-the-art French language models |
| Vector store | pgvector on PostgreSQL | No extra infrastructure; SQL joins still work |
| Generation | Anthropic API (Claude) | Quality + free for NGO/education scale |
| Retrieval | Hybrid BM25 + semantic | Legal text has precise terminology BM25 handles well |
| Chunking | Article-level | Matches Congolese legal document structure |
| Scraping | BeautifulSoup + rate limiting | Respectful of PPDS's server |
| Language | French throughout | All content and users are French-speaking |

---

## Appendix B: Resume Statement

> **JusticeCongo AI** — Donated Legal Aid Intelligence Platform
> Built and donated an open-source Congolese legal AI assistant to PPDS/LEGANET.CD, a Congolese NGO. Implemented a hybrid RAG pipeline (BM25 + pgvector semantic search) over 140 years of Congolese legislation, using `intfloat/multilingual-e5-large` embeddings and French NLP (CamemBERT, mDeBERTa zero-shot classification). Features include grounded French Q&A with article citations, plain-language legal summaries ("vulgarisation juridique"), and semantic search across 8 legal domains. Processes the entire leganet.cd corpus of 2,000+ documents. Deployed as a gift to the organization.
>
> **Stack:** Python, FastAPI, Celery, PostgreSQL + pgvector, Next.js, Hugging Face Transformers, Docker, BeautifulSoup, Anthropic API.

---

## Appendix C: Suggested Email to PPDS

Subject: Collaboration — Outil IA gratuit basé sur LEGANET.CD

Bonjour,

Je suis étudiant en informatique et intelligence artificielle à la Handong Global University (Corée du Sud). J'ai découvert LEGANET.CD et je suis profondément admiratif de votre travail de mise en ligne gratuite du droit congolais.

Je souhaite réaliser un projet de portfolio consistant à construire un assistant juridique basé sur l'IA, entièrement fondé sur les textes de votre site — et vous offrir le résultat en donation.

Concrètement, l'outil permettrait à n'importe quel citoyen de poser une question en français ("Puis-je être expulsé sans préavis ?") et d'obtenir une réponse citant les textes exacts de LEGANET.CD.

Avant de commencer, je souhaitais :
1. Obtenir votre accord pour utiliser les textes de votre site
2. Savoir si vous disposez de fichiers exportables de votre corpus
3. Vous soumettre mon plan de travail pour validation

Bien cordialement,
Christopher
