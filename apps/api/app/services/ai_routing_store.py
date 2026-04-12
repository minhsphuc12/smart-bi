"""File-backed persistence for admin AI routing profiles (JSON)."""

from __future__ import annotations

import copy
import json
import os
from pathlib import Path
from typing import Any

DEFAULT_PROFILES: dict[str, dict[str, Any]] = {
    "sql_gen": {"provider": "openai", "model": "gpt-4o-mini", "temperature": 0.0, "max_tokens": 1200},
    "answer_gen": {
        "provider": "anthropic",
        "model": "claude-sonnet-4-20250514",
        "temperature": 0.2,
        "max_tokens": 800,
    },
    "dashboard_gen": {
        "provider": "google",
        "model": "gemini-2.5-flash",
        "temperature": 0.1,
        "max_tokens": 1500,
    },
    "extract_classify": {
        "provider": "openai",
        "model": "gpt-4o-mini",
        "temperature": 0.0,
        "max_tokens": 400,
    },
}

_PROFILE_FIELDS = ("provider", "model", "temperature", "max_tokens", "timeout", "cost_limit")


def store_path() -> Path:
    """Path to AI routing JSON. Set SMART_BI_AI_ROUTING_FILE to override."""
    env = os.environ.get("SMART_BI_AI_ROUTING_FILE")
    if env:
        return Path(env).expanduser().resolve()
    return Path(__file__).resolve().parent.parent.parent / "data" / "ai_routing.json"


def load_profiles() -> dict[str, dict[str, Any]]:
    path = store_path()
    out = copy.deepcopy(DEFAULT_PROFILES)
    if not path.exists():
        return out
    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except (OSError, json.JSONDecodeError):
        return out
    if not isinstance(data, dict):
        return out
    for task, profile in data.items():
        if task not in out or not isinstance(profile, dict):
            continue
        merged = dict(out[task])
        for field in _PROFILE_FIELDS:
            if field in profile:
                merged[field] = profile[field]
        out[task] = merged
    return out


def save_profiles(profiles: dict[str, dict[str, Any]]) -> None:
    path = store_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    to_write = {k: dict(profiles[k]) for k in sorted(DEFAULT_PROFILES) if k in profiles}
    tmp = path.with_suffix(path.suffix + ".tmp")
    text = json.dumps(to_write, indent=2, ensure_ascii=False) + "\n"
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)
