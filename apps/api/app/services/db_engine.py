"""Real database connectivity: URLs, ping, introspection, and safe read previews."""

from __future__ import annotations

import re
from typing import Any, Literal
from urllib.parse import quote_plus

from sqlalchemy import MetaData, Table, create_engine, desc, func, select, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import NullPool

SourceType = Literal["oracle", "postgresql", "mysql"]

_introspection_cache: dict[int, list[dict[str, Any]]] = {}

CONNECT_TIMEOUT_SEC = 12


def clear_introspection_cache(connection_id: int | None = None) -> None:
    if connection_id is None:
        _introspection_cache.clear()
    else:
        _introspection_cache.pop(connection_id, None)


def get_introspection_cache(connection_id: int) -> list[dict[str, Any]] | None:
    cached = _introspection_cache.get(connection_id)
    return list(cached) if cached is not None else None


def set_introspection_cache(connection_id: int, tables: list[dict[str, Any]]) -> None:
    _introspection_cache[connection_id] = tables


def build_connection_url(conn: dict[str, Any]) -> str:
    user = quote_plus(conn["username"])
    pwd = quote_plus(conn.get("password") or "")
    host = conn["host"]
    port = int(conn["port"])
    kind: SourceType = conn["source_type"]

    if kind == "oracle":
        service = conn.get("service_name") or ""
        if not service.strip():
            raise ValueError("service_name is required for Oracle")
        return (
            f"oracle+oracledb://{user}:{pwd}@{host}:{port}/"
            f"?service_name={quote_plus(service.strip())}"
        )
    if kind == "postgresql":
        db = conn.get("database") or ""
        if not db.strip():
            raise ValueError("database is required for PostgreSQL")
        return f"postgresql+psycopg://{user}:{pwd}@{host}:{port}/{quote_plus(db.strip())}"
    if kind == "mysql":
        db = conn.get("database") or ""
        if not db.strip():
            raise ValueError("database is required for MySQL")
        return (
            f"mysql+pymysql://{user}:{pwd}@{host}:{port}/{quote_plus(db.strip())}"
            "?charset=utf8mb4"
        )
    raise ValueError(f"Unsupported source_type: {kind}")


def _connect_args(source_type: SourceType) -> dict[str, Any]:
    if source_type == "postgresql":
        return {"connect_timeout": CONNECT_TIMEOUT_SEC}
    if source_type == "mysql":
        return {"connect_timeout": CONNECT_TIMEOUT_SEC}
    if source_type == "oracle":
        return {"tcp_connect_timeout": CONNECT_TIMEOUT_SEC}
    return {}


def make_engine(conn: dict[str, Any]) -> Engine:
    kind: SourceType = conn["source_type"]
    url = build_connection_url(conn)
    return create_engine(
        url,
        poolclass=NullPool,
        pool_pre_ping=True,
        connect_args=_connect_args(kind),
    )


def ping_engine(engine: Engine, source_type: SourceType) -> None:
    stmt = text("SELECT 1 FROM DUAL") if source_type == "oracle" else text("SELECT 1")
    with engine.connect() as connection:
        connection.execute(stmt)


def _serialize_cell(value: Any) -> Any:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:
            return str(value)
    if isinstance(value, (bytes, bytearray, memoryview)):
        raw = bytes(value)
        if len(raw) > 256:
            return raw[:256].decode("utf-8", errors="replace") + "…"
        return raw.decode("utf-8", errors="replace")
    return value


def introspect_schema(engine: Engine, source_type: SourceType) -> list[dict[str, Any]]:
    """Return [{name: str, columns: [str, ...]}, ...] grouped by table."""
    by_table: dict[str, list[str]] = {}
    try:
        with engine.connect() as connection:
            if source_type == "postgresql":
                sql = text(
                    """
                    SELECT table_schema, table_name, column_name
                    FROM information_schema.columns
                    WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
                      AND table_schema NOT LIKE 'pg\\_%%' ESCAPE '\\'
                    ORDER BY table_schema, table_name, ordinal_position
                    """
                )
                for row in connection.execute(sql):
                    sch, tname, cname = row[0], row[1], row[2]
                    display = tname if sch == "public" else f"{sch}.{tname}"
                    by_table.setdefault(display, []).append(cname)
            elif source_type == "mysql":
                sql = text(
                    """
                    SELECT TABLE_NAME, COLUMN_NAME
                    FROM information_schema.COLUMNS
                    WHERE TABLE_SCHEMA = DATABASE()
                    ORDER BY TABLE_NAME, ORDINAL_POSITION
                    """
                )
                for row in connection.execute(sql):
                    by_table.setdefault(row[0], []).append(row[1])
            elif source_type == "oracle":
                sql = text(
                    """
                    SELECT table_name, column_name
                    FROM user_tab_columns
                    ORDER BY table_name, column_id
                    """
                )
                for row in connection.execute(sql):
                    by_table.setdefault(row[0], []).append(row[1])
            else:
                raise ValueError(f"Unsupported source_type: {source_type}")
    except SQLAlchemyError:
        raise

    tables = [{"name": name, "columns": cols} for name, cols in sorted(by_table.items())]
    max_tables = 400
    if len(tables) > max_tables:
        tables = tables[:max_tables]
    return tables


def parse_table_parts(
    display_name: str, source_type: SourceType
) -> tuple[str | None, str]:
    """Split schema-qualified name for SQLAlchemy Table(schema=..., name=...)."""
    if source_type == "postgresql" and "." in display_name:
        schema, tname = display_name.split(".", 1)
        return schema, tname
    return None, display_name


def pick_table_for_question(question: str, tables: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not tables:
        return None
    q = question.lower()
    q_tokens = set(re.findall(r"[a-z0-9_]+", q))
    best: dict[str, Any] | None = None
    best_score = 0
    for t in tables:
        name = t["name"]
        base = name.split(".")[-1].lower()
        score = 0
        if base and base in q:
            score += 3
        if name.lower() in q:
            score += 5
        for col in t.get("columns") or []:
            c = col.lower()
            if c and c in q_tokens:
                score += 1
        if score > best_score:
            best_score = score
            best = t
    if best_score > 0:
        return best
    return tables[0]


_COUNT_RE = re.compile(
    r"\b(how many|number of|count of|count the|count all)\b", re.IGNORECASE
)
_SUM_RE = re.compile(r"\b(sum|total|add up|aggregate)\b", re.IGNORECASE)


def _question_tokens(question: str) -> set[str]:
    return set(re.findall(r"[a-z0-9_]+", question.lower()))


def _infer_sum_column(question: str, columns: list[str]) -> str | None:
    tokens = _question_tokens(question)
    priority = (
        "revenue",
        "amount",
        "total",
        "price",
        "qty",
        "quantity",
        "sales",
        "value",
        "payment",
        "cost",
    )
    for p in priority:
        if p not in tokens:
            continue
        for c in columns:
            cl = c.lower()
            if cl == p or p in cl:
                return c
    for c in columns:
        if len(c) > 2 and c.lower() in tokens:
            return c
    return None


def _score_columns_for_question(question: str, columns: list[str]) -> list[tuple[str, int]]:
    q = question.lower()
    tokens = _question_tokens(question)
    scored: list[tuple[str, int]] = []
    for c in columns:
        cl = c.lower()
        score = 0
        if cl in q:
            score += 5
        if cl in tokens:
            score += 4
        for t in tokens:
            if len(t) >= 3 and t in cl:
                score += 2
        for part in cl.split("_"):
            if len(part) >= 3 and part in tokens:
                score += 2
        scored.append((c, score))
    scored.sort(key=lambda x: -x[1])
    return scored


def _infer_order_column(reflected: Table) -> Any | None:
    date_markers = ("date", "time", "at", "when", "created", "updated", "timestamp")
    for key in reflected.c.keys():
        kl = key.lower()
        if any(m in kl for m in date_markers):
            return reflected.c[key]
    return None


def _wants_recent_order(question: str) -> bool:
    return bool(
        re.search(r"\b(latest|recent|last|newest|desc)\b", question.lower())
    )


def preview_for_question(
    engine: Engine,
    source_type: SourceType,
    table: dict[str, Any],
    question: str,
    row_limit: int = 50,
) -> tuple[str, list[str], list[list[Any]], dict[str, Any]]:
    """Read-only preview shaped by lightweight heuristics (not full NL2SQL)."""
    schema, tname = parse_table_parts(table["name"], source_type)
    md = MetaData()
    try:
        reflected = Table(tname, md, schema=schema, autoload_with=engine)
    except SQLAlchemyError as exc:
        raise ValueError(f"Could not read table {table['name']}: {exc}") from exc

    q = question.lower()
    meta_base: dict[str, Any] = {"query_kind": "scan", "used_fallback": False}

    if _COUNT_RE.search(q):
        stmt = select(func.count()).select_from(reflected)
        with engine.connect() as conn:
            total = conn.execute(stmt).scalar_one()
        rows = [[_serialize_cell(total)]]
        cols = ["row_count"]
        compiled = str(stmt.compile(engine, compile_kwargs={"literal_binds": False}))
        return compiled, cols, rows, {**meta_base, "query_kind": "count", "selected_columns": None}

    if _SUM_RE.search(q):
        scol = _infer_sum_column(question, list(reflected.c.keys()))
        if scol is not None:
            col = reflected.c[scol]
            stmt = select(func.sum(col))
            with engine.connect() as conn:
                raw_total = conn.execute(stmt).scalar_one()
            rows = [[_serialize_cell(raw_total)]]
            cols = [f"sum_{scol}"]
            compiled = str(stmt.compile(engine, compile_kwargs={"literal_binds": False}))
            return compiled, cols, rows, {
                **meta_base,
                "query_kind": "sum",
                "selected_columns": [scol],
            }

    scored = _score_columns_for_question(question, list(reflected.c.keys()))
    picked = [c for c, s in scored if s > 0][:16]
    if picked:
        stmt = select(*[reflected.c[c] for c in picked])
        selected = picked
    else:
        fallback_cols = list(reflected.c.keys())[:24]
        stmt = select(*[reflected.c[c] for c in fallback_cols])
        selected = None

    oc = _infer_order_column(reflected)
    if oc is not None and _wants_recent_order(question):
        stmt = stmt.order_by(desc(oc))
    stmt = stmt.limit(row_limit)

    with engine.connect() as conn:
        result = conn.execute(stmt)
        columns = list(result.keys())
        raw_rows = result.fetchall()
    rows = [[_serialize_cell(cell) for cell in row] for row in raw_rows]
    compiled = str(stmt.compile(engine, compile_kwargs={"literal_binds": False}))
    return compiled, columns, rows, {**meta_base, "selected_columns": selected}


def preview_select(
    engine: Engine, source_type: SourceType, table: dict[str, Any], row_limit: int = 50
) -> tuple[str, list[str], list[list[Any]]]:
    schema, tname = parse_table_parts(table["name"], source_type)
    md = MetaData()
    try:
        reflected = Table(tname, md, schema=schema, autoload_with=engine)
    except SQLAlchemyError as exc:
        raise ValueError(f"Could not read table {table['name']}: {exc}") from exc

    stmt = select(reflected).limit(row_limit)
    with engine.connect() as conn:
        result = conn.execute(stmt)
        columns = list(result.keys())
        raw_rows = result.fetchall()
    rows = [[_serialize_cell(cell) for cell in row] for row in raw_rows]
    compiled = str(stmt.compile(engine, compile_kwargs={"literal_binds": False}))
    return compiled, columns, rows

