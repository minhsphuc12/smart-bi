import json
import os
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_login() -> None:
    response = client.post("/auth/login", json={"username": "admin1", "password": "secret"})
    assert response.status_code == 200
    data = response.json()
    assert data["token_type"] == "bearer"
    assert data["role"] == "admin"


def test_ask_question_requires_connection_id() -> None:
    response = client.post("/chat/questions", json={"question": "Revenue by day?"})
    assert response.status_code == 422


@patch("app.routers.chat.nl2sql_pipeline.answer_question")
def test_ask_question_contract(mock_answer) -> None:
    mock_answer.return_value = {
        "answer": "Synthetic answer for contract test.",
        "sql": "SELECT 1 AS one",
        "columns": ["one"],
        "rows": [[1]],
        "confidence": 0.9,
        "warnings": [],
        "evidence": {"query_kind": "llm_sql", "row_count": 1, "execution_ms": 1},
        "meta": {
            "sql_model": "stub",
            "answer_model": "stub",
            "sql_task_note": "",
            "answer_task_note": "",
            "sql_live": False,
            "answer_live": False,
        },
    }
    response = client.post(
        "/chat/questions",
        json={"question": "Revenue by day?", "connection_id": 1},
    )
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert "sql" in data
    assert "columns" in data
    assert "rows" in data
    assert "evidence" in data
    assert data["evidence"].get("query_kind") == "llm_sql"
    mock_answer.assert_called_once_with(1, "Revenue by day?")


def test_admin_connections_persist_and_update() -> None:
    create_body = {
        "name": "Dev PG",
        "source_type": "postgresql",
        "host": "127.0.0.1",
        "port": 5432,
        "database": "smartbi",
        "username": "smartbi",
        "password": "secret1",
    }
    created = client.post("/admin/connections", json=create_body)
    assert created.status_code == 200
    cid = created.json()["id"]

    listed = client.get("/admin/connections")
    assert listed.status_code == 200
    rows = listed.json()
    assert len(rows) == 1
    assert rows[0]["name"] == "Dev PG"
    assert rows[0]["password"] == "***"

    update_body = {
        **create_body,
        "name": "Dev PG renamed",
    }
    del update_body["password"]
    updated = client.put(f"/admin/connections/{cid}", json=update_body)
    assert updated.status_code == 200
    assert updated.json()["name"] == "Dev PG renamed"

    listed2 = client.get("/admin/connections")
    assert listed2.json()[0]["name"] == "Dev PG renamed"

    with_password = {**update_body, "password": "secret2"}
    client.put(f"/admin/connections/{cid}", json=with_password)
    test_res = client.post(f"/admin/connections/{cid}/test")
    assert test_res.status_code in (200, 400)


def test_admin_semantic_persisted_to_file() -> None:
    from app.services import semantic_store

    created = client.post("/admin/semantic/tables", json={"name": "orders", "description": "Fact table"})
    assert created.status_code == 200
    disk = semantic_store.load_semantic()
    assert len(disk["tables"]) == 1
    assert disk["tables"][0]["name"] == "orders"


def test_admin_ai_routing_persisted_to_file() -> None:
    from app.services import ai_routing_store

    body = {
        "task": "sql_gen",
        "provider": "openai",
        "model": "gpt-4o-mini",
        "temperature": 0.11,
        "max_tokens": 900,
        "timeout": 30,
        "cost_limit": 1.0,
    }
    updated = client.post("/admin/ai-routing/profiles", json=body)
    assert updated.status_code == 200
    disk = ai_routing_store.load_profiles()
    assert disk["sql_gen"]["temperature"] == 0.11
    assert disk["sql_gen"]["max_tokens"] == 900


def test_dashboard_create_and_edit() -> None:
    create = client.post("/dashboards", json={"title": "Sales", "prompt": "Create revenue dashboard"})
    assert create.status_code == 200
    body = create.json()
    dashboard_id = body["id"]
    assert "meta" in body and "dashboard_gen" in body["meta"]
    dg = body["meta"]["dashboard_gen"]
    assert "live" in dg and "parse_fallback" in dg
    assert isinstance(body.get("spec", {}).get("widgets"), list)
    assert len(body["spec"]["widgets"]) >= 1

    edit = client.post(f"/dashboards/{dashboard_id}/ai-edit", json={"prompt": "Add KPI card"})
    assert edit.status_code == 200
    assert "meta" in edit.json()

    versions = client.get(f"/dashboards/{dashboard_id}/versions")
    assert versions.status_code == 200
    assert len(versions.json()) >= 2

    path = Path(os.environ["SMART_BI_DASHBOARDS_FILE"])
    disk = json.loads(path.read_text(encoding="utf-8"))
    assert len(disk["dashboards"]) == 1
    assert str(dashboard_id) in disk["versions"]
    assert len(disk["versions"][str(dashboard_id)]) >= 2


def test_dashboard_run_queries_requires_connection() -> None:
    create = client.post("/dashboards", json={"title": "NoConn", "prompt": "KPI only"})
    assert create.status_code == 200
    did = create.json()["id"]
    bad = client.post(f"/dashboards/{did}/run-queries", json={})
    assert bad.status_code == 400


def test_dashboard_run_queries_not_found() -> None:
    r = client.post("/dashboards/999999/run-queries", json={"connection_id": 1})
    assert r.status_code == 404
