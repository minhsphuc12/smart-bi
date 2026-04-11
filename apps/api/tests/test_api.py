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


def test_dashboard_create_and_edit() -> None:
    create = client.post("/dashboards", json={"title": "Sales", "prompt": "Create revenue dashboard"})
    assert create.status_code == 200
    dashboard_id = create.json()["id"]

    edit = client.post(f"/dashboards/{dashboard_id}/ai-edit", json={"prompt": "Add KPI card"})
    assert edit.status_code == 200

    versions = client.get(f"/dashboards/{dashboard_id}/versions")
    assert versions.status_code == 200
    assert len(versions.json()) >= 2
