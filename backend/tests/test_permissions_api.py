from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)

ADMIN_HEADERS = {"X-User-Role": "admin"}
EDITOR_HEADERS = {"X-User-Role": "editor"}
VIEWER_HEADERS = {"X-User-Role": "viewer"}


def exhibit_payload(exhibit_id: str = "permission-demo"):
    payload = client.get("/api/exhibits/pulley-wall").json()
    payload["id"] = exhibit_id
    payload["name"] = "Permission Demo"
    return payload


def test_mutations_require_editor_or_admin_role():
    response = client.post("/api/exhibits", json=exhibit_payload("viewer-create-denied"))

    assert response.status_code == 403
    assert response.json()["detail"]["error"] == "Forbidden"

    viewer_response = client.post(
        "/api/exhibits",
        json=exhibit_payload("viewer-create-denied-explicit"),
        headers=VIEWER_HEADERS,
    )

    assert viewer_response.status_code == 403
    assert viewer_response.json()["detail"]["details"]["required_roles"] == ["admin", "editor"]


def test_demo_login_returns_role_token_and_profile():
    response = client.post(
        "/api/auth/login",
        json={"username": "editor", "password": "editor123"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["user"]["username"] == "editor"
    assert payload["user"]["role"] == "editor"
    assert payload["access_token"]
    assert payload["token_type"] == "bearer"


def test_demo_login_rejects_invalid_credentials():
    response = client.post(
        "/api/auth/login",
        json={"username": "editor", "password": "wrong-password"},
    )

    assert response.status_code == 401
    assert response.json()["detail"]["error"] == "InvalidCredentials"


def test_auth_me_returns_profile_for_valid_bearer_token():
    login_response = client.post(
        "/api/auth/login",
        json={"username": "editor", "password": "editor123"},
    )
    token = login_response.json()["access_token"]

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "username": "editor",
        "role": "editor",
        "display_name": "编辑员",
    }


def test_auth_me_rejects_invalid_bearer_token():
    response = client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == 401
    assert response.json()["detail"]["error"] == "InvalidToken"


def test_bearer_token_authorizes_role_protected_mutations():
    login_response = client.post(
        "/api/auth/login",
        json={"username": "editor", "password": "editor123"},
    )
    token = login_response.json()["access_token"]

    create_response = client.post(
        "/api/exhibits",
        json=exhibit_payload("editor-token-demo"),
        headers={"Authorization": f"Bearer {token}"},
    )

    assert create_response.status_code == 201

    delete_response = client.delete(
        "/api/exhibits/editor-token-demo",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert delete_response.status_code == 403


def test_role_header_auth_can_be_disabled_for_public_runtime(monkeypatch):
    monkeypatch.setenv("ALLOW_ROLE_HEADER_AUTH", "false")

    response = client.post(
        "/api/exhibits",
        json=exhibit_payload("header-auth-disabled-demo"),
        headers=ADMIN_HEADERS,
    )

    assert response.status_code == 403
    assert response.json()["detail"]["details"]["role"] == "viewer"


def test_editor_can_create_and_update_but_cannot_delete():
    create_response = client.post(
        "/api/exhibits",
        json=exhibit_payload("editor-permission-demo"),
        headers=EDITOR_HEADERS,
    )
    assert create_response.status_code == 201

    payload = create_response.json()
    payload["name"] = "Editor Updated Demo"
    update_response = client.put(
        "/api/exhibits/editor-permission-demo",
        json=payload,
        headers=EDITOR_HEADERS,
    )
    assert update_response.status_code == 200
    assert update_response.json()["name"] == "Editor Updated Demo"

    delete_response = client.delete(
        "/api/exhibits/editor-permission-demo",
        headers=EDITOR_HEADERS,
    )
    assert delete_response.status_code == 403
    assert client.get("/api/exhibits/editor-permission-demo").status_code == 200


def test_only_admin_can_update_review_status_and_audit_it():
    create_response = client.post(
        "/api/exhibits",
        json=exhibit_payload("review-workflow-demo"),
        headers=ADMIN_HEADERS,
    )
    assert create_response.status_code == 201
    assert create_response.json()["review_status"] != "已审核"

    editor_response = client.patch(
        "/api/exhibits/review-workflow-demo/review-status",
        json={"review_status": "已审核"},
        headers=EDITOR_HEADERS,
    )
    assert editor_response.status_code == 403

    admin_response = client.patch(
        "/api/exhibits/review-workflow-demo/review-status",
        json={"review_status": "已审核"},
        headers=ADMIN_HEADERS,
    )
    assert admin_response.status_code == 200
    assert admin_response.json()["review_status"] == "已审核"

    audit_response = client.get("/api/admin/audit-logs", headers=ADMIN_HEADERS)
    entries = audit_response.json()["items"]
    assert any(
        entry["actor_role"] == "admin"
        and entry["action"] == "update_review_status"
        and entry["resource_id"] == "review-workflow-demo"
        and "已审核" in entry["summary"]
        and "Updated review" not in entry["summary"]
        for entry in entries
    )


def test_admin_can_delete_and_audit_log_records_mutations():
    create_response = client.post(
        "/api/exhibits",
        json=exhibit_payload("admin-audit-demo"),
        headers=ADMIN_HEADERS,
    )
    assert create_response.status_code == 201

    delete_response = client.delete("/api/exhibits/admin-audit-demo", headers=ADMIN_HEADERS)
    assert delete_response.status_code == 204

    audit_response = client.get("/api/admin/audit-logs", headers=ADMIN_HEADERS)
    assert audit_response.status_code == 200
    entries = audit_response.json()["items"]
    assert any(
        entry["actor_role"] == "admin"
        and entry["action"] == "create_exhibit"
        and entry["resource_id"] == "admin-audit-demo"
        and "新增档案 admin-audit-demo" in entry["summary"]
        and "Created exhibit" not in entry["summary"]
        for entry in entries
    )
    assert any(
        entry["actor_role"] == "admin"
        and entry["action"] == "delete_exhibit"
        and entry["resource_id"] == "admin-audit-demo"
        and "删除档案 admin-audit-demo" in entry["summary"]
        and "Deleted exhibit" not in entry["summary"]
        for entry in entries
    )


def test_admin_can_filter_audit_logs_by_action_and_resource_id():
    audit_id = "admin-audit-filter-demo"
    create_response = client.post(
        "/api/exhibits",
        json=exhibit_payload(audit_id),
        headers=ADMIN_HEADERS,
    )
    assert create_response.status_code == 201

    delete_response = client.delete(f"/api/exhibits/{audit_id}", headers=ADMIN_HEADERS)
    assert delete_response.status_code == 204

    audit_response = client.get(
        "/api/admin/audit-logs",
        params={"action": "delete_exhibit", "resource_id": audit_id},
        headers=ADMIN_HEADERS,
    )
    assert audit_response.status_code == 200
    payload = audit_response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["action"] == "delete_exhibit"
    assert payload["items"][0]["resource_id"] == audit_id
    assert "删除档案 admin-audit-filter-demo" in payload["items"][0]["summary"]


def test_admin_cannot_delete_approved_or_landed_exhibit_directly():
    protected_id = "protected-delete-demo"
    payload = exhibit_payload(protected_id)
    payload["status"] = "已落地"
    payload["review_status"] = "已审核"
    create_response = client.post(
        "/api/exhibits",
        json=payload,
        headers=ADMIN_HEADERS,
    )
    assert create_response.status_code == 201

    try:
        delete_response = client.delete(f"/api/exhibits/{protected_id}", headers=ADMIN_HEADERS)

        assert delete_response.status_code == 409
        detail = delete_response.json()["detail"]
        assert detail["error"] == "ProtectedExhibit"
        assert detail["details"] == {
            "id": protected_id,
            "status": "已落地",
            "review_status": "已审核",
        }
        assert client.get(f"/api/exhibits/{protected_id}").status_code == 200
    finally:
        cleanup_payload = client.get(f"/api/exhibits/{protected_id}").json()
        cleanup_payload["status"] = "制作中"
        cleanup_payload["review_status"] = "待审核"
        client.put(f"/api/exhibits/{protected_id}", json=cleanup_payload, headers=ADMIN_HEADERS)
        client.delete(f"/api/exhibits/{protected_id}", headers=ADMIN_HEADERS)


def test_only_admin_can_read_audit_logs():
    response = client.get("/api/admin/audit-logs", headers=EDITOR_HEADERS)

    assert response.status_code == 403


def test_admin_can_export_filtered_audit_logs_as_csv():
    audit_id = "admin-audit-export-demo"
    create_response = client.post(
        "/api/exhibits",
        json=exhibit_payload(audit_id),
        headers=ADMIN_HEADERS,
    )
    assert create_response.status_code == 201
    delete_response = client.delete(f"/api/exhibits/{audit_id}", headers=ADMIN_HEADERS)
    assert delete_response.status_code == 204

    response = client.get(
        "/api/admin/audit-logs/export",
        params={"action": "delete_exhibit", "resource_id": audit_id},
        headers=ADMIN_HEADERS,
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "audit-logs.csv" in response.headers["content-disposition"]
    assert response.content.startswith(b"\xef\xbb\xbf")
    csv_text = response.content.decode("utf-8-sig")
    assert "日志编号,操作者角色,动作,资源类型,资源编号,摘要,时间" in csv_text
    assert "删除档案" in csv_text
    assert f"删除档案 {audit_id}" in csv_text
    assert f"新增档案 {audit_id}" not in csv_text


def test_only_admin_can_export_audit_logs():
    response = client.get("/api/admin/audit-logs/export", headers=EDITOR_HEADERS)

    assert response.status_code == 403
