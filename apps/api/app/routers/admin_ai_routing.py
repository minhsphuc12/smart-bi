from fastapi import APIRouter
from pydantic import BaseModel, model_validator

from app.ai_routing_catalog import catalog_response, is_allowed_model, is_allowed_provider

router = APIRouter(prefix="/admin/ai-routing", tags=["admin-ai-routing"])

profiles: dict[str, dict] = {
    "sql_gen": {"provider": "openai", "model": "gpt-4o-mini", "temperature": 0.0, "max_tokens": 1200},
    "answer_gen": {"provider": "anthropic", "model": "claude-sonnet-4-20250514", "temperature": 0.2, "max_tokens": 800},
    "dashboard_gen": {"provider": "google", "model": "gemini-2.5-flash", "temperature": 0.1, "max_tokens": 1500},
    "extract_classify": {"provider": "openai", "model": "gpt-4o-mini", "temperature": 0.0, "max_tokens": 400},
}


class RoutingProfilePayload(BaseModel):
    task: str
    provider: str
    model: str
    temperature: float = 0.0
    max_tokens: int = 1000
    timeout: int = 30
    cost_limit: float = 1.0

    @model_validator(mode="after")
    def provider_model_must_be_allowlisted(self) -> "RoutingProfilePayload":
        if not is_allowed_provider(self.provider):
            raise ValueError(f"Unknown provider '{self.provider}'. Use a supported provider id.")
        if not is_allowed_model(self.provider, self.model):
            raise ValueError(
                f"Model '{self.model}' is not allowed for provider '{self.provider}'."
            )
        return self


@router.get("/catalog")
def get_catalog() -> dict:
    return catalog_response()


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
