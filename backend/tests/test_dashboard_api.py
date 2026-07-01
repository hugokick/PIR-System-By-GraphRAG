from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_dashboard_summary_returns_collection_metrics() -> None:
    response = client.get("/api/dashboard/summary")

    assert response.status_code == 200
    payload = response.json()

    assert payload["total"] == 3
    assert payload["landed"] == 1
    assert payload["avg_budget"] == 35
    assert payload["pending_review"] == 1
    assert payload["rejected_review"] == 1
    assert payload["budget_bands"] == [
        {"label": "20万以下", "count": 0},
        {"label": "20-50万", "count": 2},
        {"label": "50万以上", "count": 1},
    ]
    assert payload["themes"][0]["count"] == 2
    assert {item["count"] for item in payload["categories"]} == {1, 2}
    assert len(payload["review_statuses"]) == 3


def test_dashboard_summary_respects_exhibit_filters() -> None:
    response = client.get(
        "/api/dashboard/summary",
        params={
            "review_status": "待审核",
        },
    )

    assert response.status_code == 200
    payload = response.json()

    assert payload["total"] == 1
    assert payload["landed"] == 0
    assert payload["pending_review"] == 1
    assert payload["rejected_review"] == 0


def test_dashboard_summary_respects_tag_filter() -> None:
    response = client.get("/api/dashboard/summary", params={"tag": "低预算"})

    assert response.status_code == 200
    payload = response.json()

    assert payload["total"] == 1
    assert payload["budget_bands"] == [
        {"label": "20万以下", "count": 0},
        {"label": "20-50万", "count": 1},
        {"label": "50万以上", "count": 0},
    ]
