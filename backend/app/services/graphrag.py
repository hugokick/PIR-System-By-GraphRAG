from collections.abc import Mapping

from app.graphrag.contract import (
    GraphRAGContractFilters,
    GraphRAGContractQueryInput,
    KGGraphRAGQueryResult,
    query_graphrag_contract,
)
from app.kg.models import KGSnapshot
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
    semantic_scores: Mapping[str, float] | None = None,
    snapshot: KGSnapshot | None = None,
) -> GraphRagSearchResponse:
    contract_result = query_graphrag_contract(
        GraphRAGContractQueryInput(
            query_text=query,
            top_k=top_k,
            filters=_contract_filters(filters),
        ),
        exhibits=exhibits,
        snapshot=snapshot,
        semantic_scores=semantic_scores,
    )
    return _contract_to_search_response(query, contract_result)


def answer_from_graphrag_context(
    query: str,
    exhibits: list[ExhibitResponse],
    top_k: int = 3,
    filters: GraphRagRequestFilters | None = None,
    semantic_scores: Mapping[str, float] | None = None,
    snapshot: KGSnapshot | None = None,
) -> GraphRagAnswerResponse:
    search_response = search_graphrag_context(
        query,
        exhibits,
        top_k=top_k,
        filters=filters,
        semantic_scores=semantic_scores,
        snapshot=snapshot,
    )

    if not search_response.items:
        return GraphRagAnswerResponse(
            query=query,
            answer=f"未找到依据：库内资料暂未命中“{query}”。请补充展项档案、上传资料，或调整筛选条件后重试。",
            citations=[],
            items=[],
        )

    citations = _deduplicate_citations(
        citation
        for item in search_response.items
        for citation in item.citations
    )
    if not citations:
        return GraphRagAnswerResponse(
            query=query,
            answer=(
                f"未找到依据：库内资料命中了候选展项，但没有可引用来源支撑“{query}”。"
                "请补充展项档案、上传资料，或调整筛选条件后重试。"
            ),
            citations=[],
            items=search_response.items,
        )

    grounded_items = [item for item in search_response.items if item.citations]
    answer = _compose_grounded_answer(query, grounded_items, citations)
    return GraphRagAnswerResponse(
        query=query,
        answer=answer,
        citations=citations,
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
    return GraphRagSearchResponse(query=query, total=result.total_matches, items=items)


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


def _compose_grounded_answer(
    query: str,
    items: list[GraphRagSearchHit],
    citations: list[GraphRagCitation],
) -> str:
    citation_numbers = {
        (citation.source_type, citation.source_id): index + 1
        for index, citation in enumerate(citations)
    }
    lines = [f"根据库内资料，针对“{query}”找到 {len(items)} 个相关展项："]

    for index, item in enumerate(items, start=1):
        reference = _first_reference_marker(item.citations, citation_numbers)
        reason = "、".join(item.reasons) if item.reasons else "与查询文本和图谱关系匹配"
        lines.append(
            f"{index}. {item.exhibit.name}（{item.exhibit.id}）：{item.exhibit.description}"
            f" 匹配依据：{reason}。{reference}"
        )

    if citations:
        source_summaries = [
            _citation_source_summary(index, citation)
            for index, citation in enumerate(citations, start=1)
        ]
        lines.append("来源：" + "；".join(source_summaries))
    else:
        lines.append("当前命中结果缺少可引用来源，请补充展项资料后再生成正式答复。")

    return "\n".join(lines)


def _citation_source_summary(index: int, citation: GraphRagCitation) -> str:
    snippet = citation.snippet.strip()
    if len(snippet) > 90:
        snippet = f"{snippet[:87]}..."
    return f"[{index}] {citation.title}：{snippet}"


def _first_reference_marker(
    citations: list[GraphRagCitation],
    citation_numbers: dict[tuple[str, str], int],
) -> str:
    for citation in citations:
        number = citation_numbers.get((citation.source_type, citation.source_id))
        if number is not None:
            return f"依据 [{number}]。"
    return "暂无可编号来源。"
