from fastapi import APIRouter, Depends
from api.db import get_db
from api.models.responses import StatsResponse

router = APIRouter()

@router.get("/stats", response_model=StatsResponse)
def get_stats(conn=Depends(get_db)):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT
              (SELECT COUNT(*) FROM legal_documents)    AS total_documents,
              (SELECT COUNT(*) FROM document_chunks)    AS total_chunks,
              (SELECT COUNT(*) FROM document_chunks
               WHERE embedding IS NOT NULL)             AS embedded_chunks,
              (SELECT COUNT(*) FROM qa_logs)            AS total_interactions
        """)
        totals = dict(cur.fetchone())

        cur.execute("""
            SELECT domain, COUNT(*) AS count
            FROM legal_documents
            GROUP BY domain
            ORDER BY count DESC
        """)
        by_domain = [dict(r) for r in cur.fetchall()]

        cur.execute("""
            SELECT quality, COUNT(*) AS count
            FROM legal_documents
            GROUP BY quality
        """)
        by_quality = [dict(r) for r in cur.fetchall()]

    return StatsResponse(
        total_documents    = totals['total_documents'],
        total_chunks       = totals['total_chunks'],
        embedded_chunks    = totals['embedded_chunks'],
        total_interactions = totals['total_interactions'],
        by_domain          = by_domain,
        by_quality         = by_quality,
    )
