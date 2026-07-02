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


def test_hybrid_search_explains_low_budget_intent_without_structured_filter():
    response = client.post(
        "/api/search/hybrid",
        json={
            "query": "预算不高 力学",
            "limit": 5,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] >= 2
    assert payload["items"][0]["exhibit"]["id"] == "pulley-wall"
    assert "匹配预算：低预算 15 万-28 万" in payload["items"][0]["reasons"]


def test_hybrid_search_applies_query_understanding_budget_range():
    response = client.post(
        "/api/search/hybrid",
        json={
            "query": "找预算 30-50 万的力学展项",
            "limit": 5,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["exhibit"]["id"] == "lever-play"
    assert "查询理解：预算区间 30 万-50 万" in payload["items"][0]["reasons"]


def test_hybrid_search_uses_reference_case_for_lower_budget_intent():
    response = client.post(
        "/api/search/hybrid",
        json={
            "query": "类似城市水循环沙盘但预算更低的方案",
            "limit": 5,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    ids = [item["exhibit"]["id"] for item in payload["items"]]
    assert "water-cycle" not in ids
    assert ids
    assert all(item["exhibit"]["budget_max"] < 420000 for item in payload["items"])
    assert "查询理解：预算低于参照案例 城市水循环沙盘" in payload["items"][0]["reasons"]


def test_hybrid_search_treats_overlapping_cheaper_budget_ranges_as_lower_than_reference():
    response = client.post(
        "/api/search/hybrid",
        json={
            "query": "类似杠杆乐园但预算更低的力学展项",
            "limit": 3,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] >= 1
    assert payload["items"][0]["exhibit"]["id"] == "pulley-wall"
    assert "lever-play" not in [item["exhibit"]["id"] for item in payload["items"]]
    assert "查询理解：预算低于参照案例 杠杆乐园" in payload["items"][0]["reasons"]


def test_hybrid_search_uses_query_understanding_for_chinese_business_intent():
    response = client.post(
        "/api/search/hybrid",
        json={
            "query": "找几个适合低龄儿童、预算不高、互动性强的力学展项",
            "limit": 5,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] >= 2
    assert payload["items"][0]["exhibit"]["id"] == "pulley-wall"
    joined_reasons = "；".join(payload["items"][0]["reasons"])
    assert "查询理解：主题 力学" in joined_reasons
    assert "查询理解：预算倾向 low" in joined_reasons
    assert "查询理解：人群 low_age_children" in joined_reasons


def test_hybrid_search_excludes_query_understanding_exclusions():
    response = client.post(
        "/api/search/hybrid",
        json={
            "query": "水循环展项，但不考虑数字投影",
            "limit": 5,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    ids = [item["exhibit"]["id"] for item in payload["items"]]
    assert "water-cycle" not in ids
    assert all(
        "数字投影" not in "；".join(item["reasons"])
        for item in payload["items"]
    )


def test_hybrid_search_total_counts_all_matches_before_limit():
    response = client.post(
        "/api/search/hybrid",
        json={
            "query": "力学",
            "limit": 1,
            "filters": {
                "theme": "力学",
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 2
    assert len(payload["items"]) == 1


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


def test_hybrid_search_respects_tag_filters():
    response = client.post(
        "/api/search/hybrid",
        json={
            "query": "力学",
            "limit": 5,
            "filters": {
                "tag": "低预算",
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["exhibit"]["id"] == "pulley-wall"
    assert "筛选标签：低预算" in payload["items"][0]["reasons"]


def test_hybrid_search_respects_owner_and_supplier_filters():
    owner_response = client.post(
        "/api/search/hybrid",
        json={
            "query": "力学",
            "limit": 5,
            "filters": {
                "owner": "青禾儿童科技馆",
            },
        },
    )
    supplier_response = client.post(
        "/api/search/hybrid",
        json={
            "query": "水循环",
            "limit": 5,
            "filters": {
                "supplier": "澄境模型",
            },
        },
    )

    assert owner_response.status_code == 200
    owner_payload = owner_response.json()
    assert owner_payload["total"] == 2
    assert {item["exhibit"]["id"] for item in owner_payload["items"]} == {"lever-play", "pulley-wall"}
    assert all("筛选业主：青禾儿童科技馆" in item["reasons"] for item in owner_payload["items"])

    assert supplier_response.status_code == 200
    supplier_payload = supplier_response.json()
    assert supplier_payload["total"] == 1
    assert supplier_payload["items"][0]["exhibit"]["id"] == "water-cycle"
    assert "筛选供应商：澄境模型" in supplier_payload["items"][0]["reasons"]


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


def test_hybrid_search_matches_uploaded_document_chunks():
    upload_response = client.post(
        "/api/exhibits/lever-play/assets",
        data={"asset_kind": "document", "note": "hybrid search smoke"},
        files={
            "file": (
                "hybrid-search-note.txt",
                b"kinetic prism torque memo for imported exhibit archives",
                "text/plain",
            )
        },
        headers={"X-User-Role": "editor"},
    )
    assert upload_response.status_code == 201

    response = client.post(
        "/api/search/hybrid",
        json={"query": "kinetic prism torque memo", "limit": 3},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] >= 1
    first = payload["items"][0]
    assert first["exhibit"]["id"] == "lever-play"
    assert "hybrid-search-note.txt" in " ".join(first["reasons"])
