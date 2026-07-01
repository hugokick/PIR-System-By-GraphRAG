from fastapi.testclient import TestClient

from app.repository import seed_exhibits
from app.main import app


client = TestClient(app)


def test_graphrag_search_returns_ranked_hits_with_graph_context_and_citations():
    response = client.post(
        "/api/graphrag/search",
        json={"query": "lever-play", "top_k": 2},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["query"] == "lever-play"
    assert payload["total"] >= 1

    first = payload["items"][0]
    assert first["exhibit"]["id"] == "lever-play"
    assert first["score"] > 0
    assert first["reasons"]
    assert any(citation["source_type"] == "exhibit" for citation in first["citations"])

    node_ids = {node["id"] for node in first["graph"]["nodes"]}
    edge_types = {edge["type"] for edge in first["graph"]["edges"]}
    assert "exhibit:lever-play" in node_ids
    assert "has_theme" in edge_types


def test_graphrag_search_applies_structured_filters():
    response = client.post(
        "/api/graphrag/search",
        json={
            "query": "力学",
            "top_k": 5,
            "filters": {
                "theme": "力学",
                "status": "已落地",
                "budget_min": 100000,
                "budget_max": 400000,
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["exhibit"]["id"] == "lever-play"


def test_graphrag_search_applies_review_status_filter():
    response = client.post(
        "/api/graphrag/search",
        json={
            "query": "力学",
            "top_k": 5,
            "filters": {
                "theme": "力学",
                "review_status": "待审核",
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["exhibit"]["id"] == "pulley-wall"
    assert payload["items"][0]["exhibit"]["review_status"] == "待审核"


def test_graphrag_search_applies_tag_filter():
    response = client.post(
        "/api/graphrag/search",
        json={
            "query": "力学",
            "top_k": 5,
            "filters": {
                "tag": "低预算",
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["exhibit"]["id"] == "pulley-wall"


def test_graphrag_search_applies_owner_and_supplier_filters():
    owner_response = client.post(
        "/api/graphrag/search",
        json={
            "query": "水循环",
            "top_k": 5,
            "filters": {
                "owner": "青禾儿童科技馆",
            },
        },
    )
    supplier_response = client.post(
        "/api/graphrag/search",
        json={
            "query": "力学",
            "top_k": 5,
            "filters": {
                "supplier": "澄境模型",
            },
        },
    )

    assert owner_response.status_code == 200
    owner_payload = owner_response.json()
    assert owner_payload["total"] == 0
    assert owner_payload["items"] == []

    assert supplier_response.status_code == 200
    supplier_payload = supplier_response.json()
    assert supplier_payload["total"] == 0
    assert supplier_payload["items"] == []


def test_graphrag_search_total_counts_all_matches_before_top_k():
    response = client.post(
        "/api/graphrag/search",
        json={
            "query": "力学",
            "top_k": 1,
            "filters": {
                "theme": "力学",
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 2
    assert len(payload["items"]) == 1


def test_graphrag_search_keeps_document_citations_with_their_exhibit():
    response = client.post(
        "/api/graphrag/search",
        json={"query": "力学", "top_k": 2, "filters": {"theme": "力学"}},
    )

    assert response.status_code == 200
    payload = response.json()
    items_by_id = {item["exhibit"]["id"]: item for item in payload["items"]}
    lever_citation_ids = {citation["source_id"] for citation in items_by_id["lever-play"]["citations"]}
    pulley_citation_ids = {citation["source_id"] for citation in items_by_id["pulley-wall"]["citations"]}

    assert "lever-brief" in lever_citation_ids
    assert "lever-brief" not in pulley_citation_ids


def test_graphrag_search_explains_document_matches_in_business_language():
    response = client.post(
        "/api/graphrag/search",
        json={"query": "样例文档 来源链路", "top_k": 1},
    )

    assert response.status_code == 200
    payload = response.json()
    first = payload["items"][0]

    assert first["exhibit"]["id"] == "lever-play"
    assert "匹配资料：杠杆乐园展项说明" in first["reasons"]
    assert any(citation["source_id"] == "lever-brief" for citation in first["citations"])


def test_graphrag_search_uses_repository_vector_scores(monkeypatch):
    from app import main

    class VectorScoreRepository:
        def list_exhibits(self):
            return seed_exhibits

        def semantic_scores(self, query: str, limit: int = 20):
            assert query == "液体城市系统"
            return {"water-cycle": 0.91}

    monkeypatch.setattr(main, "repository", VectorScoreRepository())

    response = client.post(
        "/api/graphrag/search",
        json={"query": "液体城市系统", "top_k": 1},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["items"][0]["exhibit"]["id"] == "water-cycle"
    assert "向量召回" in "；".join(payload["items"][0]["reasons"])
    assert payload["items"][0]["citations"]


def test_graphrag_search_passes_repository_kg_snapshot_to_contract(monkeypatch):
    from app import main
    from app.graphrag.contract import KGGraphRAGQueryResult
    from app.kg.builder import build_exhibit_kg_snapshot
    from app.services import graphrag as graphrag_service

    snapshot = build_exhibit_kg_snapshot(seed_exhibits)
    seen = {}

    class SnapshotRepository:
        def list_exhibits(self):
            return seed_exhibits

        def semantic_scores(self, query: str, limit: int = 20):
            return {}

        def get_kg_snapshot(self):
            return snapshot

    def recording_query_contract(query_input, exhibits, snapshot=None, semantic_scores=None):
        seen["snapshot"] = snapshot
        return KGGraphRAGQueryResult()

    monkeypatch.setattr(main, "repository", SnapshotRepository())
    monkeypatch.setattr(graphrag_service, "query_graphrag_contract", recording_query_contract)

    response = client.post(
        "/api/graphrag/search",
        json={"query": "力学", "top_k": 1},
    )

    assert response.status_code == 200
    assert seen["snapshot"] is snapshot


def test_graphrag_answer_passes_repository_kg_snapshot_to_contract(monkeypatch):
    from app import main
    from app.graphrag.contract import KGGraphRAGQueryResult
    from app.kg.builder import build_exhibit_kg_snapshot
    from app.services import graphrag as graphrag_service

    snapshot = build_exhibit_kg_snapshot(seed_exhibits)
    seen = {}

    class SnapshotRepository:
        def list_exhibits(self):
            return seed_exhibits

        def semantic_scores(self, query: str, limit: int = 20):
            return {}

        def get_kg_snapshot(self):
            return snapshot

    def recording_query_contract(query_input, exhibits, snapshot=None, semantic_scores=None):
        seen["snapshot"] = snapshot
        return KGGraphRAGQueryResult()

    monkeypatch.setattr(main, "repository", SnapshotRepository())
    monkeypatch.setattr(graphrag_service, "query_graphrag_contract", recording_query_contract)

    response = client.post(
        "/api/graphrag/answer",
        json={"query": "力学", "top_k": 1},
    )

    assert response.status_code == 200
    assert seen["snapshot"] is snapshot


def test_graphrag_answer_uses_search_hits_and_returns_citations():
    response = client.post(
        "/api/graphrag/answer",
        json={"query": "lever-play", "top_k": 1},
    )

    assert response.status_code == 200
    payload = response.json()
    assert "lever-play" in payload["answer"]
    assert payload["citations"]
    assert payload["items"][0]["exhibit"]["id"] == "lever-play"


def test_graphrag_answer_is_source_grounded_with_numbered_citations():
    response = client.post(
        "/api/graphrag/answer",
        json={"query": "lever-play", "top_k": 1, "filters": {"theme": "力学"}},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["items"][0]["exhibit"]["id"] == "lever-play"
    assert "根据库内资料" in payload["answer"]
    assert "[1]" in payload["answer"]
    assert "杠杆乐园" in payload["answer"]
    assert payload["citations"][0]["title"]
    assert payload["citations"][0]["snippet"]


def test_graphrag_answer_reports_when_no_evidence_is_found():
    response = client.post(
        "/api/graphrag/answer",
        json={"query": "definitely-not-in-library", "top_k": 3},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["items"] == []
    assert payload["citations"] == []
    assert "未找到依据" in payload["answer"]
