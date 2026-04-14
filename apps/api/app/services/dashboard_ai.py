"""LLM-backed dashboard spec generation (create + AI edit).

Produces a normalized ``{"widgets": [...]}`` contract for the web preview.
Requires a configured LLM and a valid JSON response; callers should surface errors to the client.
"""

from __future__ import annotations

import json
import re
from typing import Any

from app.core.logging import logger
from app.routers.admin_connections import get_connection_record
from app.services import db_engine, semantic_store
from app.services.ai_router import run_task

_MAX_WIDGETS = 10
MAX_DASHBOARD_WIDGETS = _MAX_WIDGETS
_MAX_SQL_CHARS = 20_000
_ALLOWED_TYPES = frozenset({"line", "bar", "area", "kpi", "table"})
# Map common model synonyms to the strict widget contract.
_TYPE_ALIASES: dict[str, str] = {
    "pie": "bar",
    "donut": "bar",
    "column": "bar",
    "histogram": "bar",
    "time_series": "line",
    "timeseries": "line",
    "trend": "line",
    "scatter": "line",
    "metric": "kpi",
    "scalar": "kpi",
    "number": "kpi",
    "card": "kpi",
    "single_value": "kpi",
    "gauge": "kpi",
    "grid": "table",
    "data_grid": "table",
    "list": "table",
    "chart": "line",
}


def _balanced_json_object_slice(raw: str, start: int) -> str | None:
    """Slice one JSON object starting at raw[start] == '{', respecting double-quoted strings."""
    if start < 0 or start >= len(raw) or raw[start] != "{":
        return None
    depth = 0
    i = start
    in_str = False
    escape = False
    while i < len(raw):
        ch = raw[i]
        if in_str:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_str = False
            i += 1
            continue
        if ch == '"':
            in_str = True
            i += 1
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return raw[start : i + 1]
        i += 1
    return None


def _dashboard_system_prompt(*, edit_mode: bool, require_sql: bool, mart_yaml_block: str) -> str:
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
    base += (
        "\n## Business semantics (YAML)\n"
        "Use the following mart YAML for metrics, dimensions, and join logic when designing widget SQL and titles.\n\n"
        f"{mart_yaml_block.strip()}\n"
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


def _balanced_json_array_slice(raw: str, start: int) -> str | None:
    """Slice one JSON array starting at raw[start] == '[', respecting double-quoted strings."""
    if start < 0 or start >= len(raw) or raw[start] != "[":
        return None
    depth = 0
    i = start
    in_str = False
    escape = False
    while i < len(raw):
        ch = raw[i]
        if in_str:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_str = False
            i += 1
            continue
        if ch == '"':
            in_str = True
            i += 1
            continue
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                return raw[start : i + 1]
        i += 1
    return None


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
    idx_open_arr = raw.find("[")
    idx_open_obj = raw.find("{")
    # When the payload is a root-level array (often with preamble text), "[" appears before the
    # first "{". When the payload is an object, "{" almost always comes first — then prefer
    # object slices so we do not grab the inner "widgets": [...] array by mistake.
    if idx_open_arr >= 0 and (idx_open_obj < 0 or idx_open_arr < idx_open_obj):
        start_arr = idx_open_arr
        while start_arr >= 0:
            candidate = _balanced_json_array_slice(raw, start_arr)
            if candidate:
                try:
                    parsed_arr = json.loads(candidate)
                except json.JSONDecodeError:
                    parsed_arr = None
                else:
                    if isinstance(parsed_arr, list) and _list_looks_like_widgets(parsed_arr):
                        return parsed_arr
            start_arr = raw.find("[", start_arr + 1)
    start = raw.find("{")
    while start >= 0:
        candidate = _balanced_json_object_slice(raw, start)
        if candidate:
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                pass
        start = raw.find("{", start + 1)
    start_arr = raw.find("[")
    while start_arr >= 0:
        candidate = _balanced_json_array_slice(raw, start_arr)
        if candidate:
            try:
                parsed_arr = json.loads(candidate)
            except json.JSONDecodeError:
                parsed_arr = None
            else:
                if isinstance(parsed_arr, list) and _list_looks_like_widgets(parsed_arr):
                    return parsed_arr
        start_arr = raw.find("[", start_arr + 1)
    return None


_MAX_UNWRAP_DEPTH = 8
# JSON keys models often use instead of "widgets" (matched case-insensitively).
_WIDGET_LIST_KEYS = frozenset(
    {
        "widgets",
        "charts",
        "panels",
        "cards",
        "items",
        "components",
        "visualizations",
        "visualisations",
        "figures",
        "blocks",
        "elements",
        "views",
        "reports",
        "tiles",
        "graphs",
        "kpis",
        "visuals",
        "dashboard_widgets",
    }
)
_WRAPPER_KEYS = (
    "dashboard",
    "spec",
    "layout",
    "data",
    "response",
    "output",
    "result",
    "content",
    "answer",
    "json",
    "body",
    "payload",
)

_SQL_KEYS = ("sql", "query", "statement", "sqlQuery", "sql_query", "sqlText", "sql_text")
_TYPE_KEYS = (
    "type",
    "chartType",
    "chart_type",
    "kind",
    "widgetType",
    "widget_type",
    "vizType",
    "viz_type",
    "visualization_type",
)


def _first_sql_string(w: dict[str, Any]) -> str:
    for k in _SQL_KEYS:
        v = w.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return ""


def _raw_type_string(w: dict[str, Any]) -> str:
    for k in _TYPE_KEYS:
        v = w.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return ""


def _dict_signals_widgetish(d: dict[str, Any]) -> bool:
    raw = _raw_type_string(d).lower().replace("-", "_")
    resolved = _TYPE_ALIASES.get(raw, raw) if raw else ""
    if resolved in _ALLOWED_TYPES:
        return True
    return bool(_first_sql_string(d))


def _dict_has_nested_widget_list(d: dict[str, Any]) -> bool:
    for v in d.values():
        if isinstance(v, list) and len(v) > 0 and _list_looks_like_widgets(v):
            return True
    return False


def _list_looks_like_widgets(items: list[Any]) -> bool:
    """Heuristic: list of dicts intended as dashboard tiles (not arbitrary metadata arrays)."""
    if not isinstance(items, list):
        return False
    if len(items) == 0:
        return True
    if not all(isinstance(x, dict) for x in items):
        return False
    for x in items:
        if _dict_signals_widgetish(x):
            return True
    return False


def _coerce_list_value(v: Any) -> list[Any] | None:
    if isinstance(v, list):
        return v
    if isinstance(v, str):
        t = v.strip()
        if not t:
            return None
        try:
            parsed = json.loads(t)
        except json.JSONDecodeError:
            return None
        if isinstance(parsed, list):
            return parsed
    return None


def _widgets_list_from_mapping(obj: dict[str, Any]) -> list[Any] | None:
    for k, v in obj.items():
        lk = str(k).lower().replace("-", "_")
        if lk not in _WIDGET_LIST_KEYS:
            continue
        coerced = _coerce_list_value(v)
        if coerced is not None and _list_looks_like_widgets(coerced):
            return coerced
    return None


def _unwrap_spec(obj: Any, depth: int = 0) -> dict[str, Any] | None:
    if depth > _MAX_UNWRAP_DEPTH:
        return None
    if isinstance(obj, list):
        if _list_looks_like_widgets(obj):
            return {"widgets": obj}
        return None
    if not isinstance(obj, dict):
        return None

    found = _widgets_list_from_mapping(obj)
    if found is not None:
        return {"widgets": found}

    if _dict_signals_widgetish(obj) and not _dict_has_nested_widget_list(obj):
        return {"widgets": [obj]}

    for key in _WRAPPER_KEYS:
        inner = obj.get(key)
        if isinstance(inner, dict):
            got = _unwrap_spec(inner, depth + 1)
            if got is not None:
                return got
        elif isinstance(inner, list):
            got = _unwrap_spec(inner, depth + 1)
            if got is not None:
                return got

    for v in obj.values():
        if isinstance(v, dict):
            got = _unwrap_spec(v, depth + 1)
            if got is not None:
                return got
        if isinstance(v, list) and v and all(isinstance(x, dict) for x in v):
            if _list_looks_like_widgets(v):
                return {"widgets": v}
    return None


def _normalize_widget(w: Any) -> dict[str, Any] | None:
    if not isinstance(w, dict):
        return None
    sql_src = _first_sql_string(w)
    raw_type = _raw_type_string(w).lower().replace("-", "_")
    wtype = _TYPE_ALIASES.get(raw_type, raw_type) if raw_type else ""
    if wtype not in _ALLOWED_TYPES:
        if sql_src:
            wtype = "table"
        else:
            return None
    title = str(w.get("title") or w.get("name") or "").strip()
    if not title:
        title = f"{wtype.title()} chart"
    out: dict[str, Any] = {"type": wtype, "title": title[:120]}
    for key in ("x", "y", "field", "description"):
        if w.get(key) is not None:
            val = str(w.get(key)).strip()
            if val:
                out[key] = val[:200]
    if sql_src:
        out["sql"] = sql_src[:_MAX_SQL_CHARS]
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


def _log_dashboard_ai_debug(
    *,
    stage: str,
    ai_meta: dict[str, Any],
    raw_out: str,
    parsed: Any | None = None,
    unwrapped: dict[str, Any] | None = None,
    spec: dict[str, Any] | None = None,
) -> None:
    """Emit detailed dashboard_gen payload logs to help debug model format mismatches."""
    logger.warning(
        "dashboard_ai_debug",
        extra={
            "stage": stage,
            "provider": ai_meta.get("provider"),
            "model": ai_meta.get("model"),
            "live": ai_meta.get("live"),
            "error": ai_meta.get("error"),
            "raw_len": len(raw_out),
            "raw_output": raw_out,
            "parsed_type": type(parsed).__name__ if parsed is not None else None,
            "parsed_preview": parsed,
            "has_unwrapped": unwrapped is not None,
            "unwrapped_keys": sorted(unwrapped.keys()) if isinstance(unwrapped, dict) else None,
            "unwrapped_widget_count": len(unwrapped.get("widgets", [])) if isinstance(unwrapped, dict) else None,
            "normalized_widget_count": len(spec.get("widgets", [])) if isinstance(spec, dict) else None,
        },
    )


def generate_spec(
    *,
    user_prompt: str,
    connection_id: int | None = None,
    existing_spec: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Returns keys: spec (dict), ai (run_task result), change_summary (str).

    Raises:
        ValueError: Missing LLM configuration, vendor error, empty model output, or no usable widgets in JSON.
    """
    edit_mode = existing_spec is not None
    schema = _schema_context(connection_id)
    require_sql = connection_id is not None
    mart_yaml = semantic_store.load_mart_yaml_bundle_text()
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
        system_prompt=_dashboard_system_prompt(
            edit_mode=edit_mode, require_sql=require_sql, mart_yaml_block=mart_yaml
        ),
    )
    if ai.get("error"):
        raise ValueError(str(ai["error"]))
    if not ai.get("live"):
        raise ValueError(
            f"No API key configured for dashboard_gen provider '{ai.get('provider')}'. "
            "Set the matching environment variable (see README)."
        )

    raw_out = str(ai.get("output") or "")
    parsed = _extract_json_object(raw_out)
    _log_dashboard_ai_debug(stage="parsed", ai_meta=ai, raw_out=raw_out, parsed=parsed)
    if parsed is None:
        _log_dashboard_ai_debug(stage="parse_failed", ai_meta=ai, raw_out=raw_out, parsed=parsed)
        raise ValueError(
            "Dashboard model output was not valid JSON (or could not be extracted). "
            "Try again with a shorter prompt, check the model response for extra text outside JSON, "
            "or raise dashboard_gen max_tokens in Admin → AI routing if replies look truncated."
        )
    unwrapped = _unwrap_spec(parsed)
    if unwrapped is None:
        _log_dashboard_ai_debug(stage="unwrap_failed", ai_meta=ai, raw_out=raw_out, parsed=parsed)
        raise ValueError(
            'Dashboard model JSON must include a widget array: prefer top-level "widgets", or '
            'nested under keys like "dashboard" / "spec" / "data". '
            'Known alternate array names are also accepted (e.g. "charts", "panels"). '
            "Each entry should be an object with at least type or sql/query."
        )
    spec = normalize_spec(unwrapped)
    _log_dashboard_ai_debug(
        stage="normalized",
        ai_meta=ai,
        raw_out=raw_out,
        parsed=parsed,
        unwrapped=unwrapped,
        spec=spec,
    )
    if not spec["widgets"]:
        raw_widgets = unwrapped.get("widgets")
        n = len(raw_widgets) if isinstance(raw_widgets, list) else 0
        _log_dashboard_ai_debug(
            stage="no_usable_widgets",
            ai_meta=ai,
            raw_out=raw_out,
            parsed=parsed,
            unwrapped=unwrapped,
            spec=spec,
        )
        raise ValueError(
            f"Dashboard model returned {n} widget entr{'y' if n == 1 else 'ies'} but none matched the "
            f"required schema (type must be one of: {', '.join(sorted(_ALLOWED_TYPES))}, "
            "each object needs a recognized type and optional fields per API docs). "
            "Try naming chart types explicitly as line, bar, area, kpi, or table."
        )

    summary = str(ai.get("output") or "").strip()
    if len(summary) > 280:
        summary = summary[:277] + "…"

    return {"spec": spec, "ai": ai, "change_summary": summary}
