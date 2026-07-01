from typing import Protocol

from pydantic import BaseModel, Field


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


def extract_document_suggestions(
    payload: DocumentExtractionInput,
    provider: DocumentExtractionProvider | None = None,
) -> DocumentExtractionResult:
    _ = provider
    return DocumentExtractionResult(
        document_id=payload.document_id,
        file_name=payload.file_name,
        file_type=payload.file_type,
        source_note=payload.source_note,
    )
