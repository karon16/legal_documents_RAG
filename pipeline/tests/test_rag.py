import pytest
from unittest.mock import patch, MagicMock

from pipeline.retriever import RetrievedChunk
from pipeline.rag import (
    build_context,
    build_messages,
    validate_answer,
    ask,
)

@pytest.fixture
def SAMPLE_CHUNKS():
    return [
        RetrievedChunk(
            chunk_id="uuid-1",
            text="Article 5: La société commerciale visée...",
            article_number="5",
            chapter_heading=None,
            document_title="Décret du 24 avril 2009",
            domain="droit_public",
            doc_type="decret",
            date_enacted="2009-04-24",
            source_url="https://leganet.cd/...",
            semantic_score=0.87,
            bm25_score=0.0,
            rrf_score=0.0164
        ),
        RetrievedChunk(
            chunk_id="uuid-2",
            text="Article 12: Le locataire est tenu...",
            article_number="12",
            chapter_heading=None,
            document_title="Loi du 30 juillet 1888",
            domain="droit_civil",
            doc_type="loi",
            date_enacted="1888-07-30",
            source_url="https://leganet.cd/...",
            semantic_score=0.82,
            bm25_score=0.31,
            rrf_score=0.0158
        )
    ]

def test_build_context_with_chunks(SAMPLE_CHUNKS):
    context = build_context(SAMPLE_CHUNKS)
    assert "Source 1" in context
    assert "Article 5" in context
    assert "Décret du 24 avril 2009" in context
    assert "Source 2" in context
    assert "---" in context

def test_build_context_empty():
    context = build_context([])
    assert "Aucun extrait" in context

def test_build_messages_structure(SAMPLE_CHUNKS):
    messages = build_messages("Test question?", SAMPLE_CHUNKS)
    assert len(messages) == 1
    assert messages[0]["role"] == "user"
    assert "Test question?" in messages[0]["content"]
    assert "Source 1" in messages[0]["content"]
    assert "LEGANET.CD" in messages[0]["content"]

def test_validate_answer_valid():
    answer = (
        "Selon l'Article 5 du Décret du 24 avril 2009, "
        "la société commerciale doit être enregistrée."
    )
    result = validate_answer(answer)
    assert result["has_citation"] is True
    assert result["is_valid"] is True



def test_validate_answer_admits_ignorance():
    answer = (
        "Cette information ne figure pas dans les textes "
        "disponibles sur LEGANET.CD."
    )
    result = validate_answer(answer)
    assert result["admits_ignorance"] is True
    assert result["is_valid"] is True

def test_validate_answer_too_short():
    answer = "Je ne sais pas."
    result = validate_answer(answer)
    assert result["not_too_short"] is False

@patch("pipeline.rag.retrieve")
@patch("pipeline.rag.ollama.chat")
@patch("pipeline.rag.psycopg2.connect")
@patch("pipeline.rag.register_vector")
def test_ask_returns_rag_response(
    mock_register, mock_connect, mock_chat, mock_retrieve, SAMPLE_CHUNKS
):
    # Setup mocks
    mock_retrieve.return_value = SAMPLE_CHUNKS
    mock_chat.return_value = {
        'message': {
            'content': (
                "Selon l'Article 5 du Décret du 24 avril 2009, "
                "la société doit être enregistrée."
            )
        }
    }

    result = ask(
        "Comment créer une société?",
        log_to_db=False
    )

    assert result.was_grounded is True
    assert result.retrieved_count == 2
    assert result.had_citations is True
    assert len(result.sources) == 2

@patch("pipeline.rag.retrieve")
@patch("pipeline.rag.psycopg2.connect")
@patch("pipeline.rag.register_vector")
def test_ask_empty_retrieval(mock_register, mock_connect, mock_retrieve):
    mock_retrieve.return_value = []

    result = ask("Question sans résultat?", log_to_db=False)

    assert result.was_grounded is False
    assert result.retrieved_count == 0
    assert "LEGANET.CD" in result.answer

def test_ask_empty_question():
    result = ask("", log_to_db=False)
    assert result.answer == "Veuillez poser une question."
    assert result.was_grounded is False
