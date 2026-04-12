from app.routers.admin_ai_routing import get_profile_for_task
from app.services import llm_client


def route_task(task: str) -> dict:
    return get_profile_for_task(task)


def _default_system_prompt(task: str) -> str:
    if task == "sql_gen":
        return "You are a helpful analytics SQL assistant. Follow user instructions precisely."
    if task == "answer_gen":
        return "You are a helpful business analyst. Answer clearly and honestly."
    if task == "dashboard_gen":
        return "You are a BI dashboard assistant. Respond with concise structured guidance."
    if task == "extract_classify":
        return "You extract and classify entities from user text. Respond concisely."
    return "You are a helpful assistant."


def run_task(
    task: str,
    user_prompt: str,
    *,
    system_prompt: str | None = None,
) -> dict:
    profile = route_task(task)
    base: dict = {
        "task": task,
        "provider": profile["provider"],
        "model": profile["model"],
        "prompt_chars": len(user_prompt),
    }
    provider = str(profile.get("provider") or "")
    if not llm_client.provider_configured(provider):
        return {
            **base,
            "output": f"Simulated output for task={task}",
            "live": False,
            "error": None,
        }

    system = system_prompt if system_prompt is not None else _default_system_prompt(task)
    text, err = llm_client.complete_chat(
        provider=provider,
        model=str(profile.get("model") or ""),
        system=system,
        user=user_prompt,
        temperature=float(profile.get("temperature", 0.2)),
        max_tokens=int(profile.get("max_tokens", 1024)),
        timeout_sec=profile.get("timeout"),
    )
    if err:
        return {**base, "output": "", "live": False, "error": err}
    return {**base, "output": text, "live": True, "error": None}
