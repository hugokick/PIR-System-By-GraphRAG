from fastapi.testclient import TestClient

from app.repository import seed_exhibits
from app.main import app


client = TestClient(app)


def test_hybrid_search_combines_structured_filters_and_query_reasons():
    response = client.post(
        "/api/search/hybrid",
        json={
            "query": "找几个适合低龄儿童、预算不高、互动性强的力学展项",
            "limit": 5,
            "filters": {
                "venue_type": "儿童科技馆",
                "theme": "力学",
                "material": "金属",
                "interaction": "机械互动",
                "budget_max": 350000,
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["query"] == "找几个适合低龄儿童、预算不高、互动性强的力学展项"
    assert payload["total"] >= 1

    ids = [item["exhibit"]["id"] for item in payload["items"]]
    assert "pulley-wall" in ids
    assert set(ids) <= {"lever-play", "pulley-wall"}

    pulley_hit = next(item for item in payload["items"] if item["exhibit"]["id"] == "pulley-wall")
    assert pulley_hit["score"] > 0
    assert "低龄儿童" in "；".join(pulley_hit["reasons"])
    assert "预算" in "；".join(pulley_hit["reasons"])
    assert "机械互动" in "；".join(pulley_hit["reasons"])


def test_hybrid_search_respects_budget_filters():
    response = client.post(
        "/api/search/hybrid",
        json={
            "query": "水循环 沙盘",
            "limit": 5,
            "filters": {
                "budget_max": 300000,
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["items"] == []


def test_hybrid_search_respects_project_case_filters():
    response = client.post(
        "/api/search/hybrid",
        json={
            "query": "water-cycle",
            "limit": 5,
            "filters": {
                "project_id": "jiangbei-2022",
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["exhibit"]["id"] == "water-cycle"


def test_hybrid_search_respects_review_status_filters():
    response = client.post(
        "/api/search/hybrid",
        json={
            "query": "pulley-wall",
            "limit": 5,
            "filters": {
                "review_status": "待审核",
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["exhibit"]["id"] == "pulley-wall"
    assert any("待审核" in reason for reason in payload["items"][0]["reasons"])


def test_hybrid_search_matches_exhibit_ids_for_smoke_checks_and_exact_lookup():
    response = client.post(
        "/api/search/hybrid",
        json={"query": "lever-play", "limit": 1},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["exhibit"]["id"] == "lever-play"
    assert "lever-play" in "；".join(payload["items"][0]["reasons"])


def test_hybrid_search_uses_repository_vector_scores(monkeypatch):
    from app import main

    class VectorScoreRepository:
        def list_exhibits(self):
            return seed_exhibits

        def semantic_scores(self, query: str, limit: int = 20):
            assert query == "液体城市系统"
            return {"water-cycle": 0.91}

    monkeypatch.setattr(main, "repository", VectorScoreRepository())

    response = client.post(
        "/api/search/hybrid",
        json={"query": "液体城市系统", "limit": 3},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["exhibit"]["id"] == "water-cycle"
    assert "向量召回" in "；".join(payload["items"][0]["reasons"])


def test_hybrid_search_ignores_low_confidence_vector_noise(monkeypatch):
    from app import main

    class LowScoreRepository:
        def list_exhibits(self):
            return seed_exhibits

        def semantic_scores(self, query: str, limit: int = 20):
            return {"water-cycle": 0.05}

    monkeypatch.setattr(main, "repository", LowScoreRepository())

    response = client.post(
        "/api/search/hybrid",
        json={"query": "unrelated-low-confidence-vector-only", "limit": 3},
    )

    assert response.status_code == 200
    assert response.json()["items"] == []
