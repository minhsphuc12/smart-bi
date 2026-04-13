"""LLM-backed dashboard spec generation (create + AI edit).

Produces a normalized ``{"widgets": [...]}`` contract for the web preview.
When the model is unavailable or JSON parsing fails, falls back to a small heuristic spec.
"""

from __future__ import annotations

import json
import re
from typing import Any

from app.routers.admin_connections import get_connection_record
from app.services import db_engine
from app.services.ai_router import run_task

_MAX_WIDGETS = 10
_MAX_SQL_CHARS = 20_000
_ALLOWED_TYPES = frozenset({"line", "bar", "area", "kpi", "table"})


def _dashboard_system_prompt(*, edit_mode: bool, require_sql: bool) -> str:
    sql_block = ""
    if require_sql:
        sql_block = (
            "\nEach widget MUST include a **sql** field: exactly one read-only `SELECT` or `WITH ... SELECT` string.\n"
            "- Use **only** tables (and schema qualifiers) that appear in the PHYSICAL SCHEMA list above.\n"
            "- **kpi**: return exactly **one row**; the primary numeric value should be in the **first** column "
            "(optionally name the column to match **field**).\n"
            "- **line**, **bar**, **area**: return multiple rows; **first column** = dimension (time/category), "
            "**second column** = numeric measure (aliases should align with **x** / **y** hints when possible).\n"
            "- **table**: return a bounded tabular preview (the server enforces a row cap).\n"
            "- No DDL/DML, no multiple statements, no comments-only replies.\n"
            "- Do not wrap SQL in markdown fences inside the JSON string; escape quotes as needed for valid JSON.\n"
        )
    else:
        sql_block = (
            "\nSet each widget's **sql** to an empty string \"\" (no datasource schema was provided for this request).\n"
        )

    base = (
        "You are a Smart BI dashboard spec generator for business users.\n"
        "Reply with a single JSON object only — no markdown fences, no commentary before or after.\n\n"
        "Required JSON shape:\n"
        "{\n"
        '  "widgets": [\n'
        "    {\n"
        '      "type": "line" | "bar" | "area" | "kpi" | "table",\n'
        '      "title": "short title",\n'
        '      "x": "optional dimension column hint",\n'
        '      "y": "optional measure column hint",\n'
        '      "field": "optional field for kpi or single-metric table",\n'
        '      "description": "optional one sentence",\n'
        '      "sql": "SELECT ..."\n'
        "    }\n"
        "  ]\n"
        "}\n\n"
        f"Rules: 1 to {_MAX_WIDGETS} widgets; types must be exactly one of the listed literals; "
        "use plausible column-like snake_case names when you infer them.\n"
        f"{sql_block}"
    )
    if edit_mode:
        base += (
            "\nYou will be given the current dashboard spec as JSON. "
            "Apply the user's instruction and return the FULL updated object with the same top-level shape.\n"
        )
    return base


def _ensure_introspection_tables(connection_id: int) -> list[dict[str, Any]]:
    """Populate introspection cache when missing (same pattern as NL2SQL / widget query runner)."""
    cached = db_engine.get_introspection_cache(connection_id)
    if cached:
        return cached
    conn = get_connection_record(connection_id)
    eng = db_engine.make_engine(conn)
    try:
        tables = db_engine.introspect_schema(eng, conn["source_type"])
    finally:
        eng.dispose()
    db_engine.set_introspection_cache(connection_id, tables)
    return tables


def _schema_context(connection_id: int | None) -> str:
    if connection_id is None:
        return ""
    tables = _ensure_introspection_tables(connection_id)
    if not tables:
        return (
            "\n## Datasource schema\n"
            "Introspection returned no visible tables for this connection. "
            "Set each widget's **sql** to an empty string \"\" until an admin fixes grants or connection settings.\n"
        )
    lines: list[str] = ["\n## Datasource schema (cached physical tables, truncated)\n"]
    for t in tables[:40]:
        name = str(t.get("name") or "")
        cols = t.get("columns") or []
        col_names = [str(c.get("name") or c) if isinstance(c, dict) else str(c) for c in cols[:16]]
        lines.append(f"- {name}: {', '.join(col_names)}\n")
    if len(tables) > 40:
        lines.append(f"... and {len(tables) - 40} more tables omitted.\n")
    return "".join(lines)


def _extract_json_object(text: str) -> Any | None:
    raw = (text or "").strip()
    if not raw:
        return None
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw, re.IGNORECASE)
    if fence:
        raw = fence.group(1).strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    start = raw.find("{")
    end = raw.rfind("}")
    if start >= 0 and end > start:
        try:
            return json.loads(raw[start : end + 1])
        except json.JSONDecodeError:
            return None
    return None


def _unwrap_spec(obj: Any) -> dict[str, Any] | None:
    if not isinstance(obj, dict):
        return None
    if "widgets" in obj and isinstance(obj["widgets"], list):
        return obj
    for key in ("dashboard", "spec", "layout"):
        inner = obj.get(key)
        if isinstance(inner, dict) and isinstance(inner.get("widgets"), list):
            return inner
    return None


def _normalize_widget(w: Any) -> dict[str, Any] | None:
    if not isinstance(w, dict):
        return None
    wtype = str(w.get("type") or "").strip().lower()
    if wtype not in _ALLOWED_TYPES:
        return None
    title = str(w.get("title") or "").strip()
    if not title:
        title = f"{wtype.title()} chart"
    out: dict[str, Any] = {"type": wtype, "title": title[:120]}
    for key in ("x", "y", "field", "description"):
        if w.get(key) is not None:
            val = str(w.get(key)).strip()
            if val:
                out[key] = val[:200]
    if isinstance(w.get("sql"), str):
        sq = w["sql"].strip()
        if sq:
            out["sql"] = sq[:_MAX_SQL_CHARS]
    return out


def normalize_spec(raw: dict[str, Any] | None) -> dict[str, Any]:
    if not raw or not isinstance(raw.get("widgets"), list):
        return {"widgets": []}
    widgets: list[dict[str, Any]] = []
    for item in raw["widgets"]:
        nw = _normalize_widget(item)
        if nw:
            widgets.append(nw)
        if len(widgets) >= _MAX_WIDGETS:
            break
    return {"widgets": widgets}


def _fallback_widgets(user_prompt: str) -> list[dict[str, Any]]:
    hint = (user_prompt or "").strip().split("\n")[0][:80] or "Overview"
    return [
        {
            "type": "line",
            "title": f"Trend — {hint}",
            "x": "date",
            "y": "amount",
            "description": "Heuristic placeholder; configure LLM keys and a datasource for executable SQL.",
        },
        {
            "type": "kpi",
            "title": "Key metric",
            "field": "amount",
            "description": "Heuristic placeholder KPI.",
        },
    ]


def generate_spec(
    *,
    user_prompt: str,
    connection_id: int | None = None,
    existing_spec: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Returns keys: spec (dict), ai (run_task result), parse_fallback (bool), change_summary (str).
    """
    edit_mode = existing_spec is not None
    schema = _schema_context(connection_id)
    require_sql = connection_id is not None
    if edit_mode:
        user_body = (
            f"Current dashboard spec (JSON):\n{json.dumps(existing_spec, indent=2)}\n\n"
            f"User instruction:\n{user_prompt.strip()}\n"
        )
    else:
        user_body = f"User request for a new dashboard:\n{user_prompt.strip()}\n"

    ai = run_task(
        "dashboard_gen",
        user_body + schema,
        system_prompt=_dashboard_system_prompt(edit_mode=edit_mode, require_sql=require_sql),
    )
    parse_fallback = False
    parsed = _extract_json_object(str(ai.get("output") or ""))
    unwrapped = _unwrap_spec(parsed) if parsed is not None else None
    spec = normalize_spec(unwrapped) if unwrapped else {"widgets": []}

    if not spec["widgets"]:
        parse_fallback = True
        spec = {"widgets": _fallback_widgets(user_prompt)}

    summary = str(ai.get("output") or "").strip()
    if len(summary) > 280:
        summary = summary[:277] + "…"
    if parse_fallback and ai.get("live"):
        summary = "Model returned no usable JSON; applied heuristic widget layout. " + (summary or "")
    elif parse_fallback:
        summary = "LLM not configured or failed; applied heuristic widget layout."

    return {"spec": spec, "ai": ai, "parse_fallback": parse_fallback, "change_summary": summary}
