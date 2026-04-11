from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field, model_validator

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


@router.get("")
def list_connections() -> list[dict]:
    return _connections


@router.post("")
def create_connection(payload: ConnectionPayload) -> dict:
    connection = payload.model_dump()
    connection["id"] = len(_connections) + 1
    connection["password"] = "***"
    _connections.append(connection)
    return connection


@router.post("/{connection_id}/test")
def test_connection(connection_id: int) -> dict[str, str | int]:
    return {"status": "success", "connection_id": connection_id}


@router.post("/{connection_id}/introspect")
def introspect(connection_id: int) -> dict:
    tables = [
        {"name": "sales_orders", "columns": ["order_id", "order_date", "amount"]},
        {"name": "customers", "columns": ["customer_id", "customer_name", "segment"]},
    ]
    return {"connection_id": connection_id, "tables": tables}
