from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.ai_router import run_task

router = APIRouter(tags=["dashboards"])

dashboards: list[dict] = []
dashboard_versions: dict[int, list[dict]] = {}


class DashboardCreatePayload(BaseModel):
    prompt: str
    title: str


class DashboardEditPayload(BaseModel):
    prompt: str


@router.post("/dashboards")
def create_dashboard(payload: DashboardCreatePayload) -> dict:
    ai = run_task("dashboard_gen", payload.prompt)
    spec = {
        "widgets": [
            {"type": "line", "title": "Revenue by Date", "x": "order_date", "y": "revenue"},
        ]
    }
    dashboard = {"id": len(dashboards) + 1, "title": payload.title, "spec": spec, "created_by_model": ai["model"]}
    dashboards.append(dashboard)
    dashboard_versions[dashboard["id"]] = [{"version": 1, "spec": spec, "change_note": "initial"}]
    return dashboard


@router.get("/dashboards")
def list_dashboards() -> list[dict]:
    return dashboards


@router.get("/dashboards/{dashboard_id}")
def get_dashboard(dashboard_id: int) -> dict:
    for dashboard in dashboards:
        if dashboard["id"] == dashboard_id:
            return dashboard
    raise HTTPException(status_code=404, detail="dashboard not found")


@router.post("/dashboards/{dashboard_id}/ai-edit")
def edit_dashboard(dashboard_id: int, payload: DashboardEditPayload) -> dict:
    ai = run_task("dashboard_gen", payload.prompt)
    for dashboard in dashboards:
        if dashboard["id"] == dashboard_id:
            current = dashboard["spec"]
            updated = {
                "widgets": current["widgets"] + [{"type": "kpi", "title": "Total Revenue", "field": "revenue"}]
            }
            dashboard["spec"] = updated
            versions = dashboard_versions[dashboard_id]
            versions.append({"version": len(versions) + 1, "spec": updated, "change_note": ai["output"]})
            return {"dashboard": dashboard, "preview": updated}
    raise HTTPException(status_code=404, detail="dashboard not found")


@router.get("/dashboards/{dashboard_id}/versions")
def get_dashboard_versions(dashboard_id: int) -> list[dict]:
    if dashboard_id not in dashboard_versions:
        raise HTTPException(status_code=404, detail="dashboard not found")
    return dashboard_versions[dashboard_id]
