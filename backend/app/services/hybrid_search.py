import re
from collections.abc import Mapping

from app.ai.query_understanding import (
    AUDIENCE_LOW_AGE_CHILDREN,
    BUDGET_LOW,
    BUDGET_LOWER_THAN_REFERENCE,
    QueryUnderstandingResult,
    understand_query,
)
from app.repository import ExhibitRepository
from app.schemas import (
    ExhibitResponse,
    HybridSearchFilters,
    HybridSearchHit,
    HybridSearchResponse,
)


SEMANTIC_RECALL_THRESHOLD = 0.2


def search_hybrid_exhibits(
    query: str,
    exhibits: list[ExhibitResponse],
    *,
    limit: int = 5,
    filters: HybridSearchFilters | None = None,
    semantic_scores: Mapping[str, float] | None = None,
) -> HybridSearchResponse:
    filtered = _apply_filters(exhibits, filters)
    understanding = understand_query(query)
    reference_exhibit = _find_reference_exhibit(filtered, understanding)
    hits: list[tuple[int, HybridSearchHit]] = []

    for index, exhibit in enumerate(filtered):
        if reference_exhibit and exhibit.id == reference_exhibit.id:
            continue
        if _is_outside_reference_budget(understanding, exhibit, reference_exhibit):
            continue
        if _is_excluded_by_query_understanding(understanding, exhibit):
            continue
        if _is_outside_query_budget_range(understanding, exhibit):
            continue
        score, reasons = _score_exhibit(query, exhibit, filters, understanding, reference_exhibit)
        semantic_score = (semantic_scores or {}).get(exhibit.id, 0.0)
        if semantic_score >= SEMANTIC_RECALL_THRESHOLD:
            score += semantic_score * 6
            reasons.append(f"向量召回：语义相似度 {semantic_score:.2f}")
        if score > 0:
            hits.append(
                (
                    index,
                    HybridSearchHit(
                        exhibit=exhibit,
                        score=round(score, 2),
                        reasons=_dedupe_reasons(reasons),
                    ),
                )
            )

    hits.sort(key=lambda item: (-item[1].score, item[0]))
    total = len(hits)
    items = [hit for _, hit in hits[:limit]]
    return HybridSearchResponse(query=query, total=total, items=items)


def _apply_filters(
    exhibits: list[ExhibitResponse],
    filters: HybridSearchFilters | None,
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
    filters: HybridSearchFilters | None,
    understanding: QueryUnderstandingResult,
    reference_exhibit: ExhibitResponse | None = None,
) -> tuple[float, list[str]]:
    compact_query = _compact(query)
    score = 0.0
    reasons: list[str] = []

    direct_fields = [
        (exhibit.id, 5.0, f"匹配编号：{exhibit.id}"),
        (exhibit.name, 5.0, f"匹配展项：{exhibit.name}"),
        (exhibit.category, 3.0, f"匹配类别：{exhibit.category}"),
        (exhibit.theme.name, 4.0, f"匹配主题：{exhibit.theme.name}"),
        (exhibit.venue_type, 3.0, f"匹配场馆：{exhibit.venue_type}"),
        (exhibit.owner.name, 2.0, f"匹配业主：{exhibit.owner.name}"),
        (exhibit.supplier.name, 2.0, f"匹配供应商：{exhibit.supplier.name}"),
        *[
            (material.name, 2.0, f"匹配材料：{material.name}")
            for material in exhibit.materials
        ],
        *[
            (interaction.name, 2.0, f"匹配互动：{interaction.name}")
            for interaction in exhibit.interactions
        ],
        *[(tag, 2.0, f"匹配标签：{tag}") for tag in exhibit.tags],
    ]

    for value, weight, reason in direct_fields:
        if value and _compact(value) in compact_query:
            score += weight
            reasons.append(reason)

    if _mentions_child_audience(compact_query) and _exhibit_has_child_signal(exhibit):
        score += 4.0
        reasons.append("匹配人群：低龄儿童")

    if "互动" in compact_query and exhibit.interactions:
        score += 3.0
        interaction_names = "、".join(interaction.name for interaction in exhibit.interactions[:3])
        reasons.append(f"匹配互动形式：{interaction_names}")

    if _mentions_low_budget(compact_query) and _exhibit_has_low_budget(exhibit):
        score += 3.0
        reasons.append(
            f"匹配预算：低预算 {_format_budget(exhibit.budget_min)}-{_format_budget(exhibit.budget_max)}"
        )

    description_hits = _description_hits(compact_query, exhibit.description)
    if description_hits:
        score += len(description_hits)
        reasons.append(f"匹配说明：{'、'.join(description_hits)}")

    document_hits = _document_hits(compact_query, exhibit)
    if document_hits:
        score += len(document_hits) * 2.5
        reasons.extend(document_hits)

    understanding_score, understanding_reasons = _query_understanding_score(
        understanding,
        exhibit,
        reference_exhibit,
    )
    if understanding_score:
        score += understanding_score
        reasons.extend(understanding_reasons)

    reasons.extend(_filter_reasons(exhibit, filters))
    return score, reasons


def _filter_reasons(
    exhibit: ExhibitResponse,
    filters: HybridSearchFilters | None,
) -> list[str]:
    if filters is None:
        return []

    reasons: list[str] = []
    if filters.venue_type:
        reasons.append(f"筛选场馆：{filters.venue_type}")
    if filters.category:
        reasons.append(f"筛选类别：{filters.category}")
    if filters.theme:
        reasons.append(f"筛选主题：{filters.theme}")
    if filters.project_id:
        reasons.append(f"筛选项目：{filters.project_id}")
    if filters.owner:
        reasons.append(f"筛选业主：{filters.owner}")
    if filters.supplier:
        reasons.append(f"筛选供应商：{filters.supplier}")
    if filters.tag:
        reasons.append(f"筛选标签：{filters.tag}")
    if filters.material:
        reasons.append(f"筛选材料：{filters.material}")
    if filters.interaction:
        reasons.append(f"筛选互动：{filters.interaction}")
    if filters.status:
        reasons.append(f"筛选状态：{filters.status}")
    if filters.review_status:
        reasons.append(f"筛选审核：{filters.review_status}")
    if filters.budget_min is not None or filters.budget_max is not None:
        reasons.append(
            f"预算符合：{_format_budget(exhibit.budget_min)}-{_format_budget(exhibit.budget_max)}"
        )
    return reasons


def _description_hits(compact_query: str, description: str) -> list[str]:
    hits: list[str] = []
    compact_description = _compact(description)
    for signal in ("推拉", "配重", "跷跷板", "滑轮", "沙盘", "水循环", "投影"):
        if signal in compact_query and signal in compact_description:
            hits.append(signal)
    return hits


def _document_hits(compact_query: str, exhibit: ExhibitResponse) -> list[str]:
    if not compact_query:
        return []

    hits: list[str] = []
    for document in exhibit.documents:
        for chunk in document.chunks:
            if compact_query in _compact(chunk.text):
                hits.append(f"匹配资料：{document.name} #{chunk.sequence}")
                break
    return hits


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
    if AUDIENCE_LOW_AGE_CHILDREN in understanding.audience and _exhibit_has_child_signal(exhibit):
        score += 2.0
        reasons.append("查询理解：人群 low_age_children")
    if understanding.budget_intent == BUDGET_LOW and _exhibit_has_low_budget(exhibit):
        score += 2.5
        reasons.append("查询理解：预算倾向 low")
    elif _exhibit_has_lower_budget_than_reference(understanding, exhibit, reference_exhibit):
        score += 2.5
        reasons.append(f"查询理解：预算低于参照案例 {reference_exhibit.name}")
    elif understanding.budget_intent == BUDGET_LOWER_THAN_REFERENCE and _exhibit_has_low_budget(exhibit):
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


def _mentions_child_audience(compact_query: str) -> bool:
    return any(signal in compact_query for signal in ("低龄儿童", "低龄", "儿童", "亲子"))


def _exhibit_has_child_signal(exhibit: ExhibitResponse) -> bool:
    text = _compact(
        " ".join(
            [
                exhibit.venue_type,
                exhibit.description,
                *exhibit.tags,
                *[interaction.name for interaction in exhibit.interactions],
            ]
        )
    )
    return any(signal in text for signal in ("低龄儿童", "低龄", "儿童", "亲子"))


def _mentions_low_budget(compact_query: str) -> bool:
    return any(signal in compact_query for signal in ("预算不高", "低预算", "预算低", "预算有限"))


def _exhibit_has_low_budget(exhibit: ExhibitResponse) -> bool:
    return exhibit.budget_max <= 300000


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
            bool(AUDIENCE_LOW_AGE_CHILDREN in understanding.audience and _exhibit_has_child_signal(exhibit)),
            bool(understanding.tags and any(tag in understanding.tags for tag in exhibit.tags)),
        ]
    )


def _exhibit_matches_exclusions(exhibit: ExhibitResponse, exclusions: list[str]) -> bool:
    text = " ".join(
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
    return any(exclusion in text for exclusion in exclusions)


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


def _compact(value: str) -> str:
    return re.sub(r"[\s,，、。；;:：|/\\-]+", "", value.strip().lower())


def _dedupe_reasons(reasons: list[str]) -> list[str]:
    unique: list[str] = []
    seen: set[str] = set()
    for reason in reasons:
        if reason in seen:
            continue
        seen.add(reason)
        unique.append(reason)
    return unique
