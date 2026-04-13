from threading import Lock

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services import dashboard_store
from app.services.dashboard_ai import generate_spec
from app.services.dashboard_queries import run_all_widget_queries

router = APIRouter(tags=["dashboards"])

_dash_lock = Lock()
dashboards: list[dict] = []
dashboard_versions: dict[int, list[dict]] = {}

# Populate from disk at import (tests set SMART_BI_DASHBOARDS_FILE in pytest_configure first).
_initial_boards, _initial_versions = dashboard_store.load_state()
dashboards.extend(_initial_boards)
dashboard_versions.update(_initial_versions)


class DashboardCreatePayload(BaseModel):
    prompt: str
    title: str
    connection_id: int | None = Field(
        default=None,
        description="Optional datasource; when set, the API introspects if needed so the model emits executable SQL.",
    )


class DashboardEditPayload(BaseModel):
    prompt: str
    connection_id: int | None = Field(default=None, description="Optional schema context for the LLM.")


class RunQueriesPayload(BaseModel):
    connection_id: int | None = Field(
        default=None,
        description="Datasource to run widget SQL against; falls back to dashboard.connection_id when omitted.",
    )


def _meta_from_ai(ai: dict) -> dict:
    return {
        "dashboard_gen": {
            "live": bool(ai.get("live")),
            "error": ai.get("error"),
            "provider": ai.get("provider"),
            "model": ai.get("model"),
        }
    }


def _next_id_unlocked() -> int:
    if not dashboards:
        return 1
    return max(int(d["id"]) for d in dashboards) + 1


def _persist_unlocked() -> None:
    dashboard_store.save_state(dashboards, dashboard_versions)


@router.post("/dashboards")
def create_dashboard(payload: DashboardCreatePayload) -> dict:
    try:
        result = generate_spec(
            user_prompt=payload.prompt,
            connection_id=payload.connection_id,
            existing_spec=None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    spec = result["spec"]
    ai = result["ai"]
    meta = _meta_from_ai(ai)

    with _dash_lock:
        dashboard = {
            "id": _next_id_unlocked(),
            "title": payload.title,
            "spec": spec,
            "created_by_model": str(ai.get("model") or "n/a"),
            "meta": meta,
            "connection_id": payload.connection_id,
        }
        dashboards.append(dashboard)
        note = str(result.get("change_summary") or "initial")
        if len(note) > 500:
            note = note[:497] + "…"
        dashboard_versions[dashboard["id"]] = [{"version": 1, "spec": spec, "change_note": note}]
        _persist_unlocked()
        return dashboard


@router.get("/dashboards")
def list_dashboards() -> list[dict]:
    with _dash_lock:
        return list(dashboards)


@router.get("/dashboards/{dashboard_id}")
def get_dashboard(dashboard_id: int) -> dict:
    with _dash_lock:
        for dashboard in dashboards:
            if dashboard["id"] == dashboard_id:
                return dashboard
    raise HTTPException(status_code=404, detail="dashboard not found")


@router.post("/dashboards/{dashboard_id}/ai-edit")
def edit_dashboard(dashboard_id: int, payload: DashboardEditPayload) -> dict:
    with _dash_lock:
        target: dict | None = None
        for dashboard in dashboards:
            if dashboard["id"] == dashboard_id:
                target = dashboard
                break
        if target is None:
            raise HTTPException(status_code=404, detail="dashboard not found")
        current_spec = dict(target["spec"]) if isinstance(target.get("spec"), dict) else {}
        effective_conn = (
            payload.connection_id
            if payload.connection_id is not None
            else target.get("connection_id")
        )

    try:
        result = generate_spec(
            user_prompt=payload.prompt,
            connection_id=effective_conn if isinstance(effective_conn, int) else None,
            existing_spec=current_spec,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    updated = result["spec"]
    ai = result["ai"]
    meta = _meta_from_ai(ai)

    with _dash_lock:
        refreshed: dict | None = None
        for dashboard in dashboards:
            if dashboard["id"] == dashboard_id:
                refreshed = dashboard
                break
        if refreshed is None:
            raise HTTPException(status_code=404, detail="dashboard not found")
        refreshed["spec"] = updated
        refreshed["meta"] = meta
        if payload.connection_id is not None:
            refreshed["connection_id"] = payload.connection_id
        versions = dashboard_versions[dashboard_id]
        note = str(result.get("change_summary") or ai.get("output") or "ai-edit")
        if len(note) > 500:
            note = note[:497] + "…"
        versions.append({"version": len(versions) + 1, "spec": updated, "change_note": note})
        _persist_unlocked()
        return {"dashboard": refreshed, "preview": updated, "meta": meta}


@router.get("/dashboards/{dashboard_id}/versions")
def get_dashboard_versions(dashboard_id: int) -> list[dict]:
    with _dash_lock:
        if dashboard_id not in dashboard_versions:
            raise HTTPException(status_code=404, detail="dashboard not found")
        return list(dashboard_versions[dashboard_id])


@router.post("/dashboards/{dashboard_id}/run-queries")
def run_dashboard_queries(dashboard_id: int, payload: RunQueriesPayload) -> dict:
    with _dash_lock:
        dash: dict | None = None
        for d in dashboards:
            if d["id"] == dashboard_id:
                dash = d
                break
    if dash is None:
        raise HTTPException(status_code=404, detail="dashboard not found")

    cid = payload.connection_id
    if cid is None:
        raw = dash.get("connection_id")
        cid = int(raw) if isinstance(raw, int) else None
    if cid is None:
        raise HTTPException(
            status_code=400,
            detail="connection_id required (request body or saved on dashboard).",
        )

    widgets = list((dash.get("spec") or {}).get("widgets") or [])
    series = run_all_widget_queries(cid, widgets)
    return {"connection_id": cid, "series": series}
