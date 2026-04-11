import os
import tempfile

import pytest


def pytest_configure(config) -> None:
    """Point connection storage at a temp file before test modules import the FastAPI app."""
    fd, path = tempfile.mkstemp(prefix="smartbi-connections-", suffix=".json")
    os.close(fd)
    os.environ["SMART_BI_CONNECTIONS_FILE"] = path


@pytest.fixture(autouse=True)
def _reset_connection_store() -> None:
    """Keep the in-memory list aligned with an empty file between tests."""
    from app.routers import admin_connections as ac
    from app.services import connection_store

    connection_store.save_connections([])
    with ac._conn_lock:
        ac._connections.clear()
        ac._connections.extend(connection_store.load_connections())
