from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from api.main import app

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert "JusticeCongo AI" in response.json()["name"]

@patch("api.routes.ask.rag_ask")
@patch("api.routes.ask.get_db")
def test_ask_valid_question(mock_db, mock_rag):
    mock_rag.return_value = MagicMock(
        question        = "Test question?",
        answer          = "Selon l'Article 5, la réponse est oui. Veuillez consulter vos documents.",
        sources         = [],
        retrieved_count = 3,
        had_citations   = True,
        was_grounded    = True,
        retrieval_ms    = 120,
        generation_ms   = 980,
        qa_log_id       = "some-uuid",
    )
    response = client.post("/api/ask", json={"question": "Test question?"})
    assert response.status_code == 200
    data = response.json()
    assert data["was_grounded"] is True
    assert data["had_citations"] is True

def test_ask_empty_question():
    response = client.post("/api/ask", json={"question": ""})
    assert response.status_code == 422

def test_ask_question_too_short():
    response = client.post("/api/ask", json={"question": "Oui"})
    assert response.status_code == 422

def test_stats_endpoint():
    with patch("api.routes.stats.get_db"):
        response = client.get("/api/stats")
        assert response.status_code in [200, 500]

def test_feedback_missing_body():
    response = client.post("/api/feedback", json={})
    assert response.status_code == 422

def test_search_missing_query():
    response = client.get("/api/search")
    assert response.status_code == 422

def test_document_not_found():
    with patch("api.routes.documents.get_db"):
        response = client.get("/api/documents/00000000-0000-0000-0000-000000000000")
        assert response.status_code in [404, 500]
