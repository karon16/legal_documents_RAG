from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from api.db import get_db
from api.models.requests import AskRequest
from api.models.responses import AskResponse, SourceDoc
from pipeline.rag import ask as rag_ask, ask_stream as rag_ask_stream

router = APIRouter()

@router.post("/ask", response_model=AskResponse)
def ask_question(request: AskRequest, conn=Depends(get_db)):
    try:
        result = rag_ask(
            question        = request.question,
            domain_filters   = request.domain_filters,
            doc_type_filters = request.doc_type_filters,
            top_k           = request.top_k,
            log_to_db       = True,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"RAG pipeline error: {str(e)}"
        )

    sources = [SourceDoc(**s) for s in result.sources]

    return AskResponse(
        question        = result.question,
        answer          = result.answer,
        sources         = sources,
        retrieved_count = result.retrieved_count,
        had_citations   = result.had_citations,
        was_grounded    = result.was_grounded,
        retrieval_ms    = result.retrieval_ms,
        generation_ms   = result.generation_ms,
        qa_log_id       = result.qa_log_id,
    )

@router.post("/ask/stream")
def ask_question_stream(request: AskRequest, conn=Depends(get_db)):
    # Note: ask_stream doesn't take conn directly, it manages its own connection because of the async nature of streaming
    # But wait, rag.py's ask_stream opens its own connection via psycopg2.connect(DB_CONN)!
    generator = rag_ask_stream(
        question        = request.question,
        domain_filters  = request.domain_filters,
        doc_type_filters= request.doc_type_filters,
        top_k           = request.top_k,
        log_to_db       = True,
    )
    return StreamingResponse(generator, media_type="application/x-ndjson")
