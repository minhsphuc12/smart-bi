from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/admin/ai-routing", tags=["admin-ai-routing"])

profiles: dict[str, dict] = {
    "sql_gen": {"provider": "providerA", "model": "sql-model", "temperature": 0.0, "max_tokens": 1200},
    "answer_gen": {"provider": "providerB", "model": "answer-model", "temperature": 0.2, "max_tokens": 800},
    "dashboard_gen": {"provider": "providerB", "model": "dashboard-model", "temperature": 0.1, "max_tokens": 1500},
    "extract_classify": {"provider": "providerA", "model": "extract-model", "temperature": 0.0, "max_tokens": 400},
}


class RoutingProfilePayload(BaseModel):
    task: str
    provider: str
    model: str
    temperature: float = 0.0
    max_tokens: int = 1000
    timeout: int = 30
    cost_limit: float = 1.0


@router.get("/profiles")
def get_profiles() -> dict[str, dict]:
    return profiles


@router.post("/profiles")
def upsert_profile(payload: RoutingProfilePayload) -> dict:
    profiles[payload.task] = payload.model_dump(exclude={"task"})
    return {"task": payload.task, **profiles[payload.task]}


@router.put("/profiles")
def update_profile(payload: RoutingProfilePayload) -> dict:
    profiles[payload.task] = payload.model_dump(exclude={"task"})
    return {"task": payload.task, **profiles[payload.task]}


@router.post("/validate")
def validate_profile(payload: RoutingProfilePayload) -> dict[str, str]:
    return {"status": "valid", "task": payload.task}
