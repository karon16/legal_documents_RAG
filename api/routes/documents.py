from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Optional
from api.db import get_db
from api.models.responses import DocumentSummary, DocumentDetail

router = APIRouter()

@router.get("/documents", response_model=list[DocumentSummary])
def list_documents(
    domain:   Optional[list[str]] = Query(None),
    doc_type: Optional[list[str]] = Query(None),
    limit:    int           = Query(20, ge=1, le=100),
    offset:   int           = Query(0,  ge=0),
    conn      = Depends(get_db)
):
    conditions = ["1=1"]
    params     = []

    if domain:
        conditions.append("ld.domain = ANY(%s)")
        params.append(domain)

    if doc_type:
        conditions.append("ld.doc_type = ANY(%s)")
        params.append(doc_type)

    params += [limit, offset]
    where = " AND ".join(conditions)

    with conn.cursor() as cur:
        cur.execute(f"""
            SELECT
                ld.id::text,
                ld.title,
                ld.domain,
                ld.doc_type,
                ld.date_enacted::text,
                ld.source_url,
                ld.word_count,
                ld.scraped_at::text,
                COUNT(dc.id) AS chunk_count
            FROM legal_documents ld
            LEFT JOIN document_chunks dc ON dc.document_id = ld.id
            WHERE {where}
            GROUP BY ld.id
            ORDER BY ld.scraped_at DESC
            LIMIT %s OFFSET %s
        """, params)
        rows = cur.fetchall()

    return [
        DocumentSummary(
            id           = str(row['id']),
            title        = row['title'] or '',
            domain       = row['domain'],
            doc_type     = row['doc_type'],
            date_enacted = row['date_enacted'],
            source_url   = row['source_url'],
            word_count   = row['word_count'],
            chunk_count  = row['chunk_count'],
            scraped_at   = str(row['scraped_at']),
        )
        for row in rows
    ]

@router.get("/documents/{document_id}", response_model=DocumentDetail)
def get_document(document_id: str, conn=Depends(get_db)):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT
                ld.id::text,
                ld.title,
                ld.domain,
                ld.doc_type,
                ld.date_enacted::text,
                ld.source_url,
                ld.word_count,
                ld.scraped_at::text,
                ld.raw_text,
                COUNT(dc.id) AS chunk_count
            FROM legal_documents ld
            LEFT JOIN document_chunks dc ON dc.document_id = ld.id
            WHERE ld.id = %s::uuid
            GROUP BY ld.id
        """, (document_id,))
        row = cur.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Document not found")

    return DocumentDetail(
        id               = str(row['id']),
        title            = row['title'] or '',
        domain           = row['domain'],
        doc_type         = row['doc_type'],
        date_enacted     = row['date_enacted'],
        source_url       = row['source_url'],
        word_count       = row['word_count'],
        chunk_count      = row['chunk_count'],
        scraped_at       = str(row['scraped_at']),
        raw_text_preview = (row['raw_text'] or '')[:500],
    )
