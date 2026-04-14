from threading import Lock

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.services import semantic_store

router = APIRouter(prefix="/admin/semantic", tags=["admin-semantic"])

_sem_lock = Lock()
_bundle = semantic_store.load_semantic()
tables: list[dict] = _bundle["tables"]
relationships: list[dict] = _bundle["relationships"]
dictionary: list[dict] = _bundle["dictionary"]
metrics: list[dict] = _bundle["metrics"]


def _persist() -> None:
    semantic_store.save_semantic(
        {
            "tables": tables,
            "relationships": relationships,
            "dictionary": dictionary,
            "metrics": metrics,
        }
    )


class GenericItem(BaseModel):
    name: str
    description: str = ""


@router.get("/tables")
def get_tables() -> list[dict]:
    with _sem_lock:
        return [*tables]


@router.post("/tables")
def create_table(item: GenericItem) -> dict:
    with _sem_lock:
        row = {"id": len(tables) + 1, **item.model_dump()}
        tables.append(row)
        _persist()
        return row


@router.put("/tables/{item_id}")
def update_table(item_id: int, item: GenericItem) -> dict:
    with _sem_lock:
        tables[item_id - 1].update(item.model_dump())
        _persist()
        return tables[item_id - 1]


@router.get("/relationships")
def get_relationships() -> list[dict]:
    with _sem_lock:
        return [*relationships]


@router.post("/relationships")
def create_relationship(item: GenericItem) -> dict:
    with _sem_lock:
        row = {"id": len(relationships) + 1, **item.model_dump()}
        relationships.append(row)
        _persist()
        return row


@router.put("/relationships/{item_id}")
def update_relationship(item_id: int, item: GenericItem) -> dict:
    with _sem_lock:
        relationships[item_id - 1].update(item.model_dump())
        _persist()
        return relationships[item_id - 1]


@router.get("/dictionary")
def get_dictionary() -> list[dict]:
    with _sem_lock:
        return [*dictionary]


@router.post("/dictionary")
def create_dictionary(item: GenericItem) -> dict:
    with _sem_lock:
        row = {"id": len(dictionary) + 1, **item.model_dump()}
        dictionary.append(row)
        _persist()
        return row


@router.put("/dictionary/{item_id}")
def update_dictionary(item_id: int, item: GenericItem) -> dict:
    with _sem_lock:
        dictionary[item_id - 1].update(item.model_dump())
        _persist()
        return dictionary[item_id - 1]


@router.get("/metrics")
def get_metrics() -> list[dict]:
    with _sem_lock:
        return [*metrics]


@router.post("/metrics")
def create_metric(item: GenericItem) -> dict:
    with _sem_lock:
        row = {"id": len(metrics) + 1, **item.model_dump()}
        metrics.append(row)
        _persist()
        return row


@router.put("/metrics/{item_id}")
def update_metric(item_id: int, item: GenericItem) -> dict:
    with _sem_lock:
        metrics[item_id - 1].update(item.model_dump())
        _persist()
        return metrics[item_id - 1]


@router.get("/mart/files")
def list_mart_yaml_files() -> dict:
    """List ``*.yml`` / ``*.yaml`` under the configured mart directory (read-only)."""
    return semantic_store.list_mart_yaml_entries()


@router.get("/mart/content")
def read_mart_yaml_file(
    relative_path: str = Query(
        ...,
        min_length=1,
        alias="path",
        description="Path relative to mart root, POSIX-style (also accepted as query name `path`)",
    ),
) -> dict:
    """Return raw file contents for one mart YAML file (read-only)."""
    try:
        content = semantic_store.read_mart_yaml_relative(relative_path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Mart directory or file not found.") from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    normalized = relative_path.strip().replace("\\", "/")
    return {"path": normalized, "content": content}
