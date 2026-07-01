import re
from typing import Protocol

from pydantic import BaseModel, Field


BUDGET_UNKNOWN = "unknown"
BUDGET_LOW = "low"
BUDGET_MEDIUM = "medium"
BUDGET_HIGH = "high"
BUDGET_LOWER_THAN_REFERENCE = "lower_than_reference"

AUDIENCE_LOW_AGE_CHILDREN = "low_age_children"
AUDIENCE_PRIMARY_SCHOOL = "primary_school"
AUDIENCE_TEEN = "teen"
AUDIENCE_FAMILY = "family"
AUDIENCE_GENERAL = "general"

THEME_SIGNALS = ("力学", "水循环", "水资源", "天文", "电磁学", "生态")
VENUE_TYPE_SIGNALS = ("儿童科技馆", "县级科技馆", "综合科技馆", "科技馆", "博物馆")
MATERIAL_SIGNALS = ("金属", "木作", "亚克力", "水泵", "LED", "绳索", "防火板")
INTERACTION_SIGNALS = ("机械互动", "按钮互动", "数字投影", "模型演示", "竞赛互动", "亲子协作", "动手实验")
TAG_SIGNALS = ("低预算", "预算适中", "高互动", "互动性强", "维护成本低", "多人协作", "低龄儿童")
WEAK_QUERY_SIGNALS = ("找几个", "有没有", "推荐一下", "推荐")


class QueryUnderstandingProvider(Protocol):
    def understand(self, query: str) -> "QueryUnderstandingResult | None":
        ...


class QueryUnderstandingResult(BaseModel):
    original_query: str
    normalized_query: str
    themes: list[str] = Field(default_factory=list)
    venue_types: list[str] = Field(default_factory=list)
    audience: list[str] = Field(default_factory=list)
    budget_intent: str = BUDGET_UNKNOWN
    budget_min: int | None = None
    budget_max: int | None = None
    materials: list[str] = Field(default_factory=list)
    interactions: list[str] = Field(default_factory=list)
    project_case: str | None = None
    tags: list[str] = Field(default_factory=list)
    exclusions: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    reasoning: list[str] = Field(default_factory=list)


def understand_query(
    query: str,
    provider: QueryUnderstandingProvider | None = None,
) -> QueryUnderstandingResult:
    if provider is not None:
        try:
            provided = provider.understand(query)
        except Exception:
            provided = None
        if provided is not None and provided.confidence >= 0.6:
            return provided
    return _rule_based_understand(query)


def _rule_based_understand(query: str) -> QueryUnderstandingResult:
    normalized_query = _normalize(query)
    reasoning: list[str] = []
    themes = _matched_signals(normalized_query, THEME_SIGNALS, reasoning, "主题")
    venue_types = _matched_signals(normalized_query, VENUE_TYPE_SIGNALS, reasoning, "场馆类型")
    materials = _matched_signals(normalized_query, MATERIAL_SIGNALS, reasoning, "材料")
    interactions = _matched_signals(normalized_query, INTERACTION_SIGNALS, reasoning, "互动")
    tags = _matched_signals(normalized_query, TAG_SIGNALS, reasoning, "标签")

    audience: list[str] = []
    if "低龄儿童" in normalized_query or "低龄" in normalized_query:
        audience.append(AUDIENCE_LOW_AGE_CHILDREN)
        reasoning.append("识别到人群：low_age_children")
    elif "亲子" in normalized_query or "家庭" in normalized_query:
        audience.append(AUDIENCE_FAMILY)
        reasoning.append("识别到人群：family")

    budget_intent = BUDGET_UNKNOWN
    budget_min = None
    budget_max = None
    if "预算更低" in normalized_query or ("更低" in normalized_query and "类似" in normalized_query):
        budget_intent = BUDGET_LOWER_THAN_REFERENCE
        reasoning.append("识别到预算倾向：lower_than_reference")
    elif any(signal in normalized_query for signal in ("预算不高", "预算有限", "低预算", "预算低")):
        budget_intent = BUDGET_LOW
        budget_max = 300000
        reasoning.append("识别到预算倾向：low")
    elif any(signal in normalized_query for signal in ("高预算", "预算充足")):
        budget_intent = BUDGET_HIGH
        budget_min = 500000
        reasoning.append("识别到预算倾向：high")

    project_case = None
    case_match = re.search(r"类似(.+?)(?:但|，|,|。|的方案|方案|$)", normalized_query)
    if case_match:
        project_case = case_match.group(1).strip()
        reasoning.append(f"识别到参照案例：{project_case}")

    exclusions = _extract_exclusions(normalized_query, reasoning)
    confidence = _confidence(
        themes=themes,
        venue_types=venue_types,
        audience=audience,
        budget_intent=budget_intent,
        materials=materials,
        interactions=interactions,
        tags=tags,
        project_case=project_case,
        exclusions=exclusions,
        normalized_query=normalized_query,
    )

    if confidence < 0.4 and not reasoning:
        reasoning.append("未识别出有效检索槽位")

    return QueryUnderstandingResult(
        original_query=query,
        normalized_query=normalized_query,
        themes=themes,
        venue_types=venue_types,
        audience=audience,
        budget_intent=budget_intent,
        budget_min=budget_min,
        budget_max=budget_max,
        materials=materials,
        interactions=interactions,
        project_case=project_case,
        tags=tags,
        exclusions=exclusions,
        confidence=confidence,
        reasoning=reasoning,
    )


def _normalize(query: str) -> str:
    return re.sub(r"\s+", "", query.strip())


def _matched_signals(
    query: str,
    signals: tuple[str, ...],
    reasoning: list[str],
    label: str,
) -> list[str]:
    matched = [signal for signal in signals if signal in query]
    for signal in matched:
        reasoning.append(f"识别到{label}：{signal}")
    return matched


def _extract_exclusions(query: str, reasoning: list[str]) -> list[str]:
    matches = re.findall(r"(?:不要|排除|不考虑)([^，,。；;]+)", query)
    exclusions: list[str] = []
    for match in matches:
        for item in re.split(r"[、和及与]", match):
            cleaned = item.strip()
            if cleaned:
                exclusions.append(cleaned)
                reasoning.append(f"识别到排除条件：{cleaned}")
    return exclusions


def _confidence(
    *,
    themes: list[str],
    venue_types: list[str],
    audience: list[str],
    budget_intent: str,
    materials: list[str],
    interactions: list[str],
    tags: list[str],
    project_case: str | None,
    exclusions: list[str],
    normalized_query: str,
) -> float:
    score = 0.0
    if themes:
        score += 0.2
    if venue_types:
        score += 0.15
    if audience:
        score += 0.15
    if budget_intent != BUDGET_UNKNOWN:
        score += 0.15
    if materials:
        score += 0.1
    if interactions:
        score += 0.15
    if tags:
        score += 0.1
    if project_case:
        score += 0.1
    if exclusions:
        score += 0.1
    if not normalized_query or normalized_query in WEAK_QUERY_SIGNALS:
        return 0.2
    return round(min(score, 0.95), 2)
