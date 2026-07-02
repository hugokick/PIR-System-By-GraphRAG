import re
from pathlib import Path
from typing import Protocol

from pydantic import BaseModel, Field


THEME_KEYWORDS = {
    "力学": "基础科学",
    "水循环": "生态环保",
    "流体": "生态环保",
    "天文": "宇宙探索",
    "宇宙探索": "宇宙探索",
}

BUDGET_RANGE_PATTERNS = [
    re.compile(r"(?P<min>\d+(?:\.\d+)?)\s*万\s*(?:到|至|-|~)\s*(?P<max>\d+(?:\.\d+)?)\s*万"),
    re.compile(r"(?P<min>\d+(?:\.\d+)?)\s*万元\s*(?:到|至|-|~)\s*(?P<max>\d+(?:\.\d+)?)\s*万元"),
]
MATERIAL_KEYWORDS = ["钢结构", "亚克力", "木饰面", "铝板", "透明管道"]
INTERACTION_KEYWORDS = ["机械互动", "按钮互动", "触摸互动", "沉浸影像"]
VENUE_TYPE_KEYWORDS = [
    "儿童科技馆",
    "自然博物馆",
    "科技馆",
    "博物馆",
    "规划馆",
    "企业展厅",
    "科普馆",
    "校园科技馆",
]
TAG_KEYWORDS = [
    "低龄儿童",
    "亲子互动",
    "多人协作",
    "高互动",
    "低预算",
    "沉浸式",
    "安全维护",
    "科普教育",
]
NAME_PATTERNS = [
    re.compile(r"(?:展项名称|项目名称|方案名称)[:：]\s*(?P<name>[^。；\n]+)"),
]
VENUE_TYPE_PATTERN = re.compile(r"(?:适用场馆|适用展馆|场馆类型|展馆类型)[:：]\s*(?P<value>[^。；\n,，]+)")
TAG_PATTERN = re.compile(r"(?:标签|关键词)[:：]\s*(?P<value>[^。\n]+)")
TAG_SPLIT_PATTERN = re.compile(r"[、,，；;\s]+")
ORG_PATTERNS = {
    "supplier": re.compile(r"(?:供应商|承建单位|实施单位)[:：]\s*(?P<value>[^。；\n,，]+)"),
    "owner": re.compile(r"(?:业主|甲方|建设单位)[:：]\s*(?P<value>[^。；\n,，]+)"),
}
YEAR_PATTERN = re.compile(r"(?:项目年份|年份)[:：]?\s*(?P<value>20\d{2}|19\d{2})")


class DocumentTextInput(BaseModel):
    chunk_id: str | None = None
    text: str
    sequence: int | None = None
    source_locator: str | None = None


class DocumentExtractionInput(BaseModel):
    document_id: str
    file_name: str
    file_type: str
    source_note: str | None = None
    text: str | None = None
    chunks: list[DocumentTextInput] = Field(default_factory=list)


class SuggestedFieldSource(BaseModel):
    document_id: str
    field_name: str
    chunk_id: str | None = None
    source_locator: str | None = None
    snippet: str
    reason: str


class DocumentExtractionResult(BaseModel):
    document_id: str
    file_name: str
    file_type: str
    source_note: str | None = None
    exhibit_name: str | None = None
    category: str | None = None
    theme: str | None = None
    venue_type: str | None = None
    budget_min: int | None = None
    budget_max: int | None = None
    materials: list[str] = Field(default_factory=list)
    interactions: list[str] = Field(default_factory=list)
    supplier: str | None = None
    owner: str | None = None
    project_year: int | None = None
    tags: list[str] = Field(default_factory=list)
    summary: str = ""
    confidence: float = 0.0
    field_sources: dict[str, list[SuggestedFieldSource]] = Field(default_factory=dict)


class DocumentExtractionProvider(Protocol):
    def extract(self, payload: DocumentExtractionInput) -> DocumentExtractionResult | None:
        ...


def normalize_text(text: str) -> str:
    return " ".join(text.replace("\u3000", " ").split())


def amount_to_yuan(value: str) -> int:
    return int(float(value) * 10000)


def extract_theme(text: str) -> tuple[str | None, str | None]:
    for theme, category in THEME_KEYWORDS.items():
        if theme in text:
            return theme, category
    return None, None


def extract_budget_range(text: str) -> tuple[int | None, int | None]:
    for pattern in BUDGET_RANGE_PATTERNS:
        match = pattern.search(text)
        if match:
            return amount_to_yuan(match.group("min")), amount_to_yuan(match.group("max"))
    return None, None


def extract_name(text: str, file_name: str) -> str | None:
    for pattern in NAME_PATTERNS:
        match = pattern.search(text)
        if match:
            return match.group("name").strip()
    if not text:
        return None
    stem = Path(file_name).stem.strip()
    return stem or None


def collect_keywords(text: str, keywords: list[str]) -> list[str]:
    return [keyword for keyword in keywords if keyword in text]


def unique_in_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        normalized = value.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result


def extract_venue_type(segments: list[DocumentTextInput], text: str) -> tuple[str | None, DocumentTextInput | None]:
    for segment in segments:
        match = VENUE_TYPE_PATTERN.search(normalize_text(segment.text))
        if match:
            return match.group("value").strip(), segment
    for keyword in VENUE_TYPE_KEYWORDS:
        segment = find_segment_for_keyword(segments, keyword)
        if segment is not None:
            return keyword, segment
    return None, None


def extract_tags(segments: list[DocumentTextInput], text: str) -> list[str]:
    tags: list[str] = []
    for segment in segments:
        match = TAG_PATTERN.search(normalize_text(segment.text))
        if not match:
            continue
        tags.extend(
            value.strip()
            for value in TAG_SPLIT_PATTERN.split(match.group("value"))
            if value.strip()
        )
    tags.extend(collect_keywords(text, TAG_KEYWORDS))
    return unique_in_order(tags)[:8]


def build_summary(text: str, name: str | None, theme: str | None) -> str:
    sentences = [item.strip() for item in re.split(r"[。！？!?\n]", text) if item.strip()]
    if not sentences:
        return ""
    preferred = [
        sentence
        for sentence in sentences
        if any(token and token in sentence for token in [name, theme, "互动", "预算"])
    ]
    return "。".join(preferred[:2] or sentences[:2])


def iter_source_segments(payload: DocumentExtractionInput) -> list[DocumentTextInput]:
    if payload.chunks:
        return payload.chunks
    if payload.text:
        return [DocumentTextInput(chunk_id=None, text=payload.text, sequence=1, source_locator=None)]
    return []


def build_searchable_text(payload: DocumentExtractionInput) -> str:
    return normalize_text(" ".join(segment.text for segment in iter_source_segments(payload)))


def add_source(
    field_sources: dict[str, list[SuggestedFieldSource]],
    field_name: str,
    segment: DocumentTextInput,
    snippet: str,
    reason: str,
    document_id: str,
) -> None:
    field_sources.setdefault(field_name, []).append(
        SuggestedFieldSource(
            document_id=document_id,
            field_name=field_name,
            chunk_id=segment.chunk_id,
            source_locator=segment.source_locator,
            snippet=snippet,
            reason=reason,
        )
    )


def find_segment_for_keyword(segments: list[DocumentTextInput], keyword: str) -> DocumentTextInput | None:
    for segment in segments:
        if keyword in normalize_text(segment.text):
            return segment
    return None


def find_segment_for_budget(segments: list[DocumentTextInput]) -> DocumentTextInput | None:
    for segment in segments:
        if extract_budget_range(normalize_text(segment.text)) != (None, None):
            return segment
    return None


def extract_labeled_value(segments: list[DocumentTextInput], field_name: str) -> tuple[str | None, DocumentTextInput | None]:
    pattern = ORG_PATTERNS[field_name]
    for segment in segments:
        match = pattern.search(normalize_text(segment.text))
        if match:
            return match.group("value").strip(), segment
    return None, None


def extract_project_year(segments: list[DocumentTextInput]) -> tuple[int | None, DocumentTextInput | None]:
    for segment in segments:
        match = YEAR_PATTERN.search(normalize_text(segment.text))
        if match:
            return int(match.group("value")), segment
    return None, None


def build_field_sources(
    payload: DocumentExtractionInput,
    segments: list[DocumentTextInput],
    normalized_text: str,
    exhibit_name: str | None,
    theme: str | None,
    budget_min: int | None,
    budget_max: int | None,
    materials: list[str],
    interactions: list[str],
    venue_type: str | None,
    tags: list[str],
    supplier: str | None,
    owner: str | None,
    project_year: int | None,
) -> dict[str, list[SuggestedFieldSource]]:
    field_sources: dict[str, list[SuggestedFieldSource]] = {}

    if exhibit_name is not None:
        segment = find_segment_for_keyword(segments, exhibit_name) or (segments[0] if segments else None)
        if segment is not None:
            add_source(
                field_sources,
                "exhibit_name",
                segment,
                normalize_text(segment.text)[:200],
                f"matched exhibit name: {exhibit_name}",
                payload.document_id,
            )
    if theme is not None:
        segment = find_segment_for_keyword(segments, theme)
        if segment is not None:
            add_source(
                field_sources,
                "theme",
                segment,
                normalize_text(segment.text)[:200],
                f"matched theme keyword: {theme}",
                payload.document_id,
            )
    if budget_min is not None:
        segment = find_segment_for_budget(segments)
        if segment is not None:
            add_source(
                field_sources,
                "budget_min",
                segment,
                normalize_text(segment.text)[:200],
                "matched budget range",
                payload.document_id,
            )
    if budget_max is not None:
        segment = find_segment_for_budget(segments)
        if segment is not None:
            add_source(
                field_sources,
                "budget_max",
                segment,
                normalize_text(segment.text)[:200],
                "matched budget range",
                payload.document_id,
            )
    if materials:
        for material in materials:
            segment = find_segment_for_keyword(segments, material)
            if segment is not None:
                add_source(
                    field_sources,
                    "materials",
                    segment,
                    normalize_text(segment.text)[:200],
                    f"matched material keyword: {material}",
                    payload.document_id,
                )
    if interactions:
        for interaction in interactions:
            segment = find_segment_for_keyword(segments, interaction)
            if segment is not None:
                add_source(
                    field_sources,
                    "interactions",
                    segment,
                    normalize_text(segment.text)[:200],
                    f"matched interaction keyword: {interaction}",
                    payload.document_id,
                )
    if venue_type is not None:
        segment = find_segment_for_keyword(segments, venue_type)
        if segment is not None:
            add_source(
                field_sources,
                "venue_type",
                segment,
                normalize_text(segment.text)[:200],
                f"matched venue type: {venue_type}",
                payload.document_id,
            )
    if tags:
        for tag in tags:
            segment = find_segment_for_keyword(segments, tag)
            if segment is not None:
                add_source(
                    field_sources,
                    "tags",
                    segment,
                    normalize_text(segment.text)[:200],
                    f"matched tag: {tag}",
                    payload.document_id,
                )
    if supplier is not None:
        segment = find_segment_for_keyword(segments, supplier)
        if segment is not None:
            add_source(
                field_sources,
                "supplier",
                segment,
                normalize_text(segment.text)[:200],
                f"matched supplier: {supplier}",
                payload.document_id,
            )
    if owner is not None:
        segment = find_segment_for_keyword(segments, owner)
        if segment is not None:
            add_source(
                field_sources,
                "owner",
                segment,
                normalize_text(segment.text)[:200],
                f"matched owner: {owner}",
                payload.document_id,
            )
    if project_year is not None:
        segment = find_segment_for_keyword(segments, str(project_year))
        if segment is not None:
            add_source(
                field_sources,
                "project_year",
                segment,
                normalize_text(segment.text)[:200],
                f"matched project year: {project_year}",
                payload.document_id,
            )
    return field_sources


def extract_by_rules(payload: DocumentExtractionInput) -> DocumentExtractionResult:
    segments = iter_source_segments(payload)
    normalized_text = build_searchable_text(payload)
    exhibit_name = extract_name(normalized_text, payload.file_name)
    theme, category = extract_theme(normalized_text)
    budget_min, budget_max = extract_budget_range(normalized_text)
    materials = collect_keywords(normalized_text, MATERIAL_KEYWORDS)
    interactions = collect_keywords(normalized_text, INTERACTION_KEYWORDS)
    venue_type, _ = extract_venue_type(segments, normalized_text)
    tags = extract_tags(segments, normalized_text)
    supplier, _ = extract_labeled_value(segments, "supplier")
    owner, _ = extract_labeled_value(segments, "owner")
    project_year, _ = extract_project_year(segments)
    summary = build_summary(normalized_text, exhibit_name, theme)
    return DocumentExtractionResult(
        document_id=payload.document_id,
        file_name=payload.file_name,
        file_type=payload.file_type,
        source_note=payload.source_note,
        exhibit_name=exhibit_name,
        category=category,
        theme=theme,
        venue_type=venue_type,
        budget_min=budget_min,
        budget_max=budget_max,
        materials=materials,
        interactions=interactions,
        tags=tags,
        supplier=supplier,
        owner=owner,
        project_year=project_year,
        summary=summary,
        field_sources=build_field_sources(
            payload,
            segments,
            normalized_text,
            exhibit_name,
            theme,
            budget_min,
            budget_max,
            materials,
            interactions,
            venue_type,
            tags,
            supplier,
            owner,
            project_year,
        ),
        confidence=0.7 if any([exhibit_name, theme, budget_min is not None, budget_max is not None, materials, interactions, venue_type, tags, supplier, owner, project_year]) else 0.0,
    )


def extract_document_suggestions(
    payload: DocumentExtractionInput,
    provider: DocumentExtractionProvider | None = None,
) -> DocumentExtractionResult:
    if provider is not None:
        try:
            provider_result = provider.extract(payload)
        except Exception:
            provider_result = None
        if provider_result is not None and provider_result.confidence >= 0.6:
            return provider_result
    return extract_by_rules(payload)
