from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/admin/semantic", tags=["admin-semantic"])

tables: list[dict] = []
relationships: list[dict] = []
dictionary: list[dict] = []
metrics: list[dict] = []


class GenericItem(BaseModel):
    name: str
    description: str = ""


@router.get("/tables")
def get_tables() -> list[dict]:
    return tables


@router.post("/tables")
def create_table(item: GenericItem) -> dict:
    row = {"id": len(tables) + 1, **item.model_dump()}
    tables.append(row)
    return row


@router.put("/tables/{item_id}")
def update_table(item_id: int, item: GenericItem) -> dict:
    tables[item_id - 1].update(item.model_dump())
    return tables[item_id - 1]


@router.get("/relationships")
def get_relationships() -> list[dict]:
    return relationships


@router.post("/relationships")
def create_relationship(item: GenericItem) -> dict:
    row = {"id": len(relationships) + 1, **item.model_dump()}
    relationships.append(row)
    return row


@router.put("/relationships/{item_id}")
def update_relationship(item_id: int, item: GenericItem) -> dict:
    relationships[item_id - 1].update(item.model_dump())
    return relationships[item_id - 1]


@router.get("/dictionary")
def get_dictionary() -> list[dict]:
    return dictionary


@router.post("/dictionary")
def create_dictionary(item: GenericItem) -> dict:
    row = {"id": len(dictionary) + 1, **item.model_dump()}
    dictionary.append(row)
    return row


@router.put("/dictionary/{item_id}")
def update_dictionary(item_id: int, item: GenericItem) -> dict:
    dictionary[item_id - 1].update(item.model_dump())
    return dictionary[item_id - 1]


@router.get("/metrics")
def get_metrics() -> list[dict]:
    return metrics


@router.post("/metrics")
def create_metric(item: GenericItem) -> dict:
    row = {"id": len(metrics) + 1, **item.model_dump()}
    metrics.append(row)
    return row


@router.put("/metrics/{item_id}")
def update_metric(item_id: int, item: GenericItem) -> dict:
    metrics[item_id - 1].update(item.model_dump())
    return metrics[item_id - 1]
