"""File-backed persistence for admin datasource connections (JSON)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def store_path() -> Path:
    """Path to the connections JSON file. Set SMART_BI_CONNECTIONS_FILE to override."""
    env = os.environ.get("SMART_BI_CONNECTIONS_FILE")
    if env:
        return Path(env).expanduser().resolve()
    # apps/api/app/services/connection_store.py -> apps/api/data/connections.json
    return Path(__file__).resolve().parent.parent.parent / "data" / "connections.json"


def load_connections() -> list[dict[str, Any]]:
    path = store_path()
    if not path.exists():
        return []
    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(data, list):
        return []
    out: list[dict[str, Any]] = []
    for item in data:
        if isinstance(item, dict) and isinstance(item.get("id"), int):
            out.append(item)
    return out


def save_connections(connections: list[dict[str, Any]]) -> None:
    path = store_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    text = json.dumps(connections, indent=2, ensure_ascii=False) + "\n"
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)
