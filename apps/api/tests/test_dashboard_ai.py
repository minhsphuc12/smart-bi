"""Unit tests for dashboard AI JSON extraction and normalization."""

from __future__ import annotations

import json

import pytest

from app.services import dashboard_ai


def test_extract_json_braces_inside_sql_string() -> None:
    """Greedy }}`` slicing would break when SQL contains a literal brace."""
    payload = {
        "widgets": [
            {
                "type": "kpi",
                "title": "Brace test",
                "sql": "SELECT CASE WHEN true THEN 1 ELSE 0 END AS x FROM t WHERE y LIKE '%}%' LIMIT 1",
            }
        ]
    }
    text = "Here you go:\n" + json.dumps(payload) + "\nThanks."
    parsed = dashboard_ai._extract_json_object(text)
    assert parsed is not None
    assert len(parsed["widgets"]) == 1


def test_extract_json_from_markdown_fence() -> None:
    raw = '```json\n{"widgets": [{"type": "line", "title": "A", "sql": "SELECT 1"}]}\n```'
    parsed = dashboard_ai._extract_json_object(raw)
    assert parsed["widgets"][0]["type"] == "line"


def test_unwrap_nested_dashboard_key() -> None:
    obj = {"dashboard": {"widgets": [{"type": "bar", "title": "B", "sql": "SELECT 1"}]}}
    unwrapped = dashboard_ai._unwrap_spec(obj)
    assert unwrapped is not None
    assert unwrapped["widgets"][0]["type"] == "bar"


def test_unwrap_data_wrapper() -> None:
    obj = {"data": {"widgets": [{"type": "table", "title": "T", "sql": "SELECT 1"}]}}
    assert dashboard_ai._unwrap_spec(obj) is not None


def test_normalize_type_aliases() -> None:
    spec = dashboard_ai.normalize_spec(
        {
            "widgets": [
                {"type": "pie", "title": "P", "sql": "SELECT 1"},
                {"type": "metric", "title": "M", "sql": "SELECT 1"},
                {"type": "grid", "title": "G", "sql": "SELECT 1"},
            ]
        }
    )
    types = [w["type"] for w in spec["widgets"]]
    assert types == ["bar", "kpi", "table"]


def test_normalize_rejects_unknown_type() -> None:
    """Unknown type with no SQL-like field cannot be coerced."""
    spec = dashboard_ai.normalize_spec({"widgets": [{"type": "heatmap", "title": "H"}]})
    assert spec["widgets"] == []


def test_normalize_unknown_type_with_sql_defaults_to_table() -> None:
    spec = dashboard_ai.normalize_spec(
        {"widgets": [{"type": "heatmap", "title": "H", "sql": "SELECT 1 AS x"}]}
    )
    assert len(spec["widgets"]) == 1 and spec["widgets"][0]["type"] == "table"


def test_unwrap_charts_key_instead_of_widgets() -> None:
    obj = {"title": "Dash", "charts": [{"type": "line", "title": "A", "sql": "SELECT 1"}]}
    u = dashboard_ai._unwrap_spec(obj)
    assert u is not None and u["widgets"][0]["type"] == "line"


def test_unwrap_root_json_array_of_widgets() -> None:
    arr = [{"type": "kpi", "title": "K", "sql": "SELECT 1"}]
    u = dashboard_ai._unwrap_spec(arr)
    assert u == {"widgets": arr}


def test_normalize_query_field_maps_to_sql() -> None:
    spec = dashboard_ai.normalize_spec(
        {"widgets": [{"type": "bar", "title": "B", "query": "SELECT 2 AS x"}]}
    )
    assert spec["widgets"][0].get("sql") == "SELECT 2 AS x"


def test_unwrap_case_insensitive_widgets_key() -> None:
    obj = {"Widgets": [{"type": "area", "title": "A", "sql": "SELECT 1"}]}
    u = dashboard_ai._unwrap_spec(obj)
    assert u is not None and len(u["widgets"]) == 1


def test_unwrap_single_widget_at_object_root() -> None:
    u = dashboard_ai._unwrap_spec({"type": "kpi", "title": "R", "sql": "SELECT 1"})
    assert u == {"widgets": [{"type": "kpi", "title": "R", "sql": "SELECT 1"}]}


def test_unwrap_widgets_key_json_string() -> None:
    inner = [{"type": "table", "title": "T", "sql": "SELECT 1"}]
    obj = {"widgets": json.dumps(inner)}
    u = dashboard_ai._unwrap_spec(obj)
    assert u["widgets"] == inner


def test_unwrap_chart_type_and_statement_fields() -> None:
    obj = {"charts": [{"chartType": "bar", "title": "x", "statement": "SELECT 1"}]}
    u = dashboard_ai._unwrap_spec(obj)
    assert u is not None
    spec = dashboard_ai.normalize_spec(u)
    assert spec["widgets"][0]["type"] == "bar"
    assert spec["widgets"][0]["sql"] == "SELECT 1"


def test_extract_embedded_json_array() -> None:
    text = 'Output:\n[{"type":"kpi","title":"K","sql":"SELECT 1"}]\nend'
    parsed = dashboard_ai._extract_json_object(text)
    assert isinstance(parsed, list) and parsed[0]["type"] == "kpi"
