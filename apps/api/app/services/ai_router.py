from app.routers.admin_ai_routing import get_profile_for_task


def route_task(task: str) -> dict:
    return get_profile_for_task(task)


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
