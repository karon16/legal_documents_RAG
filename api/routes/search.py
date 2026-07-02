from fastapi import APIRouter, Depends, Query
from typing import Optional
from api.db import get_db
from api.models.responses import SearchResponse, SearchResult
from pipeline.retriever import retrieve
from pipeline.embedder import embed_query

router = APIRouter()

@router.get("/search", response_model=SearchResponse)
def search(
    q:        str = Query(..., min_length=2, max_length=500),
    domain:   Optional[list[str]] = Query(None),
    doc_type: Optional[list[str]] = Query(None),
    top_k:    int = Query(5, ge=1, le=20),
    conn      = Depends(get_db)
):
    chunks = retrieve(
        conn             = conn,
        question         = q,
        top_k            = top_k,
        domain_filters   = domain,
        doc_type_filters = doc_type,
    )

    results = [
        SearchResult(
            chunk_id        = c.chunk_id,
            text            = c.text,
            article_number  = c.article_number,
            chapter_heading = c.chapter_heading,
            document_title  = c.document_title,
            domain          = c.domain,
            doc_type        = c.doc_type,
            date_enacted    = c.date_enacted,
            source_url      = c.source_url,
            semantic_score  = c.semantic_score,
            bm25_score      = c.bm25_score,
            rrf_score       = c.rrf_score,
        )
        for c in chunks
    ]

    return SearchResponse(
        query        = q,
        results      = results,
        result_count = len(results),
    )
