"""Allowlisted AI providers and models for admin routing profiles (MVP)."""

from typing import Final

# IDs must match vendor API model strings; extend as needed.
MODELS_BY_PROVIDER: Final[dict[str, tuple[str, ...]]] = {
    "openai": (
        "gpt-4o",
        "gpt-4o-mini",
        "o4-mini",
        "o3-mini",
    ),
    "anthropic": (
        "claude-sonnet-4-20250514",
        "claude-opus-4-20250514",
        "claude-3-5-haiku-20241022",
    ),
    "google": (
        "gemini-2.5-flash",
        "gemini-2.5-pro",
        "gemini-2.0-flash",
    ),
}

PROVIDER_IDS: Final[tuple[str, ...]] = tuple(MODELS_BY_PROVIDER.keys())

PROVIDER_LABELS: Final[dict[str, str]] = {
    "openai": "OpenAI",
    "anthropic": "Anthropic",
    "google": "Google",
}


def is_allowed_provider(provider: str) -> bool:
    return provider in MODELS_BY_PROVIDER


def is_allowed_model(provider: str, model: str) -> bool:
    allowed = MODELS_BY_PROVIDER.get(provider)
    return allowed is not None and model in allowed


def catalog_response() -> dict:
    return {
        "providers": [
            {"id": pid, "label": PROVIDER_LABELS.get(pid, pid)} for pid in PROVIDER_IDS
        ],
        "models_by_provider": {pid: list(models) for pid, models in MODELS_BY_PROVIDER.items()},
    }
