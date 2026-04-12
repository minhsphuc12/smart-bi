import os
import tempfile
from copy import deepcopy

import pytest


def pytest_configure(config) -> None:
    """Point file-backed admin storage at temp files before test modules import the FastAPI app."""
    fd, path = tempfile.mkstemp(prefix="smartbi-connections-", suffix=".json")
    os.close(fd)
    os.environ["SMART_BI_CONNECTIONS_FILE"] = path

    fd2, path2 = tempfile.mkstemp(prefix="smartbi-semantic-", suffix=".json")
    os.close(fd2)
    os.environ["SMART_BI_SEMANTIC_FILE"] = path2

    fd3, path3 = tempfile.mkstemp(prefix="smartbi-ai-routing-", suffix=".json")
    os.close(fd3)
    os.environ["SMART_BI_AI_ROUTING_FILE"] = path3


@pytest.fixture(autouse=True)
def _reset_connection_store() -> None:
    """Keep in-memory admin state aligned with clean files between tests."""
    from app.routers import admin_ai_routing as air
    from app.routers import admin_connections as ac
    from app.routers import admin_semantic as sem
    from app.services import ai_routing_store
    from app.services import connection_store
    from app.services import semantic_store

    connection_store.save_connections([])
    with ac._conn_lock:
        ac._connections.clear()
        ac._connections.extend(connection_store.load_connections())

    empty_semantic = {"tables": [], "relationships": [], "dictionary": [], "metrics": []}
    semantic_store.save_semantic(empty_semantic)
    loaded_semantic = semantic_store.load_semantic()
    with sem._sem_lock:
        for key in ("tables", "relationships", "dictionary", "metrics"):
            target = getattr(sem, key)
            target.clear()
            target.extend(loaded_semantic[key])

    ai_routing_store.save_profiles(deepcopy(ai_routing_store.DEFAULT_PROFILES))
    loaded_ai = ai_routing_store.load_profiles()
    with air._ai_lock:
        air._profiles.clear()
        air._profiles.update(loaded_ai)
