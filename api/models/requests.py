from pydantic import BaseModel, Field, field_validator
from typing import Optional
from enum import Enum

class LegalDomain(str, Enum):
    droit_civil       = "droit_civil"
    droit_penal       = "droit_penal"
    droit_commercial  = "droit_commercial"
    droit_fiscal      = "droit_fiscal"
    droit_du_travail  = "droit_du_travail"
    droit_public      = "droit_public"
    droit_social      = "droit_social"
    jurisprudence     = "jurisprudence"
    doctrine          = "doctrine"
    journal_officiel  = "journal_officiel"
    modeles           = "modeles"

class DocType(str, Enum):
    loi           = "loi"
    decret        = "decret"
    arrete        = "arrete"
    ordonnance    = "ordonnance"
    jurisprudence = "jurisprudence"
    doctrine      = "doctrine"
    modele        = "modele"
    document      = "document"

class AskRequest(BaseModel):
    question:        str = Field(..., min_length=5, max_length=1000, description="Legal question in French")
    domain_filters:   Optional[list[LegalDomain]] = Field(None, description="Filter results by legal domains")
    doc_type_filters: Optional[list[DocType]] = Field(None, description="Filter results by document types")
    top_k:           int = Field(5, ge=1, le=10, description="Number of chunks to retrieve")
    session_id:      Optional[str] = Field(None, max_length=100, description="Anonymous session identifier")

    @field_validator('question')
    @classmethod
    def question_not_empty(cls, v):
        if not v.strip():
            raise ValueError('Question cannot be empty or whitespace')
        return v.strip()

class SearchRequest(BaseModel):
    query:           str = Field(..., min_length=2, max_length=500)
    domain_filters:   Optional[list[LegalDomain]] = None
    doc_type_filters: Optional[list[DocType]]     = None
    top_k:           int = Field(5, ge=1, le=20)

class FeedbackRequest(BaseModel):
    qa_log_id:      str = Field(..., description="UUID of the QA log entry")
    rating:         int = Field(..., ge=-1, le=1, description="-1 = unhelpful, 1 = helpful")
    comment:        Optional[str] = Field(None, max_length=1000)
    flagged_reason: Optional[str] = Field(None, description="incorrect_law | wrong_article | not_found | unclear | outdated")
