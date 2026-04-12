from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.exc import SQLAlchemyError

from app.services import ask_data, nl2sql_pipeline
from app.services.ai_router import run_task

router = APIRouter(prefix="/chat", tags=["chat"])


class QuestionPayload(BaseModel):
    question: str
    connection_id: int | None = Field(
        default=None,
        description="When set, runs NL2SQL (LLM + semantic + schema) with read-only policy, or heuristic preview if LLM keys are missing.",
    )


@router.post("/questions")
def ask_question(payload: QuestionPayload) -> dict:
    if payload.connection_id is not None:
        try:
            return nl2sql_pipeline.answer_question(payload.connection_id, payload.question)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except SQLAlchemyError as exc:
            raise HTTPException(status_code=400, detail=f"Query failed: {exc}") from exc

    sql_result = run_task("sql_gen", payload.question)
    answer_result = run_task("answer_gen", payload.question)

    sql = (
        "SELECT order_date, SUM(amount) AS revenue FROM sales_orders "
        "GROUP BY order_date FETCH FIRST 100 ROWS ONLY"
    )
    columns = ["order_date", "revenue"]
    rows = [
        ["2026-04-01", 125000],
        ["2026-04-02", 132500],
    ]
    evidence: dict = {
        "query_kind": "demo",
        "table": "sales_orders (demo)",
        "selected_columns": None,
        "used_fallback": False,
        "execution_ms": 0,
        "row_count": len(rows),
    }

    answer, confidence, warnings = ask_data.narrative_and_meta(
        question=payload.question,
        connection_id=None,
        columns=columns,
        rows=rows,
        evidence=evidence,
    )

    return {
        "answer": answer,
        "sql": sql,
        "columns": columns,
        "rows": rows,
        "confidence": confidence,
        "warnings": warnings,
        "evidence": evidence,
        "meta": {
            "sql_model": sql_result["model"],
            "answer_model": answer_result["model"],
            "sql_task_note": sql_result.get("output") or "",
            "answer_task_note": answer_result.get("output") or "",
            "sql_live": bool(sql_result.get("live")),
            "answer_live": bool(answer_result.get("live")),
        },
    }
