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


def compose_demo_narrative(question: str, columns: list[str], rows: list[list[Any]]) -> str:
    q = question.strip() or "your question"
    if not rows:
        return (
            f"For “{q}”, the demo dataset returns no rows. "
            "Connect a datasource to preview live tables (read-only, row-capped)."
        )
    preview_cols = ", ".join(columns[:6])
    if len(columns) > 6:
        preview_cols += ", …"
    first = rows[0]
    parts = [_format_cell(v) for v in first[:4]]
    if len(first) > 4:
        parts.append("…")
    return (
        f"Demo answer for “{q}”: the sample grid has {len(rows)} row(s) and columns {preview_cols}. "
        f"Example values from the first row: {', '.join(parts)}. "
        "This uses bundled placeholder SQL until you attach a connection for a live preview."
    )


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


def confidence_for(query_kind: str, connection_id: int | None, had_column_hints: bool) -> float:
    if connection_id is None:
        return 0.88
    if query_kind == "count":
        return 0.78
    if query_kind == "sum":
        return 0.76
    if had_column_hints:
        return 0.68
    return 0.58


def warnings_for(
    connection_id: int | None,
    query_kind: str,
    table_name: str,
    used_fallback: bool,
) -> list[str]:
    out: list[str] = []
    if connection_id is None:
        out.append("Demo mode: SQL and rows are illustrative; connect a datasource for live evidence.")
        return out
    if used_fallback:
        out.append("Heuristic query failed partway; fell back to a plain SELECT with LIMIT.")
    out.append(
        f"Heuristic Ask Data on `{table_name}` ({query_kind}). "
        "Full NL2SQL + policy engine is not enabled yet; review SQL before sharing."
    )
    return out


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


def narrative_and_meta(
    *,
    question: str,
    connection_id: int | None,
    columns: list[str],
    rows: list[list[Any]],
    evidence: dict[str, Any],
) -> tuple[str, float, list[str]]:
    qk = str(evidence.get("query_kind") or "scan")
    table = str(evidence.get("table") or "unknown")
    sel = evidence.get("selected_columns")
    selected_columns = list(sel) if isinstance(sel, list) else None
    used_fallback = bool(evidence.get("used_fallback"))
    had_hints = bool(selected_columns) and qk == "scan"

    if connection_id is None:
        answer = compose_demo_narrative(question, columns, rows)
    else:
        answer = compose_live_narrative(
            question, table, qk, columns, rows, selected_columns
        )

    conf = confidence_for(qk, connection_id, had_hints)
    warns = warnings_for(connection_id, qk, table, used_fallback)

    return answer, conf, warns
