"""File-backed persistence for user dashboards and version history (JSON)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def store_path() -> Path:
    """Path to dashboards JSON. Set SMART_BI_DASHBOARDS_FILE to override."""
    env = os.environ.get("SMART_BI_DASHBOARDS_FILE")
    if env:
        return Path(env).expanduser().resolve()
    return Path(__file__).resolve().parent.parent.parent / "data" / "dashboards.json"


def _deserialize_versions(raw: Any) -> dict[int, list[dict[str, Any]]]:
    if not isinstance(raw, dict):
        return {}
    out: dict[int, list[dict[str, Any]]] = {}
    for key, val in raw.items():
        try:
            ikey = int(key)
        except (TypeError, ValueError):
            continue
        if not isinstance(val, list):
            continue
        rows: list[dict[str, Any]] = []
        for item in val:
            if isinstance(item, dict) and isinstance(item.get("version"), int):
                rows.append(item)
        out[ikey] = rows
    return out


def _deserialize_dashboards(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    out: list[dict[str, Any]] = []
    for item in raw:
        if isinstance(item, dict) and isinstance(item.get("id"), int):
            out.append(item)
    return out


def load_state() -> tuple[list[dict[str, Any]], dict[int, list[dict[str, Any]]]]:
    path = store_path()
    if not path.exists():
        return [], {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return [], {}
    if not isinstance(data, dict):
        return [], {}
    dashboards = _deserialize_dashboards(data.get("dashboards"))
    versions = _deserialize_versions(data.get("versions"))
    return dashboards, versions


def _serialize_versions(versions: dict[int, list[dict[str, Any]]]) -> dict[str, Any]:
    return {str(k): v for k, v in sorted(versions.items(), key=lambda x: x[0])}


def save_state(
    dashboards: list[dict[str, Any]],
    versions: dict[int, list[dict[str, Any]]],
) -> None:
    path = store_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    payload = {
        "dashboards": dashboards,
        "versions": _serialize_versions(versions),
    }
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)
