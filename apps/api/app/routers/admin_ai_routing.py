from copy import deepcopy
from threading import Lock

from fastapi import APIRouter
from pydantic import BaseModel, model_validator

from app.ai_routing_catalog import catalog_response, is_allowed_model, is_allowed_provider
from app.services import ai_routing_store

router = APIRouter(prefix="/admin/ai-routing", tags=["admin-ai-routing"])

_ai_lock = Lock()
_profiles: dict[str, dict] = ai_routing_store.load_profiles()


def get_profile_for_task(task: str) -> dict:
    default_profile = {"provider": "openai", "model": "gpt-4o-mini", "temperature": 0.1, "max_tokens": 1000}
    with _ai_lock:
        profile = _profiles.get(task)
        if profile is None:
            return dict(default_profile)
        return dict(profile)


class RoutingProfilePayload(BaseModel):
    task: str
    provider: str
    model: str
    temperature: float = 0.0
    max_tokens: int = 1000
    timeout: int = 30
    cost_limit: float = 1.0

    @model_validator(mode="after")
    def task_provider_model_must_be_valid(self) -> "RoutingProfilePayload":
        if self.task not in ai_routing_store.DEFAULT_PROFILES:
            raise ValueError(f"Unknown task '{self.task}'.")
        if not is_allowed_provider(self.provider):
            raise ValueError(f"Unknown provider '{self.provider}'. Use a supported provider id.")
        if not is_allowed_model(self.provider, self.model):
            raise ValueError(f"Model '{self.model}' is not allowed for provider '{self.provider}'.")
        return self


@router.get("/catalog")
def get_catalog() -> dict:
    return catalog_response()


@router.get("/profiles")
def get_profiles() -> dict[str, dict]:
    with _ai_lock:
        return {k: deepcopy(v) for k, v in _profiles.items()}


@router.post("/profiles")
def upsert_profile(payload: RoutingProfilePayload) -> dict:
    with _ai_lock:
        _profiles[payload.task] = payload.model_dump(exclude={"task"})
        ai_routing_store.save_profiles(_profiles)
        return {"task": payload.task, **deepcopy(_profiles[payload.task])}


@router.put("/profiles")
def update_profile(payload: RoutingProfilePayload) -> dict:
    with _ai_lock:
        _profiles[payload.task] = payload.model_dump(exclude={"task"})
        ai_routing_store.save_profiles(_profiles)
        return {"task": payload.task, **deepcopy(_profiles[payload.task])}


@router.post("/validate")
def validate_profile(payload: RoutingProfilePayload) -> dict[str, str]:
    return {"status": "valid", "task": payload.task}
