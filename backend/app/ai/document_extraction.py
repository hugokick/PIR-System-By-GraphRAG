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
NAME_PATTERNS = [
    re.compile(r"(?:展项名称|项目名称|方案名称)[:：]\s*(?P<name>[^。；\n]+)"),
]


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


def build_field_sources(
    payload: DocumentExtractionInput,
    normalized_text: str,
    exhibit_name: str | None,
    theme: str | None,
    budget_min: int | None,
    budget_max: int | None,
    materials: list[str],
    interactions: list[str],
) -> dict[str, list[SuggestedFieldSource]]:
    field_sources: dict[str, list[SuggestedFieldSource]] = {}
    snippet = normalized_text[:200]

    if exhibit_name is not None:
        field_sources["exhibit_name"] = [
            SuggestedFieldSource(
                document_id=payload.document_id,
                field_name="exhibit_name",
                snippet=snippet,
                reason=f"matched exhibit name: {exhibit_name}",
            )
        ]
    if theme is not None:
        field_sources["theme"] = [
            SuggestedFieldSource(
                document_id=payload.document_id,
                field_name="theme",
                snippet=snippet,
                reason=f"matched theme keyword: {theme}",
            )
        ]
    if budget_min is not None:
        field_sources["budget_min"] = [
            SuggestedFieldSource(
                document_id=payload.document_id,
                field_name="budget_min",
                snippet=snippet,
                reason="matched budget range",
            )
        ]
    if budget_max is not None:
        field_sources["budget_max"] = [
            SuggestedFieldSource(
                document_id=payload.document_id,
                field_name="budget_max",
                snippet=snippet,
                reason="matched budget range",
            )
        ]
    if materials:
        field_sources["materials"] = [
            SuggestedFieldSource(
                document_id=payload.document_id,
                field_name="materials",
                snippet=snippet,
                reason=f"matched material keywords: {', '.join(materials)}",
            )
        ]
    if interactions:
        field_sources["interactions"] = [
            SuggestedFieldSource(
                document_id=payload.document_id,
                field_name="interactions",
                snippet=snippet,
                reason=f"matched interaction keywords: {', '.join(interactions)}",
            )
        ]
    return field_sources


def extract_document_suggestions(
    payload: DocumentExtractionInput,
    provider: DocumentExtractionProvider | None = None,
) -> DocumentExtractionResult:
    _ = provider
    normalized_text = normalize_text(payload.text or "")
    exhibit_name = extract_name(normalized_text, payload.file_name)
    theme, category = extract_theme(normalized_text)
    budget_min, budget_max = extract_budget_range(normalized_text)
    materials = collect_keywords(normalized_text, MATERIAL_KEYWORDS)
    interactions = collect_keywords(normalized_text, INTERACTION_KEYWORDS)
    summary = build_summary(normalized_text, exhibit_name, theme)
    return DocumentExtractionResult(
        document_id=payload.document_id,
        file_name=payload.file_name,
        file_type=payload.file_type,
        source_note=payload.source_note,
        exhibit_name=exhibit_name,
        category=category,
        theme=theme,
        budget_min=budget_min,
        budget_max=budget_max,
        materials=materials,
        interactions=interactions,
        summary=summary,
        field_sources=build_field_sources(
            payload,
            normalized_text,
            exhibit_name,
            theme,
            budget_min,
            budget_max,
            materials,
            interactions,
        ),
        confidence=0.7 if any([exhibit_name, theme, budget_min is not None, budget_max is not None, materials, interactions]) else 0.0,
    )
