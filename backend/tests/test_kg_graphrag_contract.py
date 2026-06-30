from app.graphrag.contract import (
    GraphRAGContractFilters,
    GraphRAGContractQueryInput,
    KGGraphRAGQueryResult,
    KGSubgraphQueryInput,
    query_graphrag_contract,
    query_subgraph_by_exhibit_id,
)
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
