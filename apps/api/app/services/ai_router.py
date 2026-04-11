from app.routers.admin_ai_routing import profiles


def route_task(task: str) -> dict:
    default_profile = {"provider": "openai", "model": "gpt-4o-mini", "temperature": 0.1, "max_tokens": 1000}
    return profiles.get(task, default_profile)


def run_task(task: str, prompt: str) -> dict:
    profile = route_task(task)
    # Placeholder for real provider SDK dispatching.
    return {
        "task": task,
        "provider": profile["provider"],
        "model": profile["model"],
        "output": f"Simulated output for task={task}",
        "prompt_chars": len(prompt),
    }
