"""Multi-vendor LLM HTTP clients (OpenAI-compatible, Anthropic, Google Gemini)."""

from __future__ import annotations

import json
import os
from typing import Any
from urllib.parse import quote

import httpx

# Prefer explicit SMART_BI_* then standard vendor env names (never read .env files from disk).
_API_ENV: dict[str, tuple[str, ...]] = {
    "openai": ("SMART_BI_OPENAI_API_KEY", "OPENAI_API_KEY"),
    "anthropic": ("SMART_BI_ANTHROPIC_API_KEY", "ANTHROPIC_API_KEY"),
    "google": ("SMART_BI_GOOGLE_API_KEY", "GOOGLE_API_KEY", "GEMINI_API_KEY"),
}


def api_key_for(provider: str) -> str | None:
    keys = _API_ENV.get(provider)
    if not keys:
        return None
    for name in keys:
        v = os.environ.get(name, "").strip()
        if v:
            return v
    return None


def provider_configured(provider: str) -> bool:
    return api_key_for(provider) is not None


def openai_base_url() -> str:
    return (
        os.environ.get("SMART_BI_OPENAI_BASE_URL")
        or os.environ.get("OPENAI_API_BASE")
        or "https://api.openai.com/v1"
    ).rstrip("/")


def _clip_timeout(timeout_sec: int | float | None) -> float:
    if timeout_sec is None:
        return 60.0
    try:
        t = float(timeout_sec)
    except (TypeError, ValueError):
        return 60.0
    return max(5.0, min(t, 180.0))


def _httpx_timeout(read_sec: float) -> httpx.Timeout:
    return httpx.Timeout(15.0, read=read_sec, write=15.0, pool=15.0)


def complete_chat(
    *,
    provider: str,
    model: str,
    system: str,
    user: str,
    temperature: float,
    max_tokens: int,
    timeout_sec: int | float | None = None,
) -> tuple[str, str | None]:
    """
    Returns (assistant_text, error_message).
    error_message is None on success.
    """
    read_t = _clip_timeout(timeout_sec)
    key = api_key_for(provider)
    if not key:
        return "", f"No API key configured for provider '{provider}'."

    if provider == "openai":
        return _openai_chat(
            key=key,
            model=model,
            system=system,
            user=user,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=read_t,
        )
    if provider == "anthropic":
        return _anthropic_messages(
            key=key,
            model=model,
            system=system,
            user=user,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=read_t,
        )
    if provider == "google":
        return _google_gemini(
            key=key,
            model=model,
            system=system,
            user=user,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=read_t,
        )
    return "", f"Unsupported provider '{provider}'."


def _extract_openai_text(data: dict[str, Any]) -> str:
    try:
        choices = data["choices"]
        if not choices:
            return ""
        msg = choices[0].get("message") or {}
        return (msg.get("content") or "").strip()
    except (KeyError, TypeError, IndexError):
        return ""


def _openai_chat(
    *,
    key: str,
    model: str,
    system: str,
    user: str,
    temperature: float,
    max_tokens: int,
    timeout: float,
) -> tuple[str, str | None]:
    url = f"{openai_base_url()}/chat/completions"
    payload = {
        "model": model,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    try:
        with httpx.Client(timeout=_httpx_timeout(timeout)) as client:
            r = client.post(url, headers=headers, json=payload)
            if r.status_code >= 400:
                return "", _safe_http_error("OpenAI", r)
            data = r.json()
    except httpx.HTTPError as exc:
        return "", f"OpenAI request failed: {exc}"
    text = _extract_openai_text(data)
    return text, None if text else "OpenAI returned an empty response."


def _anthropic_messages(
    *,
    key: str,
    model: str,
    system: str,
    user: str,
    temperature: float,
    max_tokens: int,
    timeout: float,
) -> tuple[str, str | None]:
    url = "https://api.anthropic.com/v1/messages"
    payload = {
        "model": model,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "system": system,
        "messages": [{"role": "user", "content": user}],
    }
    headers = {
        "x-api-key": key,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }
    try:
        with httpx.Client(timeout=_httpx_timeout(timeout)) as client:
            r = client.post(url, headers=headers, json=payload)
            if r.status_code >= 400:
                return "", _safe_http_error("Anthropic", r)
            data = r.json()
    except httpx.HTTPError as exc:
        return "", f"Anthropic request failed: {exc}"
    blocks = data.get("content") or []
    parts: list[str] = []
    for b in blocks:
        if isinstance(b, dict) and b.get("type") == "text":
            parts.append(str(b.get("text") or ""))
    text = "\n".join(parts).strip()
    return text, None if text else "Anthropic returned an empty response."


def _google_gemini(
    *,
    key: str,
    model: str,
    system: str,
    user: str,
    temperature: float,
    max_tokens: int,
    timeout: float,
) -> tuple[str, str | None]:
    safe_key = quote(key, safe="")
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={safe_key}"
    )
    payload = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": user}]}],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_tokens,
        },
    }
    try:
        with httpx.Client(timeout=_httpx_timeout(timeout)) as client:
            r = client.post(url, json=payload)
            if r.status_code >= 400:
                return "", _safe_http_error("Google", r)
            data = r.json()
    except httpx.HTTPError as exc:
        return "", f"Google Gemini request failed: {exc}"
    try:
        parts = data["candidates"][0]["content"]["parts"]
        text = "".join(p.get("text", "") for p in parts if isinstance(p, dict)).strip()
    except (KeyError, TypeError, IndexError):
        text = ""
    return text, None if text else "Gemini returned an empty response."


def _safe_http_error(vendor: str, response: httpx.Response) -> str:
    try:
        body = response.json()
        err = body.get("error")
        if isinstance(err, dict):
            msg = err.get("message") or err.get("type") or str(err)
        elif isinstance(err, str):
            msg = err
        else:
            msg = response.text[:500]
    except json.JSONDecodeError:
        msg = response.text[:500]
    return f"{vendor} HTTP {response.status_code}: {msg}"
