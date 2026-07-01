import re
from collections.abc import Mapping

from app.ai.query_understanding import (
    AUDIENCE_LOW_AGE_CHILDREN,
    BUDGET_LOW,
    BUDGET_LOWER_THAN_REFERENCE,
    QueryUnderstandingResult,
    understand_query,
)
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
    semantic_scores: Mapping[str, float] | None = None,
) -> GraphRAGSearchResponse:
    active_snapshot = snapshot or build_exhibit_kg_snapshot(exhibits)
    understanding = understand_query(query)
    filtered = _apply_filters(exhibits, filters)
    reference_exhibit = _find_reference_exhibit(filtered, understanding)
    hits: list[GraphRAGHit] = []
    for exhibit in filtered:
        if reference_exhibit and exhibit.id == reference_exhibit.id:
            continue
        if _is_outside_reference_budget(understanding, exhibit, reference_exhibit):
            continue
        if _is_excluded_by_query_understanding(understanding, exhibit):
            continue
        if _is_outside_query_budget_range(understanding, exhibit):
            continue
        hit = _score_exhibit(
            query,
            exhibit,
            active_snapshot,
            understanding,
            reference_exhibit=reference_exhibit,
            semantic_score=(semantic_scores or {}).get(exhibit.id, 0.0),
        )
        if hit is not None:
            hits.append(hit)

    hits.sort(key=lambda item: (-item.score, item.exhibit.id))
    total = len(hits)
    items = hits[:top_k]
    return GraphRAGSearchResponse(query=query, total=total, items=items)


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
            category=filters.category,
            theme=filters.theme,
            project_id=filters.project_id,
            owner=filters.owner,
            supplier=filters.supplier,
            tag=filters.tag,
            material=filters.material,
            interaction=filters.interaction,
            status=filters.status,
            review_status=filters.review_status,
            budget_min=filters.budget_min,
            budget_max=filters.budget_max,
        )
    ]


def _score_exhibit(
    query: str,
    exhibit: ExhibitResponse,
    snapshot: KGSnapshot,
    understanding: QueryUnderstandingResult,
    reference_exhibit: ExhibitResponse | None = None,
    semantic_score: float = 0.0,
) -> GraphRAGHit | None:
    tokens = _query_tokens(query, understanding)
    fields = {
        "identity": [exhibit.id, exhibit.name],
        "classification": [exhibit.category, exhibit.theme.name, exhibit.venue_type, *exhibit.tags],
        "materials": [item.name for item in exhibit.materials],
        "interactions": [item.name for item in exhibit.interactions],
        "project": [exhibit.project.name, exhibit.owner.name, exhibit.supplier.name],
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

    document_score, document_reasons = _document_match_score(tokens, exhibit)
    if document_score:
        score += document_score
        reasons.extend(document_reasons)

    understanding_score, understanding_reasons = _query_understanding_score(
        understanding,
        exhibit,
        reference_exhibit,
    )
    if understanding_score:
        score += understanding_score
        reasons.extend(understanding_reasons)

    if semantic_score >= 0.2:
        score += semantic_score * 6
        reasons.append(f"向量召回：语义相似度 {semantic_score:.2f}")

    if score <= 0:
        return None

    exhibit_node_id = f"exhibit:{exhibit.id}"
    neighborhood = _one_hop_neighborhood(snapshot, exhibit_node_id)
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


def _one_hop_neighborhood(snapshot: KGSnapshot, center_id: str) -> KGSnapshot:
    neighbor_ids = {center_id, *snapshot.adjacency.get(center_id, [])}
    for edge in snapshot.edges:
        if edge.source == center_id:
            neighbor_ids.add(edge.target)
        if edge.target == center_id:
            neighbor_ids.add(edge.source)

    edges = [
        edge
        for edge in snapshot.edges
        if (
            (edge.source == center_id and edge.target in neighbor_ids)
            or (edge.target == center_id and edge.source in neighbor_ids)
        )
    ]
    return KGSnapshot(
        nodes=[node for node in snapshot.nodes if node.id in neighbor_ids],
        edges=_dedupe_edges(edges),
        evidences=[],
        adjacency={center_id: [node_id for node_id in neighbor_ids if node_id != center_id]},
        warnings=[],
    )


def _query_tokens(query: str, understanding: QueryUnderstandingResult | None = None) -> list[str]:
    normalized = query.strip().lower()
    if not normalized:
        return []
    for separator in ",，、|":
        normalized = normalized.replace(separator, " ")
    tokens = [token for token in normalized.split() if token]
    if understanding is None:
        return tokens
    tokens.extend(
        [
            *understanding.themes,
            *understanding.venue_types,
            *understanding.materials,
            *understanding.interactions,
            *understanding.tags,
            understanding.project_case or "",
        ]
    )
    return _dedupe_tokens(tokens)


def _query_understanding_score(
    understanding: QueryUnderstandingResult,
    exhibit: ExhibitResponse,
    reference_exhibit: ExhibitResponse | None = None,
) -> tuple[float, list[str]]:
    if understanding.confidence < 0.4:
        return 0.0, []

    score = 0.0
    reasons: list[str] = []
    if understanding.themes and exhibit.theme.name in understanding.themes:
        score += 3.0
        reasons.append(f"查询理解：主题 {exhibit.theme.name}")
    if understanding.venue_types and exhibit.venue_type in understanding.venue_types:
        score += 2.0
        reasons.append(f"查询理解：场馆 {exhibit.venue_type}")
    matched_materials = [
        material.name for material in exhibit.materials if material.name in understanding.materials
    ]
    if matched_materials:
        score += len(matched_materials) * 1.5
        reasons.append(f"查询理解：材料 {'、'.join(matched_materials)}")
    matched_interactions = [
        interaction.name
        for interaction in exhibit.interactions
        if interaction.name in understanding.interactions
    ]
    if matched_interactions:
        score += len(matched_interactions) * 1.5
        reasons.append(f"查询理解：互动 {'、'.join(matched_interactions)}")
    if AUDIENCE_LOW_AGE_CHILDREN in understanding.audience and _exhibit_has_low_age_signal(exhibit):
        score += 2.0
        reasons.append("查询理解：人群 low_age_children")
    if understanding.budget_intent == BUDGET_LOW and exhibit.budget_max <= 300000:
        score += 2.5
        reasons.append("查询理解：预算倾向 low")
    elif _exhibit_has_lower_budget_than_reference(understanding, exhibit, reference_exhibit):
        score += 2.5
        reasons.append(f"查询理解：预算低于参照案例 {reference_exhibit.name}")
    elif understanding.budget_intent == BUDGET_LOWER_THAN_REFERENCE and exhibit.budget_max <= 300000:
        score += 1.5
        reasons.append("查询理解：预算倾向 lower_than_reference")
    if _should_score_budget_range(understanding, exhibit):
        score += 2.0
        reasons.append(f"查询理解：预算区间 {_format_query_budget_range(understanding)}")
    matched_tags = [tag for tag in exhibit.tags if tag in understanding.tags]
    if matched_tags:
        score += len(matched_tags)
        reasons.append(f"查询理解：标签 {'、'.join(matched_tags)}")
    return score, reasons


def _is_excluded_by_query_understanding(
    understanding: QueryUnderstandingResult,
    exhibit: ExhibitResponse,
) -> bool:
    return bool(
        understanding.exclusions
        and _exhibit_matches_exclusions(exhibit, understanding.exclusions)
    )


def _is_outside_query_budget_range(
    understanding: QueryUnderstandingResult,
    exhibit: ExhibitResponse,
) -> bool:
    return _has_budget_range(understanding) and not _exhibit_matches_budget_range(exhibit, understanding)


def _is_outside_reference_budget(
    understanding: QueryUnderstandingResult,
    exhibit: ExhibitResponse,
    reference_exhibit: ExhibitResponse | None,
) -> bool:
    return (
        understanding.budget_intent == BUDGET_LOWER_THAN_REFERENCE
        and reference_exhibit is not None
        and not _exhibit_has_lower_budget_than_reference(understanding, exhibit, reference_exhibit)
    )


def _document_match_score(tokens: list[str], exhibit: ExhibitResponse) -> tuple[float, list[str]]:
    score = 0.0
    reasons: list[str] = []
    for document in exhibit.documents:
        values = [
            document.name,
            document.source_note or "",
            *[chunk.text for chunk in document.chunks],
        ]
        joined = " ".join(value for value in values if value).lower()
        matched = {token for token in tokens if token in joined}
        if not matched:
            continue
        score += len(matched) * 2.0
        reasons.append(f"匹配资料：{document.name}")
    return score, reasons


def _exhibit_has_low_age_signal(exhibit: ExhibitResponse) -> bool:
    joined = " ".join(
        [
            exhibit.venue_type,
            exhibit.description,
            *exhibit.tags,
            *[interaction.name for interaction in exhibit.interactions],
        ]
    )
    return any(signal in joined for signal in ("低龄儿童", "低龄", "儿童", "亲子"))


def _exhibit_has_lower_budget_than_reference(
    understanding: QueryUnderstandingResult,
    exhibit: ExhibitResponse,
    reference_exhibit: ExhibitResponse | None,
) -> bool:
    return bool(
        understanding.budget_intent == BUDGET_LOWER_THAN_REFERENCE
        and reference_exhibit is not None
        and exhibit.budget_max < reference_exhibit.budget_min
    )


def _has_budget_range(understanding: QueryUnderstandingResult) -> bool:
    return understanding.budget_min is not None or understanding.budget_max is not None


def _exhibit_matches_budget_range(
    exhibit: ExhibitResponse,
    understanding: QueryUnderstandingResult,
) -> bool:
    if understanding.budget_min is not None and exhibit.budget_max < understanding.budget_min:
        return False
    if understanding.budget_max is not None and exhibit.budget_min > understanding.budget_max:
        return False
    return True


def _format_query_budget_range(understanding: QueryUnderstandingResult) -> str:
    if understanding.budget_min is not None and understanding.budget_max is not None:
        return f"{_format_budget(understanding.budget_min)}-{_format_budget(understanding.budget_max)}"
    if understanding.budget_max is not None:
        return f"{_format_budget(understanding.budget_max)}以内"
    if understanding.budget_min is not None:
        return f"{_format_budget(understanding.budget_min)}以上"
    return "未指定"


def _should_score_budget_range(
    understanding: QueryUnderstandingResult,
    exhibit: ExhibitResponse,
) -> bool:
    return (
        _has_budget_range(understanding)
        and _exhibit_matches_budget_range(exhibit, understanding)
        and (
            not _has_non_budget_understanding(understanding)
            or _exhibit_matches_non_budget_understanding(exhibit, understanding)
        )
    )


def _has_non_budget_understanding(understanding: QueryUnderstandingResult) -> bool:
    return bool(
        understanding.themes
        or understanding.venue_types
        or understanding.audience
        or understanding.materials
        or understanding.interactions
        or understanding.tags
    )


def _exhibit_matches_non_budget_understanding(
    exhibit: ExhibitResponse,
    understanding: QueryUnderstandingResult,
) -> bool:
    return any(
        [
            bool(understanding.themes and exhibit.theme.name in understanding.themes),
            bool(understanding.venue_types and exhibit.venue_type in understanding.venue_types),
            bool(
                understanding.materials
                and any(material.name in understanding.materials for material in exhibit.materials)
            ),
            bool(
                understanding.interactions
                and any(interaction.name in understanding.interactions for interaction in exhibit.interactions)
            ),
            bool(AUDIENCE_LOW_AGE_CHILDREN in understanding.audience and _exhibit_has_low_age_signal(exhibit)),
            bool(understanding.tags and any(tag in understanding.tags for tag in exhibit.tags)),
        ]
    )


def _exhibit_matches_exclusions(exhibit: ExhibitResponse, exclusions: list[str]) -> bool:
    joined = " ".join(
        [
            exhibit.name,
            exhibit.category,
            exhibit.theme.name,
            exhibit.venue_type,
            exhibit.description,
            exhibit.owner.name,
            exhibit.supplier.name,
            *exhibit.tags,
            *[material.name for material in exhibit.materials],
            *[interaction.name for interaction in exhibit.interactions],
        ]
    )
    return any(exclusion in joined for exclusion in exclusions)


def _find_reference_exhibit(
    exhibits: list[ExhibitResponse],
    understanding: QueryUnderstandingResult,
) -> ExhibitResponse | None:
    if not understanding.project_case:
        return None

    needle = _compact(understanding.project_case)
    if not needle:
        return None

    for exhibit in exhibits:
        values = [
            exhibit.id,
            exhibit.name,
            exhibit.description,
            exhibit.project.name,
            exhibit.theme.name,
            *exhibit.tags,
        ]
        if any(needle in _compact(value) for value in values if value):
            return exhibit
    return None


def _format_budget(value: int) -> str:
    if value % 10000 == 0:
        return f"{value // 10000} 万"
    return f"{value / 10000:.1f} 万"


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


def _dedupe_edges(edges):
    seen: set[str] = set()
    unique = []
    for edge in edges:
        key = f"{edge.source}|{edge.type}|{edge.target}"
        if key in seen:
            continue
        seen.add(key)
        unique.append(edge)
    return unique


def _dedupe_tokens(tokens: list[str]) -> list[str]:
    unique: list[str] = []
    seen: set[str] = set()
    for token in tokens:
        token = token.strip().lower()
        if not token or token in seen:
            continue
        seen.add(token)
        unique.append(token)
    return unique


def _compact(value: str) -> str:
    return re.sub(r"[\s,，、。；;:：|/\\-]+", "", value.strip().lower())
