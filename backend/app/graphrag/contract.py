from collections.abc import Mapping

from pydantic import BaseModel, Field

from app.kg.builder import build_exhibit_kg_snapshot
from app.kg.models import KGEdge, KGEvidence, KGNode, KGSnapshot
from app.repository import ExhibitRepository
from app.schemas import ExhibitResponse

from .models import GraphRAGFilters
from .search import search_graph_rag


class GraphRAGContractFilters(BaseModel):
    theme: str | None = None
    material: str | None = None
    interaction: str | None = None
    venue_type: str | None = None
    status: str | None = None
    review_status: str | None = None
    budget_min: int | None = None
    budget_max: int | None = None


class KGSubgraphQueryInput(BaseModel):
    exhibit_id: str


class GraphRAGContractQueryInput(BaseModel):
    query_text: str
    top_k: int = Field(default=5, ge=1)
    filters: GraphRAGContractFilters | None = None


class MatchedExhibit(BaseModel):
    exhibit: ExhibitResponse
    score: float


class GraphContext(BaseModel):
    nodes: list[KGNode] = Field(default_factory=list)
    edges: list[KGEdge] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ContractCitation(BaseModel):
    evidence_id: str
    source_type: str
    source_id: str
    title: str
    snippet: str


class ReasoningSignal(BaseModel):
    exhibit_id: str
    signal_type: str
    detail: str
    score: float


class KGGraphRAGQueryResult(BaseModel):
    matched_exhibits: list[MatchedExhibit] = Field(default_factory=list)
    total_matches: int = 0
    graph_context: GraphContext = Field(default_factory=GraphContext)
    citations: list[ContractCitation] = Field(default_factory=list)
    reasoning_signals: list[ReasoningSignal] = Field(default_factory=list)
    source_nodes: list[KGNode] = Field(default_factory=list)
    source_edges: list[KGEdge] = Field(default_factory=list)


def query_subgraph_by_exhibit_id(
    query: KGSubgraphQueryInput,
    exhibits: list[ExhibitResponse],
    snapshot: KGSnapshot | None = None,
) -> KGGraphRAGQueryResult:
    active_snapshot = snapshot or build_exhibit_kg_snapshot(exhibits)
    exhibit = next((item for item in exhibits if item.id == query.exhibit_id), None)
    if exhibit is None:
        return KGGraphRAGQueryResult(
            graph_context=GraphContext(warnings=[f"Missing exhibit: {query.exhibit_id}"])
        )

    center_id = f"exhibit:{query.exhibit_id}"
    nodes, edges = _center_subgraph(active_snapshot, center_id)
    citations = _contract_citations(
        [evidence for evidence in active_snapshot.evidences if center_id in evidence.linked_node_ids]
    )
    return KGGraphRAGQueryResult(
        matched_exhibits=[MatchedExhibit(exhibit=exhibit, score=1.0)],
        total_matches=1,
        graph_context=GraphContext(nodes=nodes, edges=edges, warnings=list(active_snapshot.warnings)),
        citations=citations,
        reasoning_signals=[
            ReasoningSignal(
                exhibit_id=exhibit.id,
                signal_type="center_subgraph",
                detail="matched exhibit_id center lookup",
                score=1.0,
            )
        ],
        source_nodes=nodes,
        source_edges=edges,
    )


def query_graphrag_contract(
    query: GraphRAGContractQueryInput,
    exhibits: list[ExhibitResponse],
    snapshot: KGSnapshot | None = None,
    semantic_scores: Mapping[str, float] | None = None,
) -> KGGraphRAGQueryResult:
    active_snapshot = snapshot or build_exhibit_kg_snapshot(exhibits)
    filtered_exhibits = _apply_contract_filters(exhibits, query.filters)
    search_response = search_graph_rag(
        query=query.query_text,
        exhibits=filtered_exhibits,
        snapshot=active_snapshot,
        filters=_search_filters(query.filters),
        top_k=query.top_k,
        semantic_scores=semantic_scores,
    )
    matched_exhibits = [
        MatchedExhibit(exhibit=item.exhibit, score=item.score) for item in search_response.items
    ]
    graph_nodes = _dedupe_by_id(
        [node for item in search_response.items for node in item.neighborhood.nodes],
        key=lambda node: node.id,
    )
    graph_edges = _dedupe_by_id(
        [edge for item in search_response.items for edge in item.neighborhood.edges],
        key=lambda edge: f"{edge.source}|{edge.type}|{edge.target}",
    )
    citations = _contract_citations(
        [citation for item in search_response.items for citation in item.citations]
    )
    reasoning_signals = [
        ReasoningSignal(
            exhibit_id=item.exhibit.id,
            signal_type="semantic_recall" if reason.startswith("向量召回") else "rule_match",
            detail=reason,
            score=item.score,
        )
        for item in search_response.items
        for reason in item.reasons
    ]
    return KGGraphRAGQueryResult(
        matched_exhibits=matched_exhibits,
        total_matches=search_response.total,
        graph_context=GraphContext(
            nodes=graph_nodes,
            edges=graph_edges,
            warnings=list(active_snapshot.warnings),
        ),
        citations=citations,
        reasoning_signals=reasoning_signals,
        source_nodes=graph_nodes,
        source_edges=graph_edges,
    )


def _apply_contract_filters(
    exhibits: list[ExhibitResponse],
    filters: GraphRAGContractFilters | None,
) -> list[ExhibitResponse]:
    if filters is None:
        return exhibits

    matcher = ExhibitRepository([])
    return [
        exhibit
        for exhibit in exhibits
        if matcher._matches(
            exhibit,
            keyword=None,
            venue_type=filters.venue_type,
            category=None,
            theme=filters.theme,
            project_id=None,
            material=filters.material,
            interaction=filters.interaction,
            status=filters.status,
            review_status=filters.review_status,
            budget_min=filters.budget_min,
            budget_max=filters.budget_max,
        )
    ]


def _search_filters(filters: GraphRAGContractFilters | None) -> GraphRAGFilters | None:
    if filters is None:
        return None
    return GraphRAGFilters(
        theme=filters.theme,
        material=filters.material,
        interaction=filters.interaction,
        venue_type=filters.venue_type,
        status=filters.status,
        review_status=filters.review_status,
        budget_min=filters.budget_min,
        budget_max=filters.budget_max,
    )


def _center_subgraph(snapshot: KGSnapshot, center_id: str) -> tuple[list[KGNode], list[KGEdge]]:
    neighbor_ids = [center_id, *snapshot.adjacency.get(center_id, [])]
    nodes = [node for node in snapshot.nodes if node.id in neighbor_ids]
    edges = [
        edge
        for edge in snapshot.edges
        if edge.source == center_id and edge.target in neighbor_ids
    ]
    return nodes, edges


def _contract_citations(evidences: list[KGEvidence]) -> list[ContractCitation]:
    unique = _dedupe_by_id(
        evidences,
        key=lambda evidence: f"{evidence.source_type}|{evidence.source_id}",
    )
    return [
        ContractCitation(
            evidence_id=evidence.evidence_id,
            source_type=evidence.source_type,
            source_id=evidence.source_id,
            title=evidence.title,
            snippet=evidence.snippet,
        )
        for evidence in unique
    ]


def _dedupe_by_id(items: list, key):
    seen: set[str] = set()
    unique = []
    for item in items:
        item_key = key(item)
        if item_key in seen:
            continue
        seen.add(item_key)
        unique.append(item)
    return unique
