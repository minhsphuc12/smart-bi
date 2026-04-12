"""Ask Data: compose grounded narratives and run safe read-only previews."""

from __future__ import annotations

import time
from typing import Any

from sqlalchemy.exc import SQLAlchemyError

from app.routers.admin_connections import get_connection_record
from app.services import db_engine


def _format_cell(value: Any) -> str:
    if value is None:
        return "NULL"
    s = str(value)
    return s if len(s) <= 120 else s[:117] + "…"


def compose_live_narrative(
    question: str,
    table_name: str,
    query_kind: str,
    columns: list[str],
    rows: list[list[Any]],
    selected_columns: list[str] | None,
) -> str:
    q = question.strip() or "your question"
    col_note = f"Columns shown: {', '.join(columns[:8])}" + (" …" if len(columns) > 8 else "")

    if query_kind == "count":
        n = int(rows[0][0]) if rows and rows[0] else 0
        return (
            f"Read-only COUNT on `{table_name}` for “{q}”: **{n}** row(s). "
            f"{col_note}. Heuristic routing (not full NL2SQL) detected counting language in your question."
        )

    if query_kind == "sum":
        total = rows[0][0] if rows and rows[0] else None
        src = (
            selected_columns[0]
            if selected_columns and len(selected_columns) > 0
            else (columns[0] if columns else "measure")
        )
        return (
            f"Read-only SUM(`{src}`) on `{table_name}` for “{q}”: **{_format_cell(total)}**. "
            f"{col_note}. Totals follow your wording where a numeric column could be inferred."
        )

    n = len(rows)
    subset = ""
    if selected_columns:
        subset = f"Keyword overlap narrowed the preview to {len(selected_columns)} column(s). "
    first_bits = ""
    if rows and columns:
        first_bits = f" First row starts with: {_format_cell(rows[0][0])}"
        if len(columns) > 1:
            first_bits += f", {_format_cell(rows[0][1])}"
        if len(columns) > 2:
            first_bits += ", …"
    return (
        f"Live preview from `{table_name}` for “{q}”: **{n}** row(s) (capped). "
        f"{subset}{col_note}.{first_bits}"
    )


def run_connected_question(
    connection_id: int, question: str, row_limit: int = 50
) -> tuple[str, list[str], list[list[Any]], dict[str, Any]]:
    """Load connection, introspect if needed, pick table, run read-only preview."""
    t0 = time.perf_counter()
    conn = get_connection_record(connection_id)

    tables = db_engine.get_introspection_cache(connection_id)
    if not tables:
        engine = db_engine.make_engine(conn)
        try:
            tables = db_engine.introspect_schema(engine, conn["source_type"])
        finally:
            engine.dispose()
        db_engine.set_introspection_cache(connection_id, tables)

    if not tables:
        raise ValueError("No user tables visible for this connection. Check grants or schema.")

    table = db_engine.pick_table_for_question(question, tables)
    if table is None:
        raise ValueError("Could not choose a table to preview.")

    engine = db_engine.make_engine(conn)
    used_fallback = False
    try:
        sql, columns, rows, qmeta = db_engine.preview_for_question(
            engine, conn["source_type"], table, question, row_limit=row_limit
        )
    except (ValueError, SQLAlchemyError):
        used_fallback = True
        sql, columns, rows = db_engine.preview_select(
            engine, conn["source_type"], table, row_limit=row_limit
        )
        qmeta = {
            "query_kind": "scan",
            "table": table["name"],
            "selected_columns": None,
            "used_fallback": True,
        }
    finally:
        engine.dispose()

    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    evidence = {
        **qmeta,
        "table": table["name"],
        "used_fallback": used_fallback or qmeta.get("used_fallback", False),
        "execution_ms": elapsed_ms,
        "row_count": len(rows),
    }
    return sql, columns, rows, evidence
