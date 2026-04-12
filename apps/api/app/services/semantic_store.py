"""File-backed persistence for admin semantic layer metadata (JSON)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

_KEYS = ("tables", "relationships", "dictionary", "metrics")


def store_path() -> Path:
    """Path to semantic JSON. Set SMART_BI_SEMANTIC_FILE to override."""
    env = os.environ.get("SMART_BI_SEMANTIC_FILE")
    if env:
        return Path(env).expanduser().resolve()
    return Path(__file__).resolve().parent.parent.parent / "data" / "semantic.json"


def _normalize_rows(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    out: list[dict[str, Any]] = []
    for item in raw:
        if isinstance(item, dict) and isinstance(item.get("id"), int) and isinstance(item.get("name"), str):
            out.append(
                {
                    "id": item["id"],
                    "name": item["name"],
                    "description": item.get("description") if isinstance(item.get("description"), str) else "",
                }
            )
    return out


def load_semantic() -> dict[str, list[dict[str, Any]]]:
    path = store_path()
    base = {k: [] for k in _KEYS}
    if not path.exists():
        return base
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return base
    if not isinstance(data, dict):
        return base
    for key in _KEYS:
        base[key] = _normalize_rows(data.get(key))
    return base


def save_semantic(payload: dict[str, list[dict[str, Any]]]) -> None:
    path = store_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    body = {k: _normalize_rows(payload.get(k)) for k in _KEYS}
    tmp = path.with_suffix(path.suffix + ".tmp")
    text = json.dumps(body, indent=2, ensure_ascii=False) + "\n"
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)
