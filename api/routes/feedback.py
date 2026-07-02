from fastapi import APIRouter, Depends, HTTPException
from api.db import get_db
from api.models.requests import FeedbackRequest
from api.models.responses import FeedbackResponse

router = APIRouter()

@router.post("/feedback", response_model=FeedbackResponse)
def submit_feedback(request: FeedbackRequest, conn = Depends(get_db)):
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id FROM qa_logs WHERE id = %s::uuid",
            (request.qa_log_id,)
        )
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="QA log entry not found")

    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO user_feedback
                (qa_log_id, rating, comment, flagged_reason)
            VALUES (%s::uuid, %s, %s, %s)
        """, (
            request.qa_log_id,
            request.rating,
            request.comment,
            request.flagged_reason,
        ))
    conn.commit()

    return FeedbackResponse(
        success = True,
        message = "Merci pour votre retour."
    )
