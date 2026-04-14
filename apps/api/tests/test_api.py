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


def test_admin_semantic_mart_list_and_read(monkeypatch, tmp_path) -> None:
    mart = tmp_path / "tmart"
    mart.mkdir()
    (mart / "demo.yml").write_text("version: 1\n", encoding="utf-8")
    monkeypatch.setenv("SMART_BI_SEMANTIC_MART_DIR", str(mart))

    listed = client.get("/admin/semantic/mart/files")
    assert listed.status_code == 200
    data = listed.json()
    assert data["exists"] is True
    assert data["root"] == str(mart.resolve())
    paths = {f["path"] for f in data["files"]}
    assert "demo.yml" in paths

    got = client.get("/admin/semantic/mart/content", params={"path": "demo.yml"})
    assert got.status_code == 200
    assert got.json()["content"] == "version: 1\n"


def test_default_mart_semantic_dir_discovers_repo_mart(monkeypatch) -> None:
    """Without SMART_BI_SEMANTIC_MART_DIR, mart/ should resolve next to the monorepo root."""
    monkeypatch.delenv("SMART_BI_SEMANTIC_MART_DIR", raising=False)
    from app.services import semantic_store

    repo = Path(__file__).resolve().parents[3]
    expected = (repo / "mart").resolve()
    got = semantic_store.mart_semantic_dir().resolve()
    assert got == expected, f"expected {expected}, got {got}"


def test_admin_semantic_mart_content_validation(monkeypatch, tmp_path) -> None:
    mart = tmp_path / "m2"
    mart.mkdir()
    (mart / "z.yaml").write_text("a: b", encoding="utf-8")
    monkeypatch.setenv("SMART_BI_SEMANTIC_MART_DIR", str(mart))

    bad = client.get("/admin/semantic/mart/content", params={"path": "../../etc/passwd"})
    assert bad.status_code == 400

    missing = client.get("/admin/semantic/mart/content", params={"path": "missing.yml"})
    assert missing.status_code == 404


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


@patch("app.routers.dashboards.generate_spec")
def test_dashboard_create_and_edit(mock_generate_spec) -> None:
    mock_generate_spec.return_value = {
        "spec": {"widgets": [{"type": "kpi", "title": "Key", "field": "amount"}]},
        "ai": {"live": True, "error": None, "provider": "openai", "model": "gpt-4o-mini"},
        "change_summary": "ok",
    }
    create = client.post("/dashboards", json={"title": "Sales", "prompt": "Create revenue dashboard"})
    assert create.status_code == 200
    body = create.json()
    dashboard_id = body["id"]
    assert "meta" in body and "dashboard_gen" in body["meta"]
    dg = body["meta"]["dashboard_gen"]
    assert "live" in dg and "provider" in dg
    assert "parse_fallback" not in dg
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


@patch("app.routers.dashboards.generate_spec")
def test_dashboard_patch_delete_and_widget_crud(mock_generate_spec) -> None:
    mock_generate_spec.return_value = {
        "spec": {
            "widgets": [
                {"type": "kpi", "title": "A", "field": "x", "sql": "SELECT 1 AS x FROM dual"},
                {"type": "table", "title": "B", "sql": "SELECT 1 AS c FROM dual"},
            ]
        },
        "ai": {"live": True, "error": None, "provider": "openai", "model": "gpt-4o-mini"},
        "change_summary": "ok",
    }
    create = client.post("/dashboards", json={"title": "Dash", "prompt": "two widgets"})
    assert create.status_code == 200
    did = create.json()["id"]

    bad_patch = client.patch(f"/dashboards/{did}", json={})
    assert bad_patch.status_code == 400

    patch = client.patch(f"/dashboards/{did}", json={"title": "  Renamed  "})
    assert patch.status_code == 200
    assert patch.json()["title"] == "Renamed"

    add = client.post(
        f"/dashboards/{did}/widgets",
        json={"type": "kpi", "title": "New KPI", "field": "m", "sql": "SELECT 2 AS m FROM dual"},
    )
    assert add.status_code == 200
    assert add.json()["widget_index"] == 2
    assert len(add.json()["dashboard"]["spec"]["widgets"]) == 3

    upd = client.patch(
        f"/dashboards/{did}/widgets/0",
        json={"title": "A2", "sql": "SELECT 3 AS x FROM dual"},
    )
    assert upd.status_code == 200
    assert upd.json()["widget"]["title"] == "A2"

    rm = client.delete(f"/dashboards/{did}/widgets/1")
    assert rm.status_code == 200
    assert len(rm.json()["dashboard"]["spec"]["widgets"]) == 2

    versions = client.get(f"/dashboards/{did}/versions")
    assert versions.status_code == 200
    assert len(versions.json()) >= 5

    gone = client.delete(f"/dashboards/{did}")
    assert gone.status_code == 200
    assert client.get(f"/dashboards/{did}").status_code == 404


@patch("app.routers.dashboards.generate_spec")
def test_dashboard_run_queries_requires_connection(mock_generate_spec) -> None:
    mock_generate_spec.return_value = {
        "spec": {"widgets": [{"type": "kpi", "title": "K", "field": "x"}]},
        "ai": {"live": True, "error": None, "provider": "openai", "model": "gpt-4o-mini"},
        "change_summary": "ok",
    }
    create = client.post("/dashboards", json={"title": "NoConn", "prompt": "KPI only"})
    assert create.status_code == 200
    did = create.json()["id"]
    bad = client.post(f"/dashboards/{did}/run-queries", json={})
    assert bad.status_code == 400


def test_dashboard_run_queries_not_found() -> None:
    r = client.post("/dashboards/999999/run-queries", json={"connection_id": 1})
    assert r.status_code == 404


def test_humanize_sqlalchemy_auth_error() -> None:
    from sqlalchemy.exc import OperationalError

    from app.services.db_client_errors import humanize_sqlalchemy_error

    inner = Exception(
        'connection failed: FATAL:  password authentication failed for user "metabase_business_test"'
    )
    exc = OperationalError("SELECT 1", {}, inner)
    msg = humanize_sqlalchemy_error(exc, prefix="Query failed")
    assert "rejected the username/password" in msg
    assert "connections.example.json" in msg
