from app.graphrag.contract import (
    GraphRAGContractFilters,
    GraphRAGContractQueryInput,
    KGGraphRAGQueryResult,
    query_graphrag_contract,
)
from app.schemas import (
    ExhibitResponse,
    GraphEdge,
    GraphNode,
    GraphRagAnswerResponse,
    GraphRagCitation,
    GraphRagRequestFilters,
    GraphRagSearchHit,
    GraphRagSearchResponse,
    GraphResponse,
)


def search_graphrag_context(
    query: str,
    exhibits: list[ExhibitResponse],
    top_k: int = 5,
    filters: GraphRagRequestFilters | None = None,
) -> GraphRagSearchResponse:
    contract_result = query_graphrag_contract(
        GraphRAGContractQueryInput(
            query_text=query,
            top_k=top_k,
            filters=_contract_filters(filters),
        ),
        exhibits=exhibits,
    )
    return _contract_to_search_response(query, contract_result)


def answer_from_graphrag_context(
    query: str,
    exhibits: list[ExhibitResponse],
    top_k: int = 3,
    filters: GraphRagRequestFilters | None = None,
) -> GraphRagAnswerResponse:
    search_response = search_graphrag_context(query, exhibits, top_k=top_k, filters=filters)

    if not search_response.items:
        return GraphRagAnswerResponse(
            query=query,
            answer=f"No evidence found in the exhibit library for: {query}",
            citations=[],
            items=[],
        )

    summaries = [
        f"{item.exhibit.id}: {item.exhibit.name} ({'; '.join(item.reasons)})"
        for item in search_response.items
    ]
    answer = (
        "Based on exhibit records and graph context, the strongest matches are "
        + " | ".join(summaries)
        + "."
    )
    return GraphRagAnswerResponse(
        query=query,
        answer=answer,
        citations=_deduplicate_citations(
            citation
            for item in search_response.items
            for citation in item.citations
        ),
        items=search_response.items,
    )


def _contract_filters(filters: GraphRagRequestFilters | None) -> GraphRAGContractFilters | None:
    if filters is None:
        return None
    return GraphRAGContractFilters(**filters.model_dump())


def _contract_to_search_response(query: str, result: KGGraphRAGQueryResult) -> GraphRagSearchResponse:
    items = [
        GraphRagSearchHit(
            exhibit=match.exhibit,
            score=match.score,
            reasons=[
                signal.detail
                for signal in result.reasoning_signals
                if signal.exhibit_id == match.exhibit.id
            ],
            citations=[
                _citation_to_api(citation)
                for citation in result.citations
                if _citation_belongs_to_exhibit(citation, match.exhibit.id, result)
            ],
            graph=_graph_for_exhibit(match.exhibit.id, result),
        )
        for match in result.matched_exhibits
    ]
    return GraphRagSearchResponse(query=query, total=len(items), items=items)


def _graph_for_exhibit(exhibit_id: str, result: KGGraphRAGQueryResult) -> GraphResponse:
    center_id = f"exhibit:{exhibit_id}"
    edges = [
        edge
        for edge in result.graph_context.edges
        if edge.source == center_id or edge.target == center_id
    ]
    node_ids = {center_id, *[edge.source for edge in edges], *[edge.target for edge in edges]}
    nodes = [node for node in result.graph_context.nodes if node.id in node_ids]
    return GraphResponse(
        nodes=[GraphNode(id=node.id, label=node.label, type=node.type) for node in nodes],
        edges=[
            GraphEdge(source=edge.source, target=edge.target, label=edge.label, type=edge.type)
            for edge in edges
        ],
    )


def _citation_to_api(citation) -> GraphRagCitation:
    return GraphRagCitation(
        source_id=citation.source_id,
        source_type=citation.source_type,
        title=citation.title,
        snippet=citation.snippet,
    )


def _citation_belongs_to_exhibit(citation, exhibit_id: str, result: KGGraphRAGQueryResult) -> bool:
    if citation.source_type == "exhibit":
        return citation.source_id == exhibit_id
    if citation.source_type != "document":
        return False

    center_id = f"exhibit:{exhibit_id}"
    document_id = f"document:{citation.source_id}"
    return any(
        edge.source == center_id and edge.target == document_id and edge.type == "has_document"
        for edge in result.graph_context.edges
    )


def _deduplicate_citations(citations) -> list[GraphRagCitation]:
    seen: set[tuple[str, str]] = set()
    unique: list[GraphRagCitation] = []
    for citation in citations:
        key = (citation.source_type, citation.source_id)
        if key in seen:
            continue
        seen.add(key)
        unique.append(citation)
    return unique
