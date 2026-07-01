from pydantic import BaseModel, Field

from app.kg.models import KGEvidence, KGSnapshot
from app.schemas import ExhibitResponse


class GraphRAGFilters(BaseModel):
    category: str | None = None
    theme: str | None = None
    project_id: str | None = None
    material: str | None = None
    interaction: str | None = None
    owner: str | None = None
    supplier: str | None = None
    tag: str | None = None
    venue_type: str | None = None
    status: str | None = None
    review_status: str | None = None
    budget_min: int | None = None
    budget_max: int | None = None


class GraphRAGHit(BaseModel):
    exhibit: ExhibitResponse
    score: float
    reasons: list[str] = Field(default_factory=list)
    citations: list[KGEvidence] = Field(default_factory=list)
    neighborhood: KGSnapshot


class GraphRAGSearchResponse(BaseModel):
    query: str
    total: int
    items: list[GraphRAGHit] = Field(default_factory=list)
