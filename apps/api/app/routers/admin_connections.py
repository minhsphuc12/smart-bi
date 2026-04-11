from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.exc import SQLAlchemyError

from app.services import db_engine

router = APIRouter(prefix="/admin/connections", tags=["admin-connections"])

_connections: list[dict] = []

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


def _public_connection(row: dict) -> dict:
    out = {k: v for k, v in row.items() if k != "password"}
    out["password"] = "***" if row.get("password") else ""
    return out


def _get_connection(connection_id: int) -> dict:
    for c in _connections:
        if c.get("id") == connection_id:
            return c
    raise HTTPException(status_code=404, detail="Connection not found")


def get_connection_record(connection_id: int) -> dict:
    """Return stored connection including password (server-side only)."""
    return _get_connection(connection_id)


@router.get("")
def list_connections() -> list[dict]:
    return [_public_connection(c) for c in _connections]


@router.post("")
def create_connection(payload: ConnectionPayload) -> dict:
    connection = payload.model_dump()
    connection["id"] = len(_connections) + 1
    _connections.append(connection)
    db_engine.clear_introspection_cache(connection["id"])
    return _public_connection(connection)


@router.post("/{connection_id}/test")
def test_connection(connection_id: int) -> dict[str, str | int]:
    conn = _get_connection(connection_id)
    try:
        engine = db_engine.make_engine(conn)
        try:
            db_engine.ping_engine(engine, conn["source_type"])
        finally:
            engine.dispose()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=400, detail=f"Connection failed: {exc}") from exc
    return {"status": "success", "connection_id": connection_id}


@router.post("/{connection_id}/introspect")
def introspect(connection_id: int) -> dict:
    conn = _get_connection(connection_id)
    try:
        engine = db_engine.make_engine(conn)
        try:
            tables = db_engine.introspect_schema(engine, conn["source_type"])
        finally:
            engine.dispose()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=400, detail=f"Introspection failed: {exc}") from exc
    db_engine.set_introspection_cache(connection_id, tables)
    return {"connection_id": connection_id, "tables": tables}
