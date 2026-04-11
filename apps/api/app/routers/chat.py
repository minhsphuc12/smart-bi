from fastapi import APIRouter
from pydantic import BaseModel

from app.services.ai_router import run_task

router = APIRouter(prefix="/chat", tags=["chat"])


class QuestionPayload(BaseModel):
    question: str


@router.post("/questions")
def ask_question(payload: QuestionPayload) -> dict:
    sql_result = run_task("sql_gen", payload.question)
    answer_result = run_task("answer_gen", payload.question)
    sql = "SELECT order_date, SUM(amount) AS revenue FROM sales_orders GROUP BY order_date FETCH FIRST 100 ROWS ONLY"
    columns = ["order_date", "revenue"]
    rows = [
        ["2026-04-01", 125000],
        ["2026-04-02", 132500],
    ]
    return {
        "answer": answer_result["output"],
        "sql": sql,
        "columns": columns,
        "rows": rows,
        "confidence": 0.82,
        "warnings": [],
        "meta": {
            "sql_model": sql_result["model"],
            "answer_model": answer_result["model"],
        },
    }
