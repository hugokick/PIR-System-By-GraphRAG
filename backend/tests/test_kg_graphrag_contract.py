from app.graphrag.contract import (
    GraphRAGContractFilters,
    GraphRAGContractQueryInput,
    KGGraphRAGQueryResult,
    KGSubgraphQueryInput,
    query_graphrag_contract,
    query_subgraph_by_exhibit_id,
)
from app.ai.query_understanding import TAG_SIGNALS, THEME_SIGNALS
from app.kg.models import KGEdge, KGNode, KGSnapshot
from app.repository import seed_exhibits


def test_query_subgraph_by_exhibit_id_returns_center_neighborhood():
    result = query_subgraph_by_exhibit_id(
        KGSubgraphQueryInput(exhibit_id="lever-play"),
        exhibits=seed_exhibits,
    )

    node_ids = {node.id for node in result.graph_context.nodes}
    assert isinstance(result, KGGraphRAGQueryResult)
    assert result.matched_exhibits[0].exhibit.id == "lever-play"
    assert "exhibit:lever-play" in node_ids
    assert any(node.type == "project" for node in result.graph_context.nodes)
    assert result.source_nodes
    assert result.source_edges
    assert result.citations


def test_query_subgraph_by_exhibit_id_includes_deduped_incoming_edges():
    center_id = "exhibit:lever-play"
    owner_id = "owner:qinghe"
    snapshot = KGSnapshot(
        nodes=[
            KGNode(id=center_id, type="exhibit", label="杠杆乐园"),
            KGNode(id=owner_id, type="owner", label="青禾科技馆"),
        ],
        edges=[
            KGEdge(source=owner_id, target=center_id, type="owned_by", label="业主"),
            KGEdge(source=owner_id, target=center_id, type="owned_by", label="业主"),
        ],
        evidences=[],
        adjacency={owner_id: [center_id]},
        warnings=[],
    )

    result = query_subgraph_by_exhibit_id(
        KGSubgraphQueryInput(exhibit_id="lever-play"),
        exhibits=seed_exhibits,
        snapshot=snapshot,
    )

    assert {node.id for node in result.graph_context.nodes} == {center_id, owner_id}
    assert [
        (edge.source, edge.type, edge.target)
        for edge in result.graph_context.edges
    ] == [(owner_id, "owned_by", center_id)]


def test_query_graphrag_contract_returns_candidates_citations_and_signals():
    result = query_graphrag_contract(
        GraphRAGContractQueryInput(
            query_text="力学 启思互动工坊",
            top_k=2,
            filters=GraphRAGContractFilters(theme="力学", budget_min=100000, budget_max=400000),
        ),
        exhibits=seed_exhibits,
    )

    assert isinstance(result, KGGraphRAGQueryResult)
    assert len(result.matched_exhibits) == 2
    assert result.matched_exhibits[0].exhibit.id in {"lever-play", "pulley-wall"}
    assert result.citations
    assert result.reasoning_signals
    assert any(signal.exhibit_id == result.matched_exhibits[0].exhibit.id for signal in result.reasoning_signals)
    assert any(
        signal.signal_type == "graph_neighbor_match"
        and signal.detail.startswith("匹配项目/业主/供应商")
        for signal in result.reasoning_signals
    )


def test_query_graphrag_contract_can_use_vector_semantic_scores_as_recall_signal():
    result = query_graphrag_contract(
        GraphRAGContractQueryInput(query_text="液体城市系统", top_k=1),
        exhibits=seed_exhibits,
        semantic_scores={"water-cycle": 0.91},
    )

    assert result.matched_exhibits[0].exhibit.id == "water-cycle"
    assert result.matched_exhibits[0].score > 0
    assert any(
        signal.exhibit_id == "water-cycle"
        and signal.signal_type == "semantic_recall"
        and "向量召回" in signal.detail
        for signal in result.reasoning_signals
    )
    assert result.citations


def test_query_graphrag_contract_labels_document_reasoning_signals():
    result = query_graphrag_contract(
        GraphRAGContractQueryInput(query_text="样例文档 来源链路", top_k=1),
        exhibits=seed_exhibits,
    )

    assert result.matched_exhibits[0].exhibit.id == "lever-play"
    assert any(
        signal.exhibit_id == "lever-play"
        and signal.signal_type == "document_chunk_match"
        for signal in result.reasoning_signals
    )


def test_query_graphrag_contract_labels_query_understanding_signals():
    result = query_graphrag_contract(
        GraphRAGContractQueryInput(
            query_text=f"{THEME_SIGNALS[0]} {TAG_SIGNALS[-1]}",
            top_k=2,
        ),
        exhibits=seed_exhibits,
    )

    assert any(
        signal.exhibit_id in {"lever-play", "pulley-wall"}
        and signal.signal_type == "query_understanding"
        for signal in result.reasoning_signals
    )


def test_contract_queries_are_pure_models_not_fastapi_route_responses():
    subgraph_result = query_subgraph_by_exhibit_id(
        KGSubgraphQueryInput(exhibit_id="lever-play"),
        exhibits=seed_exhibits,
    )
    search_result = query_graphrag_contract(
        GraphRAGContractQueryInput(query_text="水循环", top_k=1),
        exhibits=seed_exhibits,
    )

    assert not hasattr(subgraph_result, "status_code")
    assert not hasattr(search_result, "status_code")
    assert "matched_exhibits" in search_result.model_dump()
