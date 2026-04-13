from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.exc import SQLAlchemyError

from app.services import nl2sql_pipeline

router = APIRouter(prefix="/chat", tags=["chat"])


class QuestionPayload(BaseModel):
    question: str
    connection_id: int = Field(
        ...,
        description="Admin connection id; NL2SQL (LLM + semantic + schema) with read-only sqlglot policy. Requires provider API keys.",
    )


@router.post("/questions")
def ask_question(payload: QuestionPayload) -> dict:
    try:
        return nl2sql_pipeline.answer_question(payload.connection_id, payload.question)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=400, detail=f"Query failed: {exc}") from exc
