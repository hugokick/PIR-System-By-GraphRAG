from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def _list_items(params=None):
    response = client.get("/api/exhibits", params=params or {})
    assert response.status_code == 200
    return response.json()["items"]


def test_dashboard_summary_returns_collection_metrics() -> None:
    response = client.get("/api/dashboard/summary")

    assert response.status_code == 200
    payload = response.json()
    items = _list_items()

    assert payload["total"] == len(items)
    assert payload["landed"] == sum(1 for item in items if item["status"] == "已落地")
    assert payload["pending_review"] == sum(1 for item in items if item["review_status"] == "待审核")
    assert payload["rejected_review"] == sum(1 for item in items if item["review_status"] == "已退回")
    assert sum(item["count"] for item in payload["budget_bands"]) == payload["total"]
    assert sum(item["count"] for item in payload["categories"]) == payload["total"]
    assert sum(item["count"] for item in payload["themes"]) == payload["total"]
    assert sum(item["count"] for item in payload["review_statuses"]) == payload["total"]


def test_dashboard_summary_respects_exhibit_filters() -> None:
    params = {"review_status": "待审核"}
    response = client.get("/api/dashboard/summary", params=params)

    assert response.status_code == 200
    payload = response.json()
    items = _list_items(params)

    assert payload["total"] == len(items)
    assert payload["pending_review"] == len(items)
    assert payload["rejected_review"] == 0
    assert all(item["review_status"] == "待审核" for item in items)


def test_dashboard_summary_respects_tag_filter() -> None:
    params = {"tag": "低预算"}
    response = client.get("/api/dashboard/summary", params=params)

    assert response.status_code == 200
    payload = response.json()
    items = _list_items(params)

    assert payload["total"] == len(items)
    assert payload["total"] >= 1
    assert all("低预算" in item["tags"] for item in items)
    assert sum(item["count"] for item in payload["budget_bands"]) == payload["total"]


def test_dashboard_summary_respects_owner_filter() -> None:
    params = {"owner": "青禾儿童科技馆"}
    response = client.get("/api/dashboard/summary", params=params)

    assert response.status_code == 200
    payload = response.json()
    items = _list_items(params)

    assert payload["total"] == len(items)
    assert payload["total"] >= 2
    assert all(item["owner"]["name"] == "青禾儿童科技馆" for item in items)
