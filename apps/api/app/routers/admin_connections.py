from threading import Lock
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.exc import SQLAlchemyError

from app.services import connection_store, db_engine
from app.services.db_client_errors import humanize_sqlalchemy_error

router = APIRouter(prefix="/admin/connections", tags=["admin-connections"])

_conn_lock = Lock()
_connections: list[dict] = connection_store.load_connections()

SourceType = Literal["oracle", "postgresql", "mysql"]


class ConnectionPayload(BaseModel):
    name: str
    source_type: SourceType = "oracle"
    host: str
    port: int = 1521
    service_name: str | None = Field(default=None, description="Oracle service or PDB name")
    database: str | None = Field(default=None, description="PostgreSQL or MySQL database name")
    username: str
    password: str

    @model_validator(mode="after")
    def require_target_for_engine(self) -> "ConnectionPayload":
        if self.source_type == "oracle":
            if not (self.service_name and self.service_name.strip()):
                raise ValueError("service_name is required for Oracle connections")
        elif not (self.database and self.database.strip()):
            raise ValueError("database is required for PostgreSQL and MySQL connections")
        return self


class ConnectionUpdatePayload(BaseModel):
    name: str
    source_type: SourceType = "oracle"
    host: str
    port: int = 1521
    service_name: str | None = Field(default=None, description="Oracle service or PDB name")
    database: str | None = Field(default=None, description="PostgreSQL or MySQL database name")
    username: str
    password: str | None = Field(
        default=None,
        description="When null or empty, the existing password is kept.",
    )

    @model_validator(mode="after")
    def require_target_for_engine(self) -> "ConnectionUpdatePayload":
        if self.source_type == "oracle":
            if not (self.service_name and self.service_name.strip()):
                raise ValueError("service_name is required for Oracle connections")
        elif not (self.database and self.database.strip()):
            raise ValueError("database is required for PostgreSQL and MySQL connections")
        return self


def _public_connection(row: dict) -> dict:
    out = {k: v for k, v in row.items() if k != "password"}
    out["password"] = "***" if row.get("password") else ""
    return out


def _get_connection_row(connection_id: int) -> dict:
    for c in _connections:
        if c.get("id") == connection_id:
            return c
    raise HTTPException(status_code=404, detail="Connection not found")


def _next_connection_id() -> int:
    return max((c["id"] for c in _connections), default=0) + 1


def get_connection_record(connection_id: int) -> dict:
    """Return stored connection including password (server-side only)."""
    with _conn_lock:
        row = _get_connection_row(connection_id)
        return dict(row)


@router.get("")
def list_connections() -> list[dict]:
    with _conn_lock:
        return [_public_connection(c) for c in _connections]


@router.post("")
def create_connection(payload: ConnectionPayload) -> dict:
    with _conn_lock:
        connection = payload.model_dump()
        connection["id"] = _next_connection_id()
        _connections.append(connection)
        connection_store.save_connections(_connections)
        db_engine.clear_introspection_cache(connection["id"])
        return _public_connection(connection)


@router.put("/{connection_id}")
def update_connection(connection_id: int, payload: ConnectionUpdatePayload) -> dict:
    with _conn_lock:
        existing = _get_connection_row(connection_id)
        data = payload.model_dump()
        pwd = data.pop("password", None)
        if pwd is None or (isinstance(pwd, str) and not pwd.strip()):
            data["password"] = existing.get("password", "")
        else:
            data["password"] = pwd
        data["id"] = connection_id
        idx = next(i for i, c in enumerate(_connections) if c.get("id") == connection_id)
        _connections[idx] = data
        connection_store.save_connections(_connections)
        db_engine.clear_introspection_cache(connection_id)
        return _public_connection(data)


@router.post("/{connection_id}/test")
def test_connection(connection_id: int) -> dict[str, str | int]:
    with _conn_lock:
        conn = dict(_get_connection_row(connection_id))
    try:
        engine = db_engine.make_engine(conn)
        try:
            db_engine.ping_engine(engine, conn["source_type"])
        finally:
            engine.dispose()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=400,
            detail=humanize_sqlalchemy_error(exc, prefix="Connection failed"),
        ) from exc
    return {"status": "success", "connection_id": connection_id}


@router.post("/{connection_id}/introspect")
def introspect(connection_id: int) -> dict:
    with _conn_lock:
        conn = dict(_get_connection_row(connection_id))
    try:
        engine = db_engine.make_engine(conn)
        try:
            tables = db_engine.introspect_schema(engine, conn["source_type"])
        finally:
            engine.dispose()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=400,
            detail=humanize_sqlalchemy_error(exc, prefix="Introspection failed"),
        ) from exc
    db_engine.set_introspection_cache(connection_id, tables)
    return {"connection_id": connection_id, "tables": tables}
