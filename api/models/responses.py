from pydantic import BaseModel
from typing import Optional

class SourceDoc(BaseModel):
    article_number:  Optional[str]
    document_title:  str
    domain:          str
    doc_type:        str
    date_enacted:    Optional[str]
    source_url:      str
    rrf_score:       Optional[float]
    excerpt:         str

class AskResponse(BaseModel):
    question:        str
    answer:          str
    sources:         list[SourceDoc]
    retrieved_count: int
    had_citations:   bool
    was_grounded:    bool
    retrieval_ms:    int
    generation_ms:   int
    qa_log_id:       Optional[str]

class SearchResult(BaseModel):
    chunk_id:        str
    text:            str
    article_number:  Optional[str]
    chapter_heading: Optional[str]
    document_title:  str
    domain:          str
    doc_type:        str
    date_enacted:    Optional[str]
    source_url:      str
    semantic_score:  float
    bm25_score:      float
    rrf_score:       float

class SearchResponse(BaseModel):
    query:           str
    results:         list[SearchResult]
    result_count:    int

class DocumentSummary(BaseModel):
    id:              str
    title:           str
    domain:          str
    doc_type:        str
    date_enacted:    Optional[str]
    source_url:      str
    word_count:      Optional[int]
    chunk_count:     Optional[int]
    scraped_at:      str

class DocumentDetail(DocumentSummary):
    raw_text_preview: str

class StatsResponse(BaseModel):
    total_documents:     int
    total_chunks:        int
    embedded_chunks:     int
    total_interactions:  int
    by_domain:           list[dict]
    by_quality:          list[dict]

class FeedbackResponse(BaseModel):
    success:   bool
    message:   str
