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


def test_graphrag_search_applies_query_understanding_budget_range():
    response = client.post(
        "/api/graphrag/search",
        json={
            "query": "找预算 30-50 万的力学展项",
            "top_k": 5,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["exhibit"]["id"] == "lever-play"
    assert "查询理解：预算区间 30 万-50 万" in payload["items"][0]["reasons"]


def test_graphrag_search_uses_reference_case_for_lower_budget_intent():
    response = client.post(
        "/api/graphrag/search",
        json={
            "query": "类似城市水循环沙盘但预算更低的方案",
            "top_k": 5,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    ids = [item["exhibit"]["id"] for item in payload["items"]]
    assert "water-cycle" not in ids
    assert ids
    assert all(item["exhibit"]["budget_max"] < 420000 for item in payload["items"])
    assert "查询理解：预算低于参照案例 城市水循环沙盘" in payload["items"][0]["reasons"]


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


def test_graphrag_search_applies_category_and_project_filters():
    category_response = client.post(
        "/api/graphrag/search",
        json={
            "query": "水循环",
            "top_k": 5,
            "filters": {
                "category": "基础科学",
            },
        },
    )
    project_response = client.post(
        "/api/graphrag/search",
        json={
            "query": "水循环",
            "top_k": 5,
            "filters": {
                "project_id": "qinghe-2024",
            },
        },
    )

    assert category_response.status_code == 200
    category_payload = category_response.json()
    assert category_payload["total"] == 0
    assert category_payload["items"] == []

    assert project_response.status_code == 200
    project_payload = project_response.json()
    assert project_payload["total"] == 0
    assert project_payload["items"] == []


def test_graphrag_search_excludes_query_understanding_exclusions():
    response = client.post(
        "/api/graphrag/search",
        json={
            "query": "水循环展项，但不考虑数字投影",
            "top_k": 5,
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


def test_graphrag_answer_refuses_to_compose_without_citations(monkeypatch):
    from app.schemas import GraphResponse, GraphRagSearchHit, GraphRagSearchResponse
    from app.services import graphrag as graphrag_service

    def search_without_citations(query, exhibits, top_k=3, filters=None, semantic_scores=None, snapshot=None):
        return GraphRagSearchResponse(
            query=query,
            total=1,
            items=[
                GraphRagSearchHit(
                    exhibit=seed_exhibits[0],
                    score=1,
                    reasons=["候选展项与查询语义匹配"],
                    citations=[],
                    graph=GraphResponse(nodes=[], edges=[]),
                )
            ],
        )

    monkeypatch.setattr(graphrag_service, "search_graphrag_context", search_without_citations)

    response = client.post(
        "/api/graphrag/answer",
        json={"query": "适合儿童的机械互动展项", "top_k": 1},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["items"][0]["exhibit"]["id"] == seed_exhibits[0].id
    assert payload["citations"] == []
    assert "未找到依据" in payload["answer"]
    assert "可引用来源" in payload["answer"]
    assert "根据库内资料" not in payload["answer"]
    assert seed_exhibits[0].description not in payload["answer"]


def test_graphrag_answer_omits_uncited_candidates_from_grounded_answer(monkeypatch):
    from app.schemas import GraphResponse, GraphRagCitation, GraphRagSearchHit, GraphRagSearchResponse
    from app.services import graphrag as graphrag_service

    cited_exhibit = seed_exhibits[0]
    uncited_exhibit = seed_exhibits[1]
    citation = GraphRagCitation(
        source_id=cited_exhibit.id,
        source_type="exhibit",
        title=cited_exhibit.name,
        snippet="有来源的展项说明片段",
    )

    def search_with_mixed_citations(query, exhibits, top_k=3, filters=None, semantic_scores=None, snapshot=None):
        return GraphRagSearchResponse(
            query=query,
            total=2,
            items=[
                GraphRagSearchHit(
                    exhibit=cited_exhibit,
                    score=2,
                    reasons=["有引用命中"],
                    citations=[citation],
                    graph=GraphResponse(nodes=[], edges=[]),
                ),
                GraphRagSearchHit(
                    exhibit=uncited_exhibit,
                    score=1,
                    reasons=["候选但缺少引用"],
                    citations=[],
                    graph=GraphResponse(nodes=[], edges=[]),
                ),
            ],
        )

    monkeypatch.setattr(graphrag_service, "search_graphrag_context", search_with_mixed_citations)

    response = client.post(
        "/api/graphrag/answer",
        json={"query": "力学展项", "top_k": 2},
    )

    assert response.status_code == 200
    payload = response.json()
    assert [item["exhibit"]["id"] for item in payload["items"]] == [cited_exhibit.id, uncited_exhibit.id]
    assert payload["citations"]
    assert cited_exhibit.name in payload["answer"]
    assert uncited_exhibit.name not in payload["answer"]
    assert uncited_exhibit.description not in payload["answer"]
    assert "暂无可编号来源" not in payload["answer"]


def test_graphrag_answer_uses_rag_answerer_for_grounded_composition(monkeypatch):
    from app.ai.rag_answerer import RagAnswerResult
    from app.schemas import GraphResponse, GraphRagCitation, GraphRagSearchHit, GraphRagSearchResponse
    from app.services import graphrag as graphrag_service

    cited_exhibit = seed_exhibits[0]
    uncited_exhibit = seed_exhibits[1]
    citation = GraphRagCitation(
        source_id=cited_exhibit.id,
        source_type="exhibit",
        title=cited_exhibit.name,
        snippet="grounded source",
    )
    seen = {}

    def search_with_mixed_citations(query, exhibits, top_k=3, filters=None, semantic_scores=None, snapshot=None):
        return GraphRagSearchResponse(
            query=query,
            total=2,
            items=[
                GraphRagSearchHit(
                    exhibit=cited_exhibit,
                    score=2,
                    reasons=["grounded reason"],
                    citations=[citation],
                    graph=GraphResponse(nodes=[], edges=[]),
                ),
                GraphRagSearchHit(
                    exhibit=uncited_exhibit,
                    score=1,
                    reasons=["ungrounded reason"],
                    citations=[],
                    graph=GraphResponse(nodes=[], edges=[]),
                ),
            ],
        )

    def recording_answer_rag(inputs):
        seen["inputs"] = inputs
        return RagAnswerResult(
            answer="answerer composed text",
            used_citation_keys=[("exhibit", cited_exhibit.id)],
            refusal_reason=None,
            confidence=0.8,
            warnings=[],
        )

    monkeypatch.setattr(graphrag_service, "search_graphrag_context", search_with_mixed_citations)
    monkeypatch.setattr(graphrag_service, "answer_rag", recording_answer_rag)

    result = graphrag_service.answer_from_graphrag_context(
        "grounded query",
        seed_exhibits,
        top_k=2,
    )

    assert result.answer == "answerer composed text"
    assert result.citations == [citation]
    assert [item.exhibit.id for item in result.items] == [cited_exhibit.id, uncited_exhibit.id]
    assert [item.exhibit_id for item in seen["inputs"].matched_exhibits] == [cited_exhibit.id]
    assert seen["inputs"].matched_exhibits[0].reasons == ["grounded reason"]
    assert seen["inputs"].citations[0].source_id == cited_exhibit.id


def test_graphrag_answer_returns_only_citations_used_by_answerer(monkeypatch):
    from app.ai.rag_answerer import RagAnswerResult
    from app.schemas import GraphResponse, GraphRagCitation, GraphRagSearchHit, GraphRagSearchResponse
    from app.services import graphrag as graphrag_service

    cited_exhibit = seed_exhibits[0]
    used_citation = GraphRagCitation(
        source_id="used-doc",
        source_type="document",
        title="采用的资料",
        snippet="答案正文实际引用的资料片段",
    )
    unused_citation = GraphRagCitation(
        source_id="unused-doc",
        source_type="document",
        title="未采用的资料",
        snippet="检索命中但没有进入答案正文的资料片段",
    )

    def search_with_extra_citations(query, exhibits, top_k=3, filters=None, semantic_scores=None, snapshot=None):
        return GraphRagSearchResponse(
            query=query,
            total=1,
            items=[
                GraphRagSearchHit(
                    exhibit=cited_exhibit,
                    score=2,
                    reasons=["资料命中"],
                    citations=[used_citation, unused_citation],
                    graph=GraphResponse(nodes=[], edges=[]),
                )
            ],
        )

    def answer_using_one_citation(inputs):
        return RagAnswerResult(
            answer="只采用一个来源 [1]",
            used_citation_keys=[("document", "used-doc")],
            refusal_reason=None,
            confidence=0.8,
            warnings=[],
        )

    monkeypatch.setattr(graphrag_service, "search_graphrag_context", search_with_extra_citations)
    monkeypatch.setattr(graphrag_service, "answer_rag", answer_using_one_citation)

    result = graphrag_service.answer_from_graphrag_context(
        "引用收窄",
        seed_exhibits,
        top_k=1,
    )

    assert result.answer == "只采用一个来源 [1]"
    assert result.citations == [used_citation]
    assert result.items[0].citations == [used_citation, unused_citation]


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
