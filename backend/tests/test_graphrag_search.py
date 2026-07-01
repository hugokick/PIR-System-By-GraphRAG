from app.repository import seed_exhibits
from app.kg.builder import build_exhibit_kg_snapshot
from app.graphrag.search import GraphRAGFilters, search_graph_rag


def test_search_graph_rag_filters_before_scoring():
    snapshot = build_exhibit_kg_snapshot(seed_exhibits)

    response = search_graph_rag(
        query="力学",
        exhibits=seed_exhibits,
        snapshot=snapshot,
        filters=GraphRAGFilters(theme="力学", status="已落地"),
        top_k=5,
    )

    assert response.total == 1
    assert response.items[0].exhibit.id == "lever-play"


def test_search_graph_rag_returns_reasons_citations_and_neighborhood():
    snapshot = build_exhibit_kg_snapshot(seed_exhibits)

    response = search_graph_rag(
        query="杠杆乐园 启思互动工坊",
        exhibits=seed_exhibits,
        snapshot=snapshot,
        top_k=3,
    )

    assert response.items
    first = response.items[0]
    assert first.exhibit.id == "lever-play"
    assert first.score > 0
    assert first.reasons
    assert first.citations
    assert any(node.type == "project" for node in first.neighborhood.nodes)


def test_search_graph_rag_returns_empty_response_when_no_evidence():
    snapshot = build_exhibit_kg_snapshot(seed_exhibits)

    response = search_graph_rag(
        query="完全不存在的展项",
        exhibits=seed_exhibits,
        snapshot=snapshot,
        top_k=3,
    )

    assert response.total == 0
    assert response.items == []


def test_search_graph_rag_merges_semantic_and_rule_recall():
    response = search_graph_rag(
        query="液体城市系统",
        exhibits=seed_exhibits,
        semantic_scores={"water-cycle": 0.91},
        top_k=1,
    )

    assert response.items[0].exhibit.id == "water-cycle"
    assert any("向量召回" in reason for reason in response.items[0].reasons)


def test_search_graph_rag_prefers_document_evidence_when_query_hits_document_text():
    response = search_graph_rag(
        query="样例文档 来源链路",
        exhibits=seed_exhibits,
        filters=GraphRAGFilters(theme="力学"),
        top_k=1,
    )

    assert response.items[0].exhibit.id == "lever-play"
    assert response.items[0].citations
