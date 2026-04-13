"""NL2SQL over introspected schema + semantic layer, with LLM narrative."""

from __future__ import annotations

import json
import time
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from app.routers.admin_ai_routing import get_profile_for_task
from app.routers.admin_connections import get_connection_record
from app.services import db_engine, semantic_store, sql_policy
from app.services.ai_router import run_task
from app.services.db_engine import _serialize_cell


def _format_semantic(sem: dict[str, Any]) -> str:
    lines: list[str] = ["## Semantic layer (curated metadata)"]
    for t in sem.get("tables") or []:
        if isinstance(t, dict) and t.get("name"):
            desc = (t.get("description") or "").strip()
            lines.append(f"- **Table `{t['name']}`**: {desc or '(no description)'}")
    for r in sem.get("relationships") or []:
        if isinstance(r, dict) and r.get("name"):
            lines.append(f"- **Relationship `{r['name']}`**: {(r.get('description') or '').strip()}")
    for d in sem.get("dictionary") or []:
        if isinstance(d, dict) and d.get("name"):
            lines.append(f"- **Term `{d['name']}`**: {(d.get('description') or '').strip()}")
    for m in sem.get("metrics") or []:
        if isinstance(m, dict) and m.get("name"):
            lines.append(f"- **Metric `{m['name']}`**: {(m.get('description') or '').strip()}")
    if len(lines) == 1:
        lines.append("- _(empty — add entries in Admin → Semantic layer)_")
    return "\n".join(lines)


def _format_physical_schema(tables: list[dict[str, Any]], max_chars: int = 26000) -> str:
    parts: list[str] = ["## PHYSICAL SCHEMA (authoritative column lists)"]
    for t in tables[:200]:
        name = t.get("name")
        cols = t.get("columns") or []
        if not name:
            continue
        col_str = ", ".join(str(c) for c in cols[:120])
        if len(cols) > 120:
            col_str += ", …"
        parts.append(f"- `{name}` → {col_str}")
    body = "\n".join(parts)
    if len(body) > max_chars:
        body = body[:max_chars] + "\n\n…(schema truncated for prompt size)…"
    return body


def _dialect_row_cap_hint(source_type: str, max_rows: int) -> str:
    if source_type == "oracle":
        return f"Use `FETCH FIRST {max_rows} ROWS ONLY` (not LIMIT)."
    if source_type == "mysql":
        return f"End the query with `LIMIT {max_rows}`."
    return f"End the query with `LIMIT {max_rows}`."


def _sql_system_prompt(source_type: str, max_rows: int) -> str:
    cap = _dialect_row_cap_hint(source_type, max_rows)
    return (
        "You are a senior analytics engineer. Generate exactly one read-only SQL query.\n"
        "Hard rules:\n"
        "- Output ONLY the SQL text: a single `SELECT` or `WITH ... SELECT`. No markdown fences, no commentary.\n"
        "- Use ONLY tables that appear in the PHYSICAL SCHEMA list. Qualify with schema when the physical name includes one.\n"
        "- Respect the semantic layer hints for joins, grain, and business-friendly column choices.\n"
        f"- Row cap: {cap}\n"
        "- No DDL/DML, no multiple statements, no vendor-specific admin commands.\n"
        f"- Database dialect: **{source_type}** (generate valid SQL for this engine).\n"
    )


def _execute_readonly(engine: Engine, sql: str) -> tuple[list[str], list[list[Any]]]:
    with engine.connect() as conn:
        result = conn.execute(text(sql))
        columns = list(result.keys())
        raw_rows = result.fetchmany(500)
    rows = [[_serialize_cell(c) for c in row] for row in raw_rows]
    return columns, rows


def _warnings() -> list[str]:
    return [
        "SQL was produced by an LLM using your semantic layer + live schema, then policy-checked "
        "(read-only SELECT, allowlisted tables, row cap). Review before operational decisions."
    ]


def answer_question(connection_id: int, question: str, *, max_rows: int = 200) -> dict[str, Any]:
    t0 = time.perf_counter()
    conn = get_connection_record(connection_id)

    tables = db_engine.get_introspection_cache(connection_id)
    if not tables:
        eng0 = db_engine.make_engine(conn)
        try:
            tables = db_engine.introspect_schema(eng0, conn["source_type"])
        finally:
            eng0.dispose()
        db_engine.set_introspection_cache(connection_id, tables)

    if not tables:
        raise ValueError("No user tables visible for this connection. Check grants or schema.")

    allowed_names = {str(t["name"]) for t in tables if t.get("name")}
    sem = semantic_store.load_semantic()
    sem_txt = _format_semantic(sem)
    phy_txt = _format_physical_schema(tables)

    system_sql = _sql_system_prompt(conn["source_type"], max_rows)
    user_sql = f"{sem_txt}\n\n{phy_txt}\n\n## User question\n{question.strip()}"

    sql_gen = run_task("sql_gen", user_sql, system_prompt=system_sql)
    if sql_gen.get("error"):
        raise ValueError(str(sql_gen["error"]))
    if not sql_gen.get("live"):
        raise ValueError(
            f"No API key configured for sql_gen provider '{sql_gen.get('provider')}'. "
            "Set the matching environment variable (see README)."
        )

    raw_sql = (sql_gen.get("output") or "").strip()
    if not raw_sql:
        raise ValueError("SQL model returned an empty response.")

    try:
        prepared = sql_policy.prepare_readonly_select(
            raw_sql,
            source_type=conn["source_type"],
            allowed_table_names=allowed_names,
            max_rows=max_rows,
        )
    except ValueError as exc:
        raise ValueError(f"SQL policy rejected generated SQL: {exc}") from exc

    engine = db_engine.make_engine(conn)
    try:
        try:
            columns, rows = _execute_readonly(engine, prepared)
        except SQLAlchemyError as exc:
            raise ValueError(f"Query execution failed: {exc}") from exc
    finally:
        engine.dispose()

    sql = prepared
    elapsed_ms = int((time.perf_counter() - t0) * 1000)

    evidence: dict[str, Any] = {
        "query_kind": "llm_sql",
        "used_fallback": False,
        "execution_ms": elapsed_ms,
        "row_count": len(rows),
    }

    sample = json.dumps(rows[:40], default=str)
    user_ans = (
        f"User question:\n{question.strip()}\n\n"
        f"Executed SQL:\n{sql}\n\n"
        f"Columns: {', '.join(columns)}\n\n"
        f"Sample rows (up to 40, JSON array of arrays):\n{sample}\n"
    )
    system_ans = (
        "You are a business analyst. Answer in clear, concise prose (2–5 short sentences).\n"
        "Ground every factual claim in the provided rows and SQL; if evidence is thin, say so.\n"
        "Do not invent tables, metrics, or numbers that are not supported by the sample."
    )
    answer_gen = run_task("answer_gen", user_ans, system_prompt=system_ans)
    if answer_gen.get("error"):
        raise ValueError(str(answer_gen["error"]))
    if not answer_gen.get("live"):
        raise ValueError(
            f"No API key configured for answer_gen provider '{answer_gen.get('provider')}'. "
            "Set the matching environment variable (see README)."
        )

    answer = (answer_gen.get("output") or "").strip()
    if not answer:
        raise ValueError("Answer model returned an empty response.")

    warns = _warnings()

    sql_prof = get_profile_for_task("sql_gen")
    ans_prof = get_profile_for_task("answer_gen")

    return {
        "answer": answer,
        "sql": sql,
        "columns": columns,
        "rows": rows,
        "confidence": 0.82,
        "warnings": warns,
        "evidence": evidence,
        "meta": {
            "sql_model": sql_prof.get("model"),
            "answer_model": ans_prof.get("model"),
            "sql_task_note": (sql_gen.get("output") or "")[:4000],
            "answer_task_note": (answer_gen.get("output") or "")[:4000],
            "sql_live": True,
            "answer_live": True,
        },
    }
