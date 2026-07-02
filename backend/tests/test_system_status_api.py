from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)

ADMIN_HEADERS = {"X-User-Role": "admin"}
EDITOR_HEADERS = {"X-User-Role": "editor"}


def test_admin_can_read_system_status(monkeypatch):
    monkeypatch.setenv("FILE_STORAGE_BACKEND", "local")
    monkeypatch.setenv("ALLOW_ROLE_HEADER_AUTH", "false")
    monkeypatch.setenv("AUTH_TOKEN_TTL_SECONDS", "28800")
    monkeypatch.setenv("NEO4J_DEMO_ENABLED", "true")
    monkeypatch.setenv("NEO4J_URI", "bolt://neo4j:7687")
    login_response = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    token = login_response.json()["access_token"]

    response = client.get(
        "/api/admin/system-status",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["service"] == "exhibit-atlas-api"
    assert payload["repository"]["kind"] in {"memory", "postgres"}
    assert payload["storage"]["backend"] == "local"
    assert payload["auth"]["role_header_auth_enabled"] is False
    assert payload["auth"]["token_ttl_seconds"] == 28800
    assert payload["neo4j_demo"]["enabled"] is True
    assert payload["neo4j_demo"]["configured"] is True
    assert payload["counts"]["exhibits"] >= 1
    assert payload["counts"]["audit_logs"] >= 0


def test_only_admin_can_read_system_status():
    response = client.get("/api/admin/system-status", headers=EDITOR_HEADERS)

    assert response.status_code == 403
