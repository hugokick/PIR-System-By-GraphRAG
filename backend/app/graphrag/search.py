from app.kg.builder import build_exhibit_kg_snapshot
from app.kg.models import KGEvidence, KGSnapshot
from app.repository import ExhibitRepository
from app.schemas import ExhibitResponse

from .models import GraphRAGFilters, GraphRAGHit, GraphRAGSearchResponse


def search_graph_rag(
    query: str,
    exhibits: list[ExhibitResponse],
    snapshot: KGSnapshot | None = None,
    filters: GraphRAGFilters | None = None,
    top_k: int = 5,
) -> GraphRAGSearchResponse:
    active_snapshot = snapshot or build_exhibit_kg_snapshot(exhibits)
    filtered = _apply_filters(exhibits, filters)
    hits = [
        hit for exhibit in filtered if (hit := _score_exhibit(query, exhibit, active_snapshot)) is not None
    ]
    hits.sort(key=lambda item: (-item.score, item.exhibit.id))
    items = hits[:top_k]
    return GraphRAGSearchResponse(query=query, total=len(items), items=items)


def _apply_filters(
    exhibits: list[ExhibitResponse],
    filters: GraphRAGFilters | None,
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
            material=filters.material,
            interaction=filters.interaction,
            status=filters.status,
            budget_min=None,
            budget_max=None,
        )
    ]


def _score_exhibit(
    query: str,
    exhibit: ExhibitResponse,
    snapshot: KGSnapshot,
) -> GraphRAGHit | None:
    tokens = _query_tokens(query)
    fields = {
        "identity": [exhibit.id, exhibit.name],
        "classification": [exhibit.category, exhibit.theme.name, exhibit.venue_type, *exhibit.tags],
        "materials": [item.name for item in exhibit.materials],
        "interactions": [item.name for item in exhibit.interactions],
        "project": [exhibit.project.name, exhibit.owner.name, exhibit.supplier.name],
        "documents": [
            value
            for document in exhibit.documents
            for value in [document.name, document.source_note or ""]
            if value
        ],
        "description": [exhibit.description],
    }
    weights = {
        "identity": 4.0,
        "classification": 3.0,
        "materials": 2.0,
        "interactions": 2.0,
        "project": 2.0,
        "documents": 2.0,
        "description": 1.0,
    }

    score = 0.0
    reasons: list[str] = []
    for label, values in fields.items():
        joined = " ".join(values).lower()
        matched = [token for token in tokens if token in joined]
        if matched:
            score += len(set(matched)) * weights[label]
            reasons.append(f"matched {label}")

    if score <= 0:
        return None

    exhibit_node_id = f"exhibit:{exhibit.id}"
    neighbor_ids = [exhibit_node_id, *snapshot.adjacency.get(exhibit_node_id, [])]
    neighborhood = KGSnapshot(
        nodes=[node for node in snapshot.nodes if node.id in neighbor_ids],
        edges=[
            edge
            for edge in snapshot.edges
            if edge.source == exhibit_node_id and edge.target in neighbor_ids
        ],
        evidences=[],
        adjacency={exhibit_node_id: snapshot.adjacency.get(exhibit_node_id, [])},
        warnings=[],
    )
    citations = _dedupe_citations(
        [
            evidence
            for evidence in snapshot.evidences
            if exhibit_node_id in evidence.linked_node_ids
        ]
    )
    return GraphRAGHit(
        exhibit=exhibit,
        score=score,
        reasons=reasons,
        citations=citations,
        neighborhood=neighborhood,
    )


def _query_tokens(query: str) -> list[str]:
    normalized = query.strip().lower()
    if not normalized:
        return []
    for separator in ",，、|":
        normalized = normalized.replace(separator, " ")
    return [token for token in normalized.split() if token]


def _dedupe_citations(evidences: list[KGEvidence]) -> list[KGEvidence]:
    seen: set[tuple[str, str]] = set()
    unique: list[KGEvidence] = []
    for evidence in evidences:
        key = (evidence.source_type, evidence.source_id)
        if key in seen:
            continue
        seen.add(key)
        unique.append(evidence)
    return unique
