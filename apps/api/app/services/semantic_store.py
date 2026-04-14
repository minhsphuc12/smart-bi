"""Admin semantic layer CRUD persists to JSON; LLM prompts use raw YAML under ``mart/``."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

_KEYS = ("tables", "relationships", "dictionary", "metrics")
_MAX_MART_SINGLE_FILE_BYTES = 512 * 1024
_MART_WALK_MAX_ANCESTORS = 12


def _discover_default_mart_dir() -> Path:
    """
    Find ``<monorepo>/mart`` by walking ancestors of this module (no env).
    Prefer this over a fixed parent depth so small layout changes do not break paths.
    """
    here = Path(__file__).resolve().parent
    for anc in [here, *here.parents[:_MART_WALK_MAX_ANCESTORS]]:
        cand = anc / "mart"
        if cand.is_dir():
            return cand
    # Last-resort layout: .../apps/api/app/services → repo root at parents[4]
    return Path(__file__).resolve().parents[4] / "mart"


def mart_semantic_dir() -> Path:
    """Directory of semantic YAML files for LLM context. Override with ``SMART_BI_SEMANTIC_MART_DIR``."""
    env = os.environ.get("SMART_BI_SEMANTIC_MART_DIR")
    if env:
        return Path(env).expanduser().resolve()
    return _discover_default_mart_dir()


def load_mart_yaml_bundle_text(*, max_total_chars: int = 48_000) -> str:
    """
    Concatenate all ``*.yml`` / ``*.yaml`` under the mart directory (recursive) as plain text
    for system prompts. The LLM interprets YAML directly; files are not merged into JSON.
    """
    root = mart_semantic_dir().resolve()
    intro = (
        "## Semantic mart (YAML)\n"
        "The following files are the authoritative business semantic layer. "
        "Use them for joins, grain, metrics, and naming; physical columns must still match "
        "the PHYSICAL SCHEMA / datasource lists provided separately.\n\n"
    )
    if not root.is_dir():
        return (
            intro
            + f"_(`{root}` is missing or not a directory — set `SMART_BI_SEMANTIC_MART_DIR` or create `mart/` at the repo root.)_\n"
        )

    paths = sorted(
        {p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in (".yml", ".yaml")},
        key=lambda p: str(p).lower(),
    )
    if not paths:
        return intro + "_No `.yml` / `.yaml` files found in the mart directory._\n"

    parts: list[str] = [intro]
    used = len(intro)
    truncated = False
    for path in paths:
        try:
            body = path.read_text(encoding="utf-8", errors="replace").strip()
        except OSError:
            continue
        try:
            rel = path.resolve().relative_to(root).as_posix()
        except ValueError:
            rel = path.name
        block = f"### File: `{rel}`\n```yaml\n{body}\n```\n\n"
        if used + len(block) > max_total_chars:
            truncated = True
            break
        parts.append(block)
        used += len(block)

    out = "".join(parts)
    if truncated:
        out += f"\n_(YAML bundle truncated after ~{max_total_chars} characters; add `SMART_BI_SEMANTIC_MART_DIR` or reduce file size.)_\n"
    return out


def _mart_yaml_paths_sorted(root: Path) -> list[Path]:
    if not root.is_dir():
        return []
    return sorted(
        {p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in (".yml", ".yaml")},
        key=lambda p: str(p).lower(),
    )


def list_mart_yaml_entries() -> dict[str, Any]:
    """Read-only index of YAML files under the mart directory (for Admin UI)."""
    resolved = mart_semantic_dir().resolve()
    if not resolved.is_dir():
        return {"root": str(resolved), "exists": False, "files": []}
    files: list[dict[str, Any]] = []
    for path in _mart_yaml_paths_sorted(resolved):
        try:
            rel = path.resolve().relative_to(resolved).as_posix()
        except ValueError:
            rel = path.name
        try:
            size = path.stat().st_size
        except OSError:
            size = -1
        files.append({"path": rel, "bytes": size})
    return {"root": str(resolved), "exists": True, "files": files}


def read_mart_yaml_relative(relative_path: str, *, max_bytes: int = _MAX_MART_SINGLE_FILE_BYTES) -> str:
    """
    Read a single YAML file under the mart root. ``relative_path`` must be a relative POSIX path
    without ``..`` segments. Raises ``FileNotFoundError`` or ``ValueError`` on invalid input.
    """
    root = mart_semantic_dir().resolve()
    if not root.is_dir():
        raise FileNotFoundError("mart directory missing or not a directory")
    raw = (relative_path or "").strip().replace("\\", "/")
    if not raw or raw.startswith("/"):
        raise ValueError("invalid path")
    parts = Path(raw).parts
    if ".." in parts:
        raise ValueError("invalid path")
    candidate = (root / raw).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError("path escapes mart root") from exc
    if not candidate.is_file():
        raise FileNotFoundError("file not found")
    if candidate.suffix.lower() not in (".yml", ".yaml"):
        raise ValueError("not a YAML file")
    try:
        size = candidate.stat().st_size
    except OSError as exc:
        raise FileNotFoundError("cannot stat file") from exc
    if size > max_bytes:
        raise ValueError(f"file exceeds {max_bytes} bytes")
    return candidate.read_text(encoding="utf-8", errors="replace")


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
