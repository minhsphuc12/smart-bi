"""Execute read-only SQL for dashboard widgets (same policy as NL2SQL)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.routers.admin_connections import get_connection_record
from app.services import db_engine, sql_policy
from app.services.db_engine import _serialize_cell


def _allowed_table_names(connection_id: int) -> set[str]:
    tables = db_engine.get_introspection_cache(connection_id)
    if not tables:
        eng = db_engine.make_engine(get_connection_record(connection_id))
        try:
            conn = get_connection_record(connection_id)
            tables = db_engine.introspect_schema(eng, conn["source_type"])
        finally:
            eng.dispose()
        db_engine.set_introspection_cache(connection_id, tables)
    return {str(t["name"]) for t in tables if t.get("name")}


def run_widget_sql(
    connection_id: int,
    raw_sql: str,
    *,
    max_rows: int = 200,
) -> dict[str, Any]:
    """
    Validate and execute one widget query.
    Returns { "sql_executed", "columns", "rows" } or { "error", "sql_executed": null }.
    """
    conn = get_connection_record(connection_id)
    allowed = _allowed_table_names(connection_id)
    if not allowed:
        return {
            "error": "No tables in introspection cache for this connection.",
            "sql_executed": None,
            "columns": [],
            "rows": [],
        }

    try:
        prepared = sql_policy.prepare_readonly_select(
            raw_sql,
            source_type=conn["source_type"],
            allowed_table_names=allowed,
            max_rows=max_rows,
        )
    except ValueError as exc:
        return {"error": str(exc), "sql_executed": None, "columns": [], "rows": []}

    engine = db_engine.make_engine(conn)
    try:
        with engine.connect() as c:
            result = c.execute(text(prepared))
            columns = list(result.keys())
            raw_rows = result.fetchmany(max_rows + 1)
        rows = [[_serialize_cell(x) for x in row] for row in raw_rows[:max_rows]]
        return {"sql_executed": prepared, "columns": columns, "rows": rows, "error": None}
    except SQLAlchemyError as exc:
        return {
            "error": f"Query failed: {exc}",
            "sql_executed": prepared,
            "columns": [],
            "rows": [],
        }


def run_all_widget_queries(
    connection_id: int,
    widgets: list[dict[str, Any]],
    *,
    max_rows: int = 200,
) -> list[dict[str, Any]]:
    """Run SQL for each widget that defines a non-empty ``sql`` string."""
    out: list[dict[str, Any]] = []
    for i, w in enumerate(widgets):
        if not isinstance(w, dict):
            out.append({"widget_index": i, "error": "Invalid widget", "sql_executed": None, "columns": [], "rows": []})
            continue
        sql_raw = w.get("sql")
        if not isinstance(sql_raw, str) or not sql_raw.strip():
            out.append(
                {
                    "widget_index": i,
                    "error": "Widget has no sql field; regenerate the dashboard with a datasource selected.",
                    "sql_executed": None,
                    "columns": [],
                    "rows": [],
                }
            )
            continue
        r = run_widget_sql(connection_id, sql_raw, max_rows=max_rows)
        entry = {"widget_index": i, **r}
        out.append(entry)
    return out
