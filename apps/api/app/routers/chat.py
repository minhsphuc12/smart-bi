from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.exc import SQLAlchemyError

from app.routers.admin_connections import get_connection_record
from app.services import db_engine
from app.services.ai_router import run_task

router = APIRouter(prefix="/chat", tags=["chat"])


class QuestionPayload(BaseModel):
    question: str
    connection_id: int | None = Field(
        default=None,
        description="When set, runs a read-only preview query against this connection using cached schema.",
    )


@router.post("/questions")
def ask_question(payload: QuestionPayload) -> dict:
    sql_result = run_task("sql_gen", payload.question)
    answer_result = run_task("answer_gen", payload.question)

    if payload.connection_id is None:
        sql = "SELECT order_date, SUM(amount) AS revenue FROM sales_orders GROUP BY order_date FETCH FIRST 100 ROWS ONLY"
        columns = ["order_date", "revenue"]
        rows = [
            ["2026-04-01", 125000],
            ["2026-04-02", 132500],
        ]
        warnings: list[str] = []
    else:
        conn = get_connection_record(payload.connection_id)

        tables = db_engine.get_introspection_cache(payload.connection_id)
        if not tables:
            try:
                engine = db_engine.make_engine(conn)
                try:
                    tables = db_engine.introspect_schema(engine, conn["source_type"])
                finally:
                    engine.dispose()
                db_engine.set_introspection_cache(payload.connection_id, tables)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            except SQLAlchemyError as exc:
                raise HTTPException(
                    status_code=400, detail=f"Could not introspect database: {exc}"
                ) from exc

        if not tables:
            raise HTTPException(
                status_code=400,
                detail="No user tables visible for this connection. Check grants or schema.",
            )

        table = db_engine.pick_table_for_question(payload.question, tables)
        if table is None:
            raise HTTPException(status_code=400, detail="Could not choose a table to preview.")

        try:
            engine = db_engine.make_engine(conn)
            try:
                sql, columns, rows = db_engine.preview_select(
                    engine, conn["source_type"], table, row_limit=50
                )
            finally:
                engine.dispose()
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except SQLAlchemyError as exc:
            raise HTTPException(status_code=400, detail=f"Query failed: {exc}") from exc

        warnings = [
            f"Live read-only preview (max 50 rows) from {table['name']}. "
            "NL2SQL is not enabled yet; the chosen table matches your question heuristically or defaults to the first table."
        ]

    return {
        "answer": answer_result["output"],
        "sql": sql,
        "columns": columns,
        "rows": rows,
        "confidence": 0.82 if payload.connection_id is None else 0.55,
        "warnings": warnings,
        "meta": {
            "sql_model": sql_result["model"],
            "answer_model": answer_result["model"],
        },
    }
