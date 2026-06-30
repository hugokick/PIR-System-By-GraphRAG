import re
from collections.abc import Mapping

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
    hits: list[tuple[int, HybridSearchHit]] = []

    for index, exhibit in enumerate(filtered):
        score, reasons = _score_exhibit(query, exhibit, filters)
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
    items = [hit for _, hit in hits[:limit]]
    return HybridSearchResponse(query=query, total=len(items), items=items)


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

    description_hits = _description_hits(compact_query, exhibit.description)
    if description_hits:
        score += len(description_hits)
        reasons.append(f"匹配说明：{'、'.join(description_hits)}")

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
