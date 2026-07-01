from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)

EDITOR_HEADERS = {"X-User-Role": "editor"}
VIEWER_HEADERS = {"X-User-Role": "viewer"}


def test_editor_can_request_relation_recommendations():
    response = client.get(
        "/api/exhibits/lever-play/relation-recommendations",
        headers=EDITOR_HEADERS,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["target_exhibit_id"] == "lever-play"
    assert payload["recommendations"]
    assert all(item["source_id"] == "lever-play" for item in payload["recommendations"])
    assert {
        "relation_type",
        "target_id",
        "target_label",
        "confidence",
        "reasons",
        "evidence_refs",
        "already_exists",
    } <= payload["recommendations"][0].keys()
    assert any(item["already_exists"] is True for item in payload["recommendations"])


def test_viewer_cannot_request_relation_recommendations():
    response = client.get(
        "/api/exhibits/lever-play/relation-recommendations",
        headers=VIEWER_HEADERS,
    )

    assert response.status_code == 403


def test_relation_recommendations_unknown_exhibit_returns_404():
    response = client.get(
        "/api/exhibits/not-found/relation-recommendations",
        headers=EDITOR_HEADERS,
    )

    assert response.status_code == 404
