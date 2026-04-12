"""Parse and harden LLM-generated SQL: read-only SELECT, allowlisted tables, row cap."""

from __future__ import annotations

import re
from typing import Iterable

import sqlglot
from sqlglot import exp

_FORBIDDEN = (
    exp.Insert,
    exp.Update,
    exp.Delete,
    exp.Drop,
    exp.Create,
    exp.Alter,
    exp.Merge,
    exp.Command,
)


def sqlglot_read_dialect(source_type: str) -> str:
    if source_type == "postgresql":
        return "postgres"
    if source_type == "mysql":
        return "mysql"
    if source_type == "oracle":
        return "oracle"
    raise ValueError(f"Unsupported source_type for SQL policy: {source_type}")


def extract_sql_from_llm(raw: str) -> str:
    """Strip markdown fences and leading prose; keep first SQL-looking segment."""
    s = raw.strip()
    fence = re.search(r"```(?:sql)?\s*([\s\S]*?)```", s, re.IGNORECASE)
    if fence:
        return fence.group(1).strip()
    # First line that looks like SELECT / WITH
    for line in s.splitlines():
        t = line.strip()
        if t.upper().startswith("SELECT") or t.upper().startswith("WITH"):
            idx = s.upper().find(t[:5].upper())
            return s[idx:].strip() if idx >= 0 else t
    return s


def _allowlist_sets(table_names: Iterable[str]) -> tuple[set[str], set[str]]:
    full: set[str] = set()
    bare: set[str] = set()
    for raw in table_names:
        name = str(raw).strip()
        if not name:
            continue
        low = name.lower()
        full.add(low)
        bare.add(low.split(".")[-1])
    return full, bare


def _table_match_variants(table: exp.Table) -> set[str]:
    parts: list[str] = []
    if getattr(table, "catalog", None):
        parts.append(str(table.catalog))
    if getattr(table, "db", None):
        parts.append(str(table.db))
    parts.append(str(table.name))
    full = ".".join(p for p in parts if p).lower()
    bare = str(table.name).lower()
    out = {full, bare}
    if "." in full:
        out.add(full.split(".")[-1])
    return {x for x in out if x}


def _forbidden_present(root: exp.Expression) -> str | None:
    for cls in _FORBIDDEN:
        node = root.find(cls)
        if node is not None:
            return cls.__name__
    return None


def _cte_aliases(root: exp.Expression) -> set[str]:
    """Bare CTE names (lowercase) defined anywhere in the tree."""
    names: set[str] = set()
    for w in root.find_all(exp.With):
        for e in w.expressions:
            if isinstance(e, exp.CTE) and e.alias:
                names.add(str(e.alias).lower())
    return names


def _ensure_limit(root: exp.Expression, max_rows: int) -> exp.Expression:
    """Attach LIMIT / FETCH to the outermost SELECT or UNION."""
    if isinstance(root, exp.With):
        inner = root.this
        new_inner = _ensure_limit(inner, max_rows)
        if new_inner is not inner:
            root.set("this", new_inner)
        return root
    if isinstance(root, (exp.Select, exp.Union)):
        if root.args.get("limit") is None:
            return root.limit(max_rows)
    return root


def prepare_readonly_select(
    raw_sql: str,
    *,
    source_type: str,
    allowed_table_names: Iterable[str],
    max_rows: int = 200,
) -> str:
    """
    Validate LLM SQL and return a dialect-specific string safe to execute read-only.

    Raises ValueError on policy violations or parse errors.
    """
    read = sqlglot_read_dialect(source_type)
    sql = extract_sql_from_llm(raw_sql).strip().rstrip(";").strip()
    if not sql:
        raise ValueError("Empty SQL.")

    try:
        parsed = sqlglot.parse_one(sql, read=read)
    except sqlglot.errors.ParseError as exc:
        raise ValueError(f"Could not parse SQL: {exc}") from exc

    reason = _forbidden_present(parsed)
    if reason:
        raise ValueError(f"Forbidden SQL construct: {reason}")

    if not isinstance(parsed, (exp.Select, exp.Union, exp.With)):
        raise ValueError("Only SELECT statements (optionally WITH) are allowed.")

    full, bare = _allowlist_sets(allowed_table_names)
    cte_names = _cte_aliases(parsed)
    for table in parsed.find_all(exp.Table):
        bare_name = str(table.name).lower()
        if bare_name in cte_names:
            continue
        variants = _table_match_variants(table)
        if not any(v in full or v in bare or v.split(".")[-1] in bare for v in variants):
            raise ValueError(f"Table '{table}' is not in the connection allowlist.")

    capped = _ensure_limit(parsed, max_rows)
    return capped.sql(dialect=read)
