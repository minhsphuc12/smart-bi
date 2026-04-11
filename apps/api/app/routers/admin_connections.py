from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/admin/connections", tags=["admin-connections"])

_connections: list[dict] = []


class ConnectionPayload(BaseModel):
    name: str
    host: str
    port: int = 1521
    service_name: str
    username: str
    password: str


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
