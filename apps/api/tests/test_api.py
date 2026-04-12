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


def test_ask_question_contract() -> None:
    response = client.post("/chat/questions", json={"question": "Revenue by day?"})
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert "sql" in data
    assert "columns" in data
    assert "rows" in data


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
    dashboard_id = create.json()["id"]

    edit = client.post(f"/dashboards/{dashboard_id}/ai-edit", json={"prompt": "Add KPI card"})
    assert edit.status_code == 200

    versions = client.get(f"/dashboards/{dashboard_id}/versions")
    assert versions.status_code == 200
    assert len(versions.json()) >= 2
