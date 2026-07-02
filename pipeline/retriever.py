import logging
import math
from dataclasses import dataclass
from typing import Optional

import psycopg2
from psycopg2.extras import RealDictCursor
from pgvector.psycopg2 import register_vector

from pipeline.embedder import embed_query

logger = logging.getLogger(__name__)

# RRF constant — from the original 2009 paper by Cormack et al.
# Do not tune this unless you have a labeled evaluation set.
RRF_K = 60

# How many candidates to fetch from each retrieval method
# before merging. Fetching 2x top_k gives RRF enough signal
# to produce a good merged ranking.
CANDIDATE_MULTIPLIER = 2

@dataclass
class RetrievedChunk:
    chunk_id:        str
    text:            str
    article_number:  Optional[str]
    chapter_heading: Optional[str]
    document_title:  str
    domain:          str
    doc_type:        str
    date_enacted:    Optional[str]
    source_url:      str
    semantic_score:  float  # cosine similarity from pgvector (0–1)
    bm25_score:      float  # ts_rank from PostgreSQL (0–1, 0 if not in BM25)
    rrf_score:       float  # final merged score from RRF


def semantic_search(
    conn,
    query_embedding: list[float],
    top_k:           int = 10,
    domain_filter:   Optional[str] = None,
    doc_type_filter: Optional[str] = None,
) -> list[RetrievedChunk]:
    """
    Finds the top_k most semantically similar chunks using pgvector HNSW index.
    Uses cosine distance (<=> operator). Returns results sorted by similarity desc.
    """
    # Build WHERE clause dynamically based on filters provided
    conditions = ["dc.embedding IS NOT NULL"]
    where_params = []

    if domain_filter:
        conditions.append("ld.domain = %s")
        where_params.append(domain_filter)

    if doc_type_filter:
        conditions.append("ld.doc_type = %s")
        where_params.append(doc_type_filter)

    where_clause = " AND ".join(conditions)

    sql = f"""
        SELECT
            dc.id                                           AS chunk_id,
            dc.text,
            dc.article_number,
            dc.chapter_heading,
            ld.title                                        AS document_title,
            ld.domain,
            ld.doc_type,
            ld.date_enacted::text                          AS date_enacted,
            ld.source_url,
            1 - (dc.embedding <=> %s::vector)              AS semantic_score
        FROM document_chunks dc
        JOIN legal_documents ld ON dc.document_id = ld.id
        WHERE {where_clause}
        ORDER BY dc.embedding <=> %s::vector
        LIMIT %s
    """

    # params match the order of %s in the sql string:
    # 1. SELECT (query_embedding)
    # 2. WHERE (where_params)
    # 3. ORDER BY (query_embedding)
    # 4. LIMIT (top_k)
    params = [query_embedding] + where_params + [query_embedding, top_k]

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()

    return [
        RetrievedChunk(
            chunk_id        = str(row['chunk_id']),
            text            = row['text'],
            article_number  = row['article_number'],
            chapter_heading = row['chapter_heading'],
            document_title  = row['document_title'],
            domain          = row['domain'],
            doc_type        = row['doc_type'],
            date_enacted    = row['date_enacted'],
            source_url      = row['source_url'],
            semantic_score  = float(row['semantic_score']),
            bm25_score      = 0.0,   # filled in by RRF merge
            rrf_score       = 0.0,   # filled in by RRF merge
        )
        for row in rows
    ]


def bm25_search(
    conn,
    query:           str,
    top_k:           int = 10,
    domain_filter:   Optional[str] = None,
    doc_type_filter: Optional[str] = None,
) -> list[RetrievedChunk]:
    """
    Finds the top_k most relevant chunks using PostgreSQL French full-text search.
    Uses the GIN index on to_tsvector('french', text).
    Handles cases where the query produces no tsquery tokens gracefully.
    """
    # Convert natural language query into an OR query for BM25
    # e.g. "Mon bailleur peut-il" -> "Mon OR bailleur OR peut-il"
    or_query = " OR ".join(query.split())

    # websearch_to_tsquery is safer than to_tsquery — it never throws on
    # natural language input (no need to escape special characters)
    conditions = [
        "to_tsvector('french', dc.text) @@ websearch_to_tsquery('french', %s)",
        "dc.embedding IS NOT NULL"
    ]
    where_params = [or_query]

    if domain_filter:
        conditions.append("ld.domain = %s")
        where_params.append(domain_filter)

    if doc_type_filter:
        conditions.append("ld.doc_type = %s")
        where_params.append(doc_type_filter)

    where_clause = " AND ".join(conditions)

    sql = f"""
        SELECT
            dc.id                                           AS chunk_id,
            dc.text,
            dc.article_number,
            dc.chapter_heading,
            ld.title                                        AS document_title,
            ld.domain,
            ld.doc_type,
            ld.date_enacted::text                          AS date_enacted,
            ld.source_url,
            ts_rank(
                to_tsvector('french', dc.text),
                websearch_to_tsquery('french', %s)
            )                                               AS bm25_score
        FROM document_chunks dc
        JOIN legal_documents ld ON dc.document_id = ld.id
        WHERE {where_clause}
        ORDER BY bm25_score DESC
        LIMIT %s
    """

    # params match the order of %s in the sql string:
    # 1. SELECT (or_query for ts_rank)
    # 2. WHERE (where_params, which includes or_query for the first condition)
    # 3. LIMIT (top_k)
    params = tuple([or_query] + where_params + [top_k])

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()

    return [
        RetrievedChunk(
            chunk_id        = str(row['chunk_id']),
            text            = row['text'],
            article_number  = row['article_number'],
            chapter_heading = row['chapter_heading'],
            document_title  = row['document_title'],
            domain          = row['domain'],
            doc_type        = row['doc_type'],
            date_enacted    = row['date_enacted'],
            source_url      = row['source_url'],
            semantic_score  = 0.0,   # filled in by RRF merge
            bm25_score      = float(row['bm25_score']),
            rrf_score       = 0.0,   # filled in by RRF merge
        )
        for row in rows
    ]


def reciprocal_rank_fusion(
    semantic_results: list[RetrievedChunk],
    bm25_results:     list[RetrievedChunk],
    top_k:            int = 5,
) -> list[RetrievedChunk]:
    """
    Merges two ranked lists using Reciprocal Rank Fusion (Cormack et al. 2009).
    
    RRF score = sum of 1 / (k + rank) across all lists a chunk appears in.
    
    Chunks appearing in both lists get contributions from both,
    naturally boosting results that both retrieval methods agree on.
    """
    # Build a lookup of chunk_id → RetrievedChunk for all candidates
    all_chunks: dict[str, RetrievedChunk] = {}
    for chunk in semantic_results + bm25_results:
        if chunk.chunk_id not in all_chunks:
            all_chunks[chunk.chunk_id] = chunk
        # Merge scores into the existing entry
        else:
            all_chunks[chunk.chunk_id].semantic_score = max(
                all_chunks[chunk.chunk_id].semantic_score,
                chunk.semantic_score
            )
            all_chunks[chunk.chunk_id].bm25_score = max(
                all_chunks[chunk.chunk_id].bm25_score,
                chunk.bm25_score
            )

    # Compute RRF score for each chunk
    rrf_scores: dict[str, float] = {cid: 0.0 for cid in all_chunks}

    for rank, chunk in enumerate(semantic_results):
        rrf_scores[chunk.chunk_id] += 1.0 / (RRF_K + rank + 1)

    for rank, chunk in enumerate(bm25_results):
        rrf_scores[chunk.chunk_id] += 1.0 / (RRF_K + rank + 1)

    # Assign RRF scores back to chunks
    for chunk_id, score in rrf_scores.items():
        all_chunks[chunk_id].rrf_score = score

    # Sort by RRF score descending, return top_k
    ranked = sorted(all_chunks.values(), key=lambda c: c.rrf_score, reverse=True)

    logger.debug(
        f"RRF merge: {len(semantic_results)} semantic + "
        f"{len(bm25_results)} BM25 → {len(ranked)} unique → top {top_k}"
    )

    return ranked[:top_k]


def retrieve(
    conn,
    question:        str,
    top_k:           int = 5,
    domain_filter:   Optional[str] = None,
    doc_type_filter: Optional[str] = None,
    hyde_document:   Optional[str] = None,
) -> list[RetrievedChunk]:
    """
    Main retrieval function. Runs hybrid BM25 + semantic search and
    merges results with RRF. This is what the RAG pipeline calls.

    Args:
        conn:            psycopg2 connection (with register_vector called)
        question:        User's question in French
        top_k:           Number of chunks to return after merging
        domain_filter:   Optional — filter by legal domain
                         e.g. 'droit_civil', 'droit_penal'
        doc_type_filter: Optional — filter by document type
                         e.g. 'loi', 'decret', 'jurisprudence'
        hyde_document:   Optional — A hypothetical document generated by an LLM
                         to improve semantic search matching.

    Returns:
        List of RetrievedChunk sorted by RRF score descending.
        Empty list if no results found in either retrieval method.
    """
    if not question or not question.strip():
        logger.warning("Empty question passed to retrieve()")
        return []

    # Fetch more candidates than top_k so RRF has enough to merge
    candidates = top_k * CANDIDATE_MULTIPLIER

    # Embed the hypothetical document if provided, otherwise embed the question
    text_to_embed = hyde_document if hyde_document else question
    query_embedding = embed_query(text_to_embed)

    # Run both retrievals
    semantic_results = semantic_search(
        conn, query_embedding, candidates, domain_filter, doc_type_filter
    )
    bm25_results = bm25_search(
        conn, question, candidates, domain_filter, doc_type_filter
    )

    logger.info(
        f"Retrieved: {len(semantic_results)} semantic, "
        f"{len(bm25_results)} BM25 for query: {question[:60]!r}"
    )

    # Handle edge cases
    if not semantic_results and not bm25_results:
        logger.warning(f"No results found for: {question[:60]!r}")
        return []

    if not bm25_results:
        # BM25 returned nothing (query has no French stems in index)
        # Fall back to semantic-only, still assign RRF scores
        logger.info("BM25 returned no results — using semantic search only")
        for rank, chunk in enumerate(semantic_results):
            chunk.rrf_score = 1.0 / (RRF_K + rank + 1)
        return semantic_results[:top_k]

    if not semantic_results:
        logger.info("Semantic search returned no results — using BM25 only")
        for rank, chunk in enumerate(bm25_results):
            chunk.rrf_score = 1.0 / (RRF_K + rank + 1)
        return bm25_results[:top_k]

    # Full hybrid merge
    return reciprocal_rank_fusion(semantic_results, bm25_results, top_k)