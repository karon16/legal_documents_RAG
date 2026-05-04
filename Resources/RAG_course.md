# RAG Implementation Guide
## Based on: freeCodeCamp — "RAG & MCP Fundamentals: A Hands-On Crash Course" (Jan 2026)
## Course link: https://www.youtube.com/watch?v=I7_WXKhyGms

---

## What This Document Is

A step-by-step implementation reference derived from the freeCodeCamp RAG crash course. Each section maps to a chapter in the video, translated into working Python code with explanations of every decision. Written specifically to serve as the engineering foundation for the **JusticeCongo AI** RAG pipeline, but applicable to any French or multilingual legal corpus.

---

## Table of Contents

1. [What RAG Is (and When to Use It)](#1-what-rag-is-and-when-to-use-it)
2. [Keyword Search: TF-IDF and BM25](#2-keyword-search-tf-idf-and-bm25)
3. [Semantic Search and Embeddings](#3-semantic-search-and-embeddings)
4. [Vector Databases: Chroma and pgvector](#4-vector-databases-chroma-and-pgvector)
5. [Document Chunking Strategies](#5-document-chunking-strategies)
6. [The Complete RAG Pipeline](#6-the-complete-rag-pipeline)
7. [Production Concerns: Caching, Monitoring, Error Handling](#7-production-concerns-caching-monitoring-error-handling)
8. [JusticeCongo AI: Applying It All](#8-justicecongo-ai-applying-it-all)

---

## 1. What RAG Is (and When to Use It)

### The Core Idea

A large language model has fixed knowledge — it knows what was in its training data, and nothing more. RAG (Retrieval-Augmented Generation) solves the problem of connecting an LLM to *your* data by doing three things before generation happens:

```
User Question
      │
      ▼
[RETRIEVE] → Search a knowledge base for relevant passages
      │
      ▼
[AUGMENT]  → Inject those passages into the LLM prompt as context
      │
      ▼
[GENERATE] → LLM answers the question using the retrieved context
```

The LLM never memorizes your data. It reads it at inference time, just like a human reading a document before answering a question.

### When to Use RAG vs. The Alternatives

The course draws a clear three-way distinction:

| Technique | Best For | Example |
|-----------|----------|---------|
| **Prompt Engineering** | Static, small context — facts that fit in one prompt | "Always respond in formal French" |
| **Fine-Tuning** | Changing the model's *style*, *voice*, or *reasoning pattern* | Training a model to write in legal register |
| **RAG** | Dynamic, large, frequently updated factual information | 140 years of Congolese legislation |

**The key insight from the course:** Fine-tuning teaches a model *how* to behave. RAG gives a model *what* to know. For legal text where accuracy and citation matter above all, RAG is the correct choice. Fine-tuning a model on Congolese law would make it speak like a Congolese lawyer — RAG makes it answer from actual Congolese law texts.

### The Real-World Use Case (from the course)

The course's running example is an **internal policy chatbot**: a company has hundreds of policy documents that change quarterly. Fine-tuning would require re-training every time a policy changes. Prompt stuffing would overflow the context window. RAG retrieves only the relevant policies on demand.

For JusticeCongo AI, the parallel is exact: LEGANET.CD has 2,000+ documents spanning 1883–2023. New decrees are added periodically. RAG with a re-runnable scraper + embedding pipeline handles updates naturally.

---

## 2. Keyword Search: TF-IDF and BM25

### Why the Course Starts Here

The course begins with keyword search, not embeddings. This is intentional: understanding *why* keyword search fails on certain queries is what motivates semantic search. It also motivates hybrid retrieval — the combination of both — which is what production RAG systems actually use.

### TF-IDF

TF-IDF (Term Frequency–Inverse Document Frequency) ranks documents by how *specifically* a term appears in a document relative to all documents.

```python
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

# Example corpus (would be your legal chunks in practice)
corpus = [
    "Le contrat de bail est régi par les articles 1 à 45 du code civil.",
    "L'expulsion du locataire nécessite une décision judiciaire.",
    "Le propriétaire doit donner un préavis de trois mois.",
    "La résiliation du contrat peut intervenir en cas de non-paiement.",
]

# Build TF-IDF matrix
vectorizer = TfidfVectorizer(
    language='french',       # French stopword removal
    ngram_range=(1, 2),      # Unigrams and bigrams
    max_df=0.85,             # Ignore terms appearing in >85% of docs
    min_df=1
)
tfidf_matrix = vectorizer.fit_transform(corpus)

def keyword_search_tfidf(query: str, top_k: int = 3):
    query_vec = vectorizer.transform([query])
    scores = cosine_similarity(query_vec, tfidf_matrix).flatten()
    top_indices = scores.argsort()[-top_k:][::-1]
    return [(corpus[i], scores[i]) for i in top_indices if scores[i] > 0]

# Test
results = keyword_search_tfidf("préavis expulsion locataire")
for text, score in results:
    print(f"Score: {score:.3f} | {text}")
```

**TF-IDF limitation (the "vocabulary mismatch" problem):**
```python
# This query will FAIL to find the relevant document
results = keyword_search_tfidf("peut-on me mettre dehors sans avertissement?")
# "mettre dehors" ≠ "expulsion" in TF-IDF's vocabulary
# "avertissement" ≠ "préavis" — same concept, different word
# TF-IDF finds zero matches. A citizen's natural language query fails.
```

This is exactly the problem that motivates semantic search.

### BM25

BM25 (Best Match 25) is the gold standard for keyword retrieval — it's what powers Elasticsearch and most production search engines. It improves over TF-IDF by adding term saturation (a term appearing 100 times isn't 100x more relevant than once) and document length normalization (longer documents aren't unfairly rewarded).

```bash
pip install rank-bm25
```

```python
from rank_bm25 import BM25Okapi
import re

def tokenize_french(text: str) -> list[str]:
    """Simple French tokenizer: lowercase, remove punctuation, split."""
    text = text.lower()
    text = re.sub(r'[^\w\s]', ' ', text)
    # In production: use NLTK French stopwords or spaCy fr_core_news_sm
    stopwords = {'le', 'la', 'les', 'de', 'du', 'des', 'un', 'une', 
                 'et', 'en', 'à', 'au', 'aux', 'est', 'par', 'pour',
                 'que', 'qui', 'dans', 'sur', 'avec', 'il', 'elle'}
    tokens = [w for w in text.split() if w not in stopwords and len(w) > 2]
    return tokens

# Tokenize corpus
tokenized_corpus = [tokenize_french(doc) for doc in corpus]

# Build BM25 index
bm25 = BM25Okapi(tokenized_corpus)

def keyword_search_bm25(query: str, top_k: int = 3):
    tokenized_query = tokenize_french(query)
    scores = bm25.get_scores(tokenized_query)
    top_indices = scores.argsort()[-top_k:][::-1]
    return [(corpus[i], scores[i]) for i in top_indices if scores[i] > 0]

# BM25 is better but still fails on vocabulary mismatch
results = keyword_search_bm25("expulsion préavis")
```

**Why BM25 still matters for legal text:**
Legal documents use precise terminology. When a user asks "Article 15 du code civil congolais", BM25 will find it exactly. Semantic search might retrieve Article 15 of a *different* code if the meaning is similar. **For legal text, you need both BM25 and semantic search** — this is hybrid retrieval, covered in section 6.

---

## 3. Semantic Search and Embeddings

### The Core Concept

An embedding model converts text into a vector of numbers (a point in high-dimensional space) such that semantically similar texts are geometrically close together.

```
"expulsion du locataire"     → [0.23, -0.87, 0.45, ...]   ←──┐ close in
"mettre dehors sans préavis" → [0.21, -0.83, 0.47, ...]   ←──┘ vector space

"recette de tarte aux pommes" → [-0.91, 0.12, -0.64, ...]  ←── far away
```

The course explains three key parameters for choosing an embedding model:

| Parameter | What It Means | JusticeCongo Choice |
|-----------|---------------|---------------------|
| **Parameter size** | Larger = better quality, slower, more VRAM | `multilingual-e5-large` (560M params) |
| **Local vs. API** | Local = free, private; API = managed, costs money | Local (legal texts are sensitive) |
| **Multilingual** | Can embed French and other languages | Yes — required for French corpus |

### Implementing Semantic Search with Sentence Transformers

```bash
pip install sentence-transformers
```

```python
from sentence_transformers import SentenceTransformer
import numpy as np

# Load the multilingual model (downloads ~2GB on first run)
# This is the exact model used in Harvard's Open French Law RAG experiment
model = SentenceTransformer('intfloat/multilingual-e5-large')

# CRITICAL: multilingual-e5 requires prefix tokens
# "query: " for questions, "passage: " for documents to index
def embed_query(text: str) -> np.ndarray:
    return model.encode(f"query: {text}", normalize_embeddings=True)

def embed_passage(text: str) -> np.ndarray:
    return model.encode(f"passage: {text}", normalize_embeddings=True)

# Embed the corpus (do this once, store in database)
passages = [
    "Le contrat de bail est régi par les articles 1 à 45 du code civil.",
    "L'expulsion du locataire nécessite une décision judiciaire.",
    "Le propriétaire doit donner un préavis de trois mois.",
    "La résiliation du contrat peut intervenir en cas de non-paiement.",
]
passage_embeddings = np.array([embed_passage(p) for p in passages])
```

### Vector Similarity: Dot Product and Cosine Similarity

The course covers the math behind similarity. Since `multilingual-e5-large` returns normalized vectors, dot product and cosine similarity are equivalent (cosine similarity of unit vectors equals their dot product).

```python
def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """For normalized vectors, this equals the dot product."""
    return float(np.dot(a, b))

def semantic_search(query: str, top_k: int = 3) -> list[tuple[str, float]]:
    query_embedding = embed_query(query)
    
    # Compute similarity of query against all passage embeddings
    similarities = np.dot(passage_embeddings, query_embedding)
    
    # Get top-k indices sorted by descending similarity
    top_indices = similarities.argsort()[-top_k:][::-1]
    
    return [(passages[i], float(similarities[i])) for i in top_indices]

# Now the vocabulary mismatch problem is SOLVED
results = semantic_search("peut-on me mettre dehors sans avertissement?")
# "mettre dehors sans avertissement" maps close to
# "expulsion du locataire nécessite une décision judiciaire"
# in embedding space — even though the words are different.

for text, score in results:
    print(f"Score: {score:.4f} | {text}")
```

### When Semantic Search Fails

The course is honest about semantic search limitations:

```python
# Semantic search can FAIL on precise legal identifiers
results = semantic_search("Article 847 du code de procédure civile")
# An embedding model might retrieve semantically similar articles
# instead of the EXACT article 847. For exact legal citations,
# BM25 keyword search is more reliable.
# → This motivates hybrid retrieval.
```

---

## 4. Vector Databases: Chroma and pgvector

At scale (thousands to millions of documents), computing cosine similarity against every document in memory is too slow. Vector databases solve this with **indexing algorithms** that allow approximate nearest neighbor (ANN) search in milliseconds.

### Indexing Algorithms (from the course)

**HNSW (Hierarchical Navigable Small World)**
- Builds a multi-layer graph of vectors
- Traverses from coarse to fine layers to find neighbors
- Best recall/speed tradeoff for most use cases
- Used by pgvector and Chroma

**IVF (Inverted File Index)**
- Clusters vectors into `nlist` Voronoi cells
- At query time, only searches `nprobe` nearest cells
- Faster than HNSW but lower recall; requires training phase
- Used by FAISS

**LSH (Locality Sensitive Hashing)**
- Hashes similar vectors into the same buckets
- Very fast but lowest recall
- Good for very large-scale approximate search

**For JusticeCongo AI:** HNSW via pgvector. The corpus is ~50,000 chunks — small enough that recall matters more than raw speed.

### Option A: ChromaDB (Easy, In-Memory/Local)

The course uses Chroma for its hands-on labs. Good for prototyping.

```bash
pip install chromadb
```

```python
import chromadb
from chromadb.utils import embedding_functions

# Initialize Chroma (persistent on disk)
client = chromadb.PersistentClient(path="./chroma_db")

# Use sentence-transformers embedding function
ef = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="intfloat/multilingual-e5-large"
)

# Create a collection (like a table in SQL)
collection = client.get_or_create_collection(
    name="congolese_law",
    embedding_function=ef,
    metadata={"hnsw:space": "cosine"}  # Use cosine similarity
)

# Add documents with metadata
collection.add(
    documents=passages,
    metadatas=[
        {"domain": "droit_civil", "doc_type": "loi", "article": "Art. 1"},
        {"domain": "droit_civil", "doc_type": "loi", "article": "Art. 12"},
        {"domain": "droit_civil", "doc_type": "decret", "article": "Art. 3"},
        {"domain": "droit_commercial", "doc_type": "loi", "article": "Art. 7"},
    ],
    ids=["chunk_001", "chunk_002", "chunk_003", "chunk_004"]
)

# Query with optional metadata filter
results = collection.query(
    query_texts=["peut-on expulser un locataire sans préavis?"],
    n_results=3,
    where={"domain": "droit_civil"}  # Filter by legal domain
)

for doc, meta, dist in zip(
    results['documents'][0],
    results['metadatas'][0],
    results['distances'][0]
):
    print(f"Distance: {dist:.4f} | {meta['article']} | {doc[:80]}...")
```

### Option B: pgvector (Production, SQL-Native)

For JusticeCongo AI, pgvector is the right choice because:
- All other data (documents, entities, summaries) is already in PostgreSQL
- You can combine vector search with SQL filters (domain, date range, doc_type) in a single query
- No extra infrastructure required

```sql
-- Enable extension (run once)
CREATE EXTENSION IF NOT EXISTS vector;

-- Table with embedding column
CREATE TABLE document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES legal_documents(id),
    chunk_index INTEGER,
    text TEXT NOT NULL,
    article_number TEXT,
    domain VARCHAR(50),
    doc_type VARCHAR(30),
    date_enacted DATE,
    embedding VECTOR(1024),   -- 1024 dims for multilingual-e5-large
    metadata JSONB
);

-- HNSW index for fast approximate nearest neighbor search
CREATE INDEX ON document_chunks
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Full-text search index for hybrid retrieval (French language)
CREATE INDEX ON document_chunks
USING GIN (to_tsvector('french', text));
```

```python
import psycopg2
from psycopg2.extras import execute_values
import numpy as np

class PgVectorStore:
    def __init__(self, connection_string: str):
        self.conn = psycopg2.connect(connection_string)
        self.model = SentenceTransformer('intfloat/multilingual-e5-large')
    
    def add_chunks(self, chunks: list[dict]):
        """Insert chunks with pre-computed embeddings."""
        texts = [f"passage: {c['text']}" for c in chunks]
        embeddings = self.model.encode(texts, batch_size=32, normalize_embeddings=True)
        
        rows = [
            (
                c['document_id'],
                c['chunk_index'],
                c['text'],
                c.get('article_number'),
                c.get('domain'),
                c.get('doc_type'),
                c.get('date_enacted'),
                embedding.tolist(),
            )
            for c, embedding in zip(chunks, embeddings)
        ]
        
        with self.conn.cursor() as cur:
            execute_values(cur, """
                INSERT INTO document_chunks
                (document_id, chunk_index, text, article_number, domain, 
                 doc_type, date_enacted, embedding)
                VALUES %s
            """, rows)
        self.conn.commit()
    
    def semantic_search(
        self, 
        query: str, 
        top_k: int = 5,
        domain_filter: str = None
    ) -> list[dict]:
        """Pure semantic search via pgvector cosine similarity."""
        query_embedding = self.model.encode(
            f"query: {query}", normalize_embeddings=True
        ).tolist()
        
        filter_clause = ""
        params = [query_embedding, query_embedding, top_k]
        
        if domain_filter:
            filter_clause = "WHERE domain = %s"
            params = [query_embedding, query_embedding, domain_filter, top_k]
        
        with self.conn.cursor() as cur:
            cur.execute(f"""
                SELECT 
                    text,
                    article_number,
                    domain,
                    doc_type,
                    date_enacted,
                    1 - (embedding <=> %s::vector) AS similarity_score
                FROM document_chunks
                {filter_clause}
                ORDER BY embedding <=> %s::vector
                LIMIT %s
            """, params)
            
            cols = ['text', 'article_number', 'domain', 'doc_type', 'date_enacted', 'score']
            return [dict(zip(cols, row)) for row in cur.fetchall()]
```

---

## 5. Document Chunking Strategies

### The Precision Problem

The course calls this the most underappreciated part of RAG. If you embed an entire 50-page law as a single document, the embedding averages out the meaning of every article. A question about Article 12 might retrieve a document where Article 12 is buried on page 30, surrounded by irrelevant content about Article 1 to 45. The retrieval model cannot "zoom in" — it retrieves the whole document or nothing.

**Rule of thumb from the course:** Chunk size should match the granularity of your queries.

- User asks about a specific article → chunk at article level
- User asks about a legal concept across a law → chunk at section/chapter level
- User asks for a broad overview → whole document summary (not retrieved, generated)

### Strategy 1: Fixed-Size Chunking with Overlap

Simple, fast, works as a baseline. Splits by token count with overlap to avoid cutting concepts mid-sentence.

```python
from transformers import AutoTokenizer

tokenizer = AutoTokenizer.from_pretrained("intfloat/multilingual-e5-large")

def fixed_size_chunks(
    text: str,
    chunk_size: int = 512,    # tokens
    overlap: int = 50          # tokens of overlap between chunks
) -> list[str]:
    tokens = tokenizer.encode(text, add_special_tokens=False)
    chunks = []
    
    start = 0
    while start < len(tokens):
        end = min(start + chunk_size, len(tokens))
        chunk_tokens = tokens[start:end]
        chunk_text = tokenizer.decode(chunk_tokens, skip_special_tokens=True)
        chunks.append(chunk_text)
        
        if end == len(tokens):
            break
        start = end - overlap  # Step back by overlap amount
    
    return chunks

# Example
text = "Article 1: Le contrat est formé par l'accord des parties..." * 50
chunks = fixed_size_chunks(text)
print(f"Created {len(chunks)} chunks from {len(text)} characters")
```

**Problem with fixed-size chunking for legal text:** An article might be cut in half. Article 12 starts at token 480 and ends at token 560 — the model embeds half an article in one chunk and the other half in the next.

### Strategy 2: Boundary-Aware Chunking (Best for Legal Text)

Split on legal document structure: articles, sections, chapters. This is what the course calls "semantic chunking" — respecting the natural boundaries of the content.

```python
import re
from dataclasses import dataclass

@dataclass
class LegalChunk:
    text: str
    article_number: str | None
    chapter: str | None
    chunk_index: int

def chunk_by_article(document_text: str, document_id: str) -> list[LegalChunk]:
    """
    Splits a Congolese legal document by article number.
    Handles patterns like:
      - "Article 1:" / "Article premier:"
      - "Art. 12 —"
      - "ARTICLE 15."
    """
    # Pattern covers common Congolese legal document article markers
    article_pattern = re.compile(
        r'(?:^|\n)'                          # Start of line
        r'(?:ARTICLE|Article|Art\.)\s+'      # Keyword
        r'(\d+|premier|[IVXLCDM]+)'         # Number (arabic, "premier", roman)
        r'[.\-:\s]',                         # Separator
        re.MULTILINE
    )
    
    chapter_pattern = re.compile(
        r'(?:^|\n)'
        r'(?:CHAPITRE|Chapitre|SECTION|Section)\s+'
        r'([IVXLCDM]+|\d+)'
        r'[.\-:\s]*(.*?)(?=\n)',
        re.MULTILINE
    )
    
    # Find all article positions
    matches = list(article_pattern.finditer(document_text))
    
    if not matches:
        # No article structure detected — fall back to fixed-size
        return [LegalChunk(
            text=chunk, 
            article_number=None, 
            chapter=None, 
            chunk_index=i
        ) for i, chunk in enumerate(fixed_size_chunks(document_text))]
    
    chunks = []
    current_chapter = None
    
    for i, match in enumerate(matches):
        article_number = match.group(1)
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(document_text)
        
        chunk_text = document_text[start:end].strip()
        
        # Look for chapter heading before this article
        preceding_text = document_text[
            (matches[i-1].end() if i > 0 else 0):start
        ]
        chapter_match = chapter_pattern.search(preceding_text)
        if chapter_match:
            current_chapter = chapter_match.group(2).strip()
        
        # Enforce max chunk size (long articles still get split)
        if len(chunk_text) > 2000:
            sub_chunks = fixed_size_chunks(chunk_text, chunk_size=400, overlap=40)
            for j, sub in enumerate(sub_chunks):
                chunks.append(LegalChunk(
                    text=sub,
                    article_number=f"{article_number}.{j+1}",
                    chapter=current_chapter,
                    chunk_index=len(chunks)
                ))
        else:
            chunks.append(LegalChunk(
                text=chunk_text,
                article_number=article_number,
                chapter=current_chapter,
                chunk_index=len(chunks)
            ))
    
    return chunks

# Usage
with open("loi_bail.txt", "r", encoding="utf-8") as f:
    law_text = f.read()

chunks = chunk_by_article(law_text, document_id="doc_001")
print(f"Extracted {len(chunks)} article-level chunks")
for chunk in chunks[:3]:
    print(f"  Article {chunk.article_number} ({chunk.chapter}): {chunk.text[:80]}...")
```

### Strategy 3: Overlap Between Boundary Chunks

Even with article-level chunking, context from the previous article sometimes matters (e.g., a definition established in Article 1 applies to Article 12). The course recommends adding a "context prefix" from the surrounding chunk.

```python
def add_context_prefix(chunks: list[LegalChunk], window: int = 1) -> list[LegalChunk]:
    """
    Prepends the last N sentences of the previous chunk to each chunk.
    Gives the embedding model context about what came before.
    """
    enriched = []
    for i, chunk in enumerate(chunks):
        if i == 0:
            enriched.append(chunk)
            continue
        
        prev_text = chunks[i - 1].text
        # Take last 2 sentences of previous chunk as context
        sentences = re.split(r'(?<=[.!?])\s+', prev_text)
        context = ' '.join(sentences[-2:]) if len(sentences) >= 2 else prev_text[-200:]
        
        enriched.append(LegalChunk(
            text=f"[Contexte: {context}]\n\n{chunk.text}",
            article_number=chunk.article_number,
            chapter=chunk.chapter,
            chunk_index=chunk.chunk_index
        ))
    
    return enriched
```

---

## 6. The Complete RAG Pipeline

### Architecture Overview

The course assembles all previous components into a single end-to-end pipeline. Here it is adapted for French legal text:

```
User Question (French)
        │
        ▼
  ┌─────────────────────────────────────────┐
  │           RETRIEVAL LAYER               │
  │                                         │
  │  ┌──────────────┐  ┌─────────────────┐  │
  │  │  BM25 Search │  │ Semantic Search │  │
  │  │  (keywords)  │  │  (pgvector)     │  │
  │  └──────┬───────┘  └────────┬────────┘  │
  │         │                   │           │
  │         └──────┬────────────┘           │
  │                ▼                        │
  │    Reciprocal Rank Fusion (merge)       │
  │                │                        │
  │         Top-5 Chunks                   │
  └────────────────┼────────────────────────┘
                   │
                   ▼
  ┌────────────────────────────────────────┐
  │            AUGMENT LAYER              │
  │                                        │
  │  Prompt Template:                      │
  │  "Basé sur ces extraits de loi..."     │
  │  + Retrieved chunks with citations     │
  │  + User question                       │
  └────────────────┬───────────────────────┘
                   │
                   ▼
  ┌────────────────────────────────────────┐
  │           GENERATION LAYER             │
  │                                        │
  │  LLM (Claude / Mistral / local)        │
  │  → French answer with article citations│
  └────────────────┬───────────────────────┘
                   │
                   ▼
          Answer + Sources
```

### Hybrid Retrieval: Reciprocal Rank Fusion

The course explains that neither BM25 nor semantic search alone is optimal. Hybrid retrieval merges both ranked lists using Reciprocal Rank Fusion (RRF), which is robust because it doesn't require normalizing scores between the two systems.

```python
from typing import Any

def reciprocal_rank_fusion(
    ranked_lists: list[list[tuple[str, Any]]],
    k: int = 60
) -> list[tuple[str, float]]:
    """
    Merges multiple ranked lists using RRF.
    k=60 is the standard constant from the original RRF paper.
    
    Each input list is [(chunk_text, score), ...] sorted by descending score.
    Returns merged list sorted by RRF score.
    """
    rrf_scores: dict[str, float] = {}
    
    for ranked_list in ranked_lists:
        for rank, (text, _score) in enumerate(ranked_list):
            if text not in rrf_scores:
                rrf_scores[text] = 0.0
            rrf_scores[text] += 1.0 / (k + rank + 1)
    
    return sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)


class HybridRetriever:
    def __init__(self, vector_store: PgVectorStore, bm25_corpus: list[str]):
        self.vector_store = vector_store
        self.bm25 = BM25Okapi([tokenize_french(doc) for doc in bm25_corpus])
        self.corpus = bm25_corpus
    
    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        domain_filter: str = None
    ) -> list[dict]:
        # 1. Semantic retrieval
        semantic_results = self.vector_store.semantic_search(
            query, top_k=top_k * 2, domain_filter=domain_filter
        )
        semantic_ranked = [(r['text'], r['score']) for r in semantic_results]
        
        # 2. BM25 retrieval
        tokenized_query = tokenize_french(query)
        bm25_scores = self.bm25.get_scores(tokenized_query)
        bm25_top_indices = bm25_scores.argsort()[-(top_k * 2):][::-1]
        bm25_ranked = [
            (self.corpus[i], bm25_scores[i]) 
            for i in bm25_top_indices 
            if bm25_scores[i] > 0
        ]
        
        # 3. Merge with RRF
        merged = reciprocal_rank_fusion([semantic_ranked, bm25_ranked])
        
        # 4. Return top-k with full metadata
        top_texts = {text for text, _ in merged[:top_k]}
        return [r for r in semantic_results if r['text'] in top_texts][:top_k]
```

### Prompt Engineering for Legal RAG

The prompt is where RAG answers go wrong most often. The course emphasizes four principles: **grounding** (answer only from context), **citation** (always name the source), **honesty** (admit when you don't know), and **safety** (disclaim professional advice).

```python
SYSTEM_PROMPT = """Tu es un assistant juridique spécialisé dans le droit congolais.
Tu as accès à une base de données de textes légaux provenant de LEGANET.CD.

RÈGLES ABSOLUES:
1. Tu ne réponds QUE sur la base des extraits fournis. Pas d'inventions.
2. Tu cites TOUJOURS l'article exact (ex: "Article 12 de la loi du 15 mars 1990").
3. Si la réponse n'est pas dans les extraits, tu dis clairement:
   "Cette information ne figure pas dans les textes disponibles."
4. Tu NE fournis PAS de conseil juridique personnalisé.
5. Tu termines TOUJOURS par: "Pour votre situation spécifique, 
   consultez un avocat ou contactez un magistrat."

Tu réponds en français simple et accessible, pas en jargon juridique."""

def build_rag_prompt(question: str, retrieved_chunks: list[dict]) -> list[dict]:
    """Build the messages array for the LLM API call."""
    
    # Format retrieved chunks as numbered sources
    context_parts = []
    for i, chunk in enumerate(retrieved_chunks, 1):
        source_label = (
            f"[Source {i}: {chunk.get('doc_type', 'Texte').title()}, "
            f"Article {chunk.get('article_number', 'N/A')}, "
            f"{chunk.get('domain', '').replace('_', ' ').title()}]"
        )
        context_parts.append(f"{source_label}\n{chunk['text']}")
    
    context = "\n\n---\n\n".join(context_parts)
    
    user_message = f"""Voici les extraits de loi pertinents :

{context}

---

Question : {question}"""
    
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_message}
    ]
```

### Putting It All Together: The End-to-End Pipeline

```python
import anthropic

class JusticeCongoRAG:
    def __init__(
        self,
        vector_store: PgVectorStore,
        bm25_corpus: list[str],
        anthropic_api_key: str
    ):
        self.retriever = HybridRetriever(vector_store, bm25_corpus)
        self.client = anthropic.Anthropic(api_key=anthropic_api_key)
    
    def answer(
        self,
        question: str,
        domain_filter: str = None,
        top_k: int = 5
    ) -> dict:
        """
        Full RAG pipeline:
        1. Retrieve relevant legal chunks
        2. Build augmented prompt
        3. Generate grounded French answer
        4. Return answer + sources
        """
        # Step 1: Retrieve
        chunks = self.retriever.retrieve(
            question, 
            top_k=top_k, 
            domain_filter=domain_filter
        )
        
        if not chunks:
            return {
                "answer": (
                    "Aucun texte de loi pertinent n'a été trouvé dans la base "
                    "de données pour cette question. "
                    "Consultez un avocat pour obtenir de l'aide."
                ),
                "sources": [],
                "retrieved_count": 0
            }
        
        # Step 2: Build prompt
        messages = build_rag_prompt(question, chunks)
        
        # Step 3: Generate
        response = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            messages=messages
        )
        
        answer_text = response.content[0].text
        
        # Step 4: Return structured response
        return {
            "answer": answer_text,
            "sources": [
                {
                    "article": c.get('article_number'),
                    "domain": c.get('domain'),
                    "doc_type": c.get('doc_type'),
                    "date": str(c.get('date_enacted', '')),
                    "excerpt": c['text'][:200] + "..."
                }
                for c in chunks
            ],
            "retrieved_count": len(chunks)
        }


# Usage
rag = JusticeCongoRAG(
    vector_store=PgVectorStore("postgresql://localhost/justicecongo"),
    bm25_corpus=all_chunk_texts,  # List of all chunk texts
    anthropic_api_key="sk-ant-..."
)

result = rag.answer(
    question="Un propriétaire peut-il expulser son locataire sans préavis?",
    domain_filter="droit_civil"
)

print(result["answer"])
print("\nSources:")
for s in result["sources"]:
    print(f"  - Article {s['article']} ({s['doc_type']}, {s['date']})")
```

---

## 7. Production Concerns: Caching, Monitoring, Error Handling

### Caching (3 Layers)

The course identifies three distinct caching opportunities, each with different TTLs:

```python
import hashlib
import json
import redis
from functools import wraps

redis_client = redis.Redis(host='localhost', port=6379, db=0)

# Layer 1: Query Cache (exact question match, TTL: 1 hour)
# Same question asked twice → return cached answer immediately
def cache_query(ttl: int = 3600):
    def decorator(func):
        @wraps(func)
        def wrapper(self, question: str, **kwargs):
            cache_key = f"query:{hashlib.md5(question.encode()).hexdigest()}"
            cached = redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
            result = func(self, question, **kwargs)
            redis_client.setex(cache_key, ttl, json.dumps(result))
            return result
        return wrapper
    return decorator

# Layer 2: Embedding Cache (TTL: 24 hours)
# Same text → same embedding, no need to re-encode
def get_cached_embedding(text: str, model) -> np.ndarray:
    cache_key = f"emb:{hashlib.md5(text.encode()).hexdigest()}"
    cached = redis_client.get(cache_key)
    if cached:
        return np.frombuffer(cached, dtype=np.float32)
    embedding = model.encode(text, normalize_embeddings=True)
    redis_client.setex(86400, cache_key, embedding.tobytes())
    return embedding

# Layer 3: LLM Response Cache (TTL: 6 hours)
# Same retrieved context + same question → same LLM answer
def get_cached_llm_response(context_hash: str, question: str, client) -> str | None:
    cache_key = f"llm:{context_hash}:{hashlib.md5(question.encode()).hexdigest()}"
    return redis_client.get(cache_key)
```

### Essential Metrics (from the course)

The course identifies three RAG-specific metrics that matter in production:

```python
import time
from dataclasses import dataclass

@dataclass
class RAGMetrics:
    retrieval_latency_ms: float       # Time to retrieve chunks
    generation_latency_ms: float      # Time for LLM response
    retrieved_chunk_count: int        # How many chunks were retrieved
    answer_has_citations: bool        # Did the answer cite sources?
    query_served_from_cache: bool     # Was it a cache hit?

def instrumented_answer(self, question: str, **kwargs) -> tuple[dict, RAGMetrics]:
    t0 = time.time()
    
    # Retrieval
    chunks = self.retriever.retrieve(question, **kwargs)
    retrieval_time = (time.time() - t0) * 1000
    
    # Generation
    t1 = time.time()
    messages = build_rag_prompt(question, chunks)
    response = self.client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        messages=messages
    )
    generation_time = (time.time() - t1) * 1000
    
    answer_text = response.content[0].text
    
    metrics = RAGMetrics(
        retrieval_latency_ms=retrieval_time,
        generation_latency_ms=generation_time,
        retrieved_chunk_count=len(chunks),
        answer_has_citations="Article" in answer_text,
        query_served_from_cache=False
    )
    
    # Log metrics (to PostgreSQL, or a monitoring service like Prometheus)
    log_metrics(question, metrics)
    
    return {"answer": answer_text, "sources": chunks}, metrics
```

### Error Handling

The course covers three failure modes for RAG pipelines:

```python
class RAGError(Exception):
    pass

class RetrievalError(RAGError):
    pass

class GenerationError(RAGError):
    pass

def safe_answer(self, question: str, **kwargs) -> dict:
    """Production-safe RAG with graceful degradation."""
    
    # Validate input
    if not question or len(question.strip()) < 5:
        return {"answer": "Veuillez poser une question plus détaillée.", "sources": []}
    
    if len(question) > 2000:
        return {"answer": "Votre question est trop longue. Veuillez la reformuler.", "sources": []}
    
    # Attempt retrieval with fallback
    try:
        chunks = self.retriever.retrieve(question, **kwargs)
    except Exception as e:
        # Log the error, attempt keyword-only fallback
        print(f"Vector retrieval failed: {e}, falling back to BM25 only")
        try:
            tokenized = tokenize_french(question)
            scores = self.retriever.bm25.get_scores(tokenized)
            top_idx = scores.argsort()[-5:][::-1]
            chunks = [{"text": self.retriever.corpus[i], "score": scores[i]} for i in top_idx]
        except Exception as e2:
            raise RetrievalError(f"Both retrieval methods failed: {e2}")
    
    if not chunks:
        return {
            "answer": (
                "Aucun texte pertinent n'a été trouvé pour cette question. "
                "Essayez de reformuler avec des termes juridiques plus précis, "
                "ou consultez directement leganet.cd."
            ),
            "sources": []
        }
    
    # Attempt generation with retry
    for attempt in range(3):
        try:
            messages = build_rag_prompt(question, chunks)
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1000,
                messages=messages
            )
            return {
                "answer": response.content[0].text,
                "sources": chunks
            }
        except anthropic.RateLimitError:
            time.sleep(2 ** attempt)  # Exponential backoff
        except anthropic.APIError as e:
            raise GenerationError(f"LLM generation failed: {e}")
    
    raise GenerationError("Generation failed after 3 attempts")
```

---

## 8. JusticeCongo AI: Applying It All

This section shows the complete initialization sequence for the JusticeCongo AI pipeline.

### Step 1: Ingest the LEGANET.CD Corpus (runs once, then on updates)

```python
import requests
from bs4 import BeautifulSoup
import time

def ingest_leganet_corpus(db_conn):
    """
    Full ingestion pipeline:
    Scrape → Parse → Chunk → Embed → Store
    """
    store = PgVectorStore(db_conn)
    
    # Scrape legislation index
    base_url = "https://www.leganet.cd"
    resp = requests.get(f"{base_url}/legislation.htm", 
                        headers={"User-Agent": "JusticeCongo-AI/1.0"})
    resp.encoding = 'iso-8859-1'  # Critical for French accented characters
    soup = BeautifulSoup(resp.text, 'html.parser')
    
    # Find all [Texte] links
    law_links = [
        base_url + a['href'] 
        for a in soup.find_all('a') 
        if a.text.strip() == 'Texte' and a.get('href')
    ]
    
    print(f"Found {len(law_links)} documents to ingest")
    
    all_chunks = []
    
    for url in law_links:
        time.sleep(2)  # Respectful rate limiting
        
        try:
            doc_resp = requests.get(url, headers={"User-Agent": "JusticeCongo-AI/1.0"})
            doc_resp.encoding = 'iso-8859-1'
            doc_soup = BeautifulSoup(doc_resp.text, 'html.parser')
            
            # Extract text (remove navigation, headers)
            body = doc_soup.find('body')
            if not body:
                continue
            
            # Remove navigation elements
            for nav in body.find_all(['nav', 'header', 'footer']):
                nav.decompose()
            
            raw_text = body.get_text(separator='\n', strip=True)
            
            # Chunk by article
            chunks = chunk_by_article(raw_text, document_id=url)
            chunks = add_context_prefix(chunks)
            
            # Prepare for storage
            for chunk in chunks:
                all_chunks.append({
                    "document_id": url,  # Use URL as ID for now
                    "chunk_index": chunk.chunk_index,
                    "text": chunk.text,
                    "article_number": chunk.article_number,
                    "domain": detect_domain(url),  # From URL path
                    "doc_type": detect_doc_type(raw_text),
                })
        
        except Exception as e:
            print(f"Failed to process {url}: {e}")
            continue
    
    # Batch embed and store (much faster than one-by-one)
    batch_size = 100
    for i in range(0, len(all_chunks), batch_size):
        batch = all_chunks[i:i+batch_size]
        store.add_chunks(batch)
        print(f"Stored chunks {i} to {i+len(batch)}")
    
    print(f"Ingestion complete. Total chunks: {len(all_chunks)}")
```

### Step 2: Run the RAG System

```python
# Initialize (after ingestion is complete)
rag = JusticeCongoRAG(
    vector_store=PgVectorStore("postgresql://user:pass@localhost/justicecongo"),
    bm25_corpus=fetch_all_chunk_texts(),   # Load from DB
    anthropic_api_key=os.getenv("ANTHROPIC_API_KEY")
)

# Example citizen queries
questions = [
    "Un propriétaire peut-il expulser son locataire sans décision judiciaire?",
    "Quels sont mes droits en cas de licenciement abusif?",
    "Comment contester une saisie de mes biens?",
    "Quelles sont les conditions pour enregistrer un mariage coutumier?"
]

for q in questions:
    print(f"\nQuestion: {q}")
    result = rag.answer(q)
    print(f"Réponse: {result['answer'][:300]}...")
    print(f"Sources ({len(result['sources'])}):")
    for s in result['sources']:
        print(f"  - {s.get('doc_type', 'Texte')}, Art. {s.get('article_number')}")
```

---

## Quick Reference: Key Design Decisions

| Decision | What the Course Recommends | JusticeCongo Choice | Why |
|----------|---------------------------|---------------------|-----|
| Chunk strategy | Match granularity to query type | Article-level | Legal Q&A is article-specific |
| Chunk overlap | 50–100 tokens | Context prefix from previous article | Preserves legal definitions across articles |
| Embedding model | Depends on language | `multilingual-e5-large` | Best French legal retrieval (Harvard validated) |
| Retrieval | Hybrid (BM25 + semantic) | pgvector + rank-bm25 + RRF | Legal text needs both exact and semantic matching |
| Vector index | HNSW for most cases | pgvector HNSW | Best recall for ~50K chunk corpus |
| Generation | Grounded prompts with citations | Claude API with strict system prompt | Accuracy + citation are non-negotiable for legal |
| Caching | 3 layers: query, embedding, LLM | Redis (already in stack for Celery) | Reduces latency and API costs |
| Error handling | Graceful degradation | BM25 fallback + no-answer response | Users deserve honest "I don't know" over hallucination |

---

*This guide covers the RAG portion of the freeCodeCamp "RAG & MCP Fundamentals" crash course (Jan 2026, 0:00 – 0:58:00). The MCP section (0:59:40 onward) is not covered here.*