from typing import Literal

from pydantic import BaseModel, Field


ReviewStatusValue = Literal["草稿", "待审核", "已审核", "已退回"]


class EntityRef(BaseModel):
    id: str
    name: str


class MediaAsset(BaseModel):
    id: str
    type: str
    name: str
    url: str
    note: str | None = None


class DocumentChunk(BaseModel):
    id: str
    text: str
    sequence: int


class DocumentAsset(BaseModel):
    id: str
    name: str
    file_type: str
    url: str
    source_note: str | None = None
    chunks: list[DocumentChunk] = Field(default_factory=list)


class ExhibitResponse(BaseModel):
    id: str
    name: str
    category: str
    theme: EntityRef
    venue_type: str
    budget_min: int
    budget_max: int
    materials: list[EntityRef]
    dimensions: str
    interactions: list[EntityRef]
    supplier: EntityRef
    project: EntityRef
    owner: EntityRef
    project_year: int
    status: str
    review_status: str = "待审核"
    description: str
    tags: list[str]
    media_assets: list[MediaAsset]
    documents: list[DocumentAsset]
    related_exhibit_ids: list[str] = Field(default_factory=list)


class ExhibitWriteRequest(BaseModel):
    id: str
    name: str
    category: str
    theme: EntityRef
    venue_type: str
    budget_min: int = Field(ge=0)
    budget_max: int = Field(ge=0)
    materials: list[EntityRef]
    dimensions: str
    interactions: list[EntityRef]
    supplier: EntityRef
    project: EntityRef
    owner: EntityRef
    project_year: int
    status: str
    review_status: str = "待审核"
    description: str
    tags: list[str] = Field(default_factory=list)
    media_assets: list[MediaAsset] = Field(default_factory=list)
    documents: list[DocumentAsset] = Field(default_factory=list)
    related_exhibit_ids: list[str] = Field(default_factory=list)

    def to_response(self) -> ExhibitResponse:
        return ExhibitResponse(**self.model_dump())


class ReviewStatusUpdateRequest(BaseModel):
    review_status: ReviewStatusValue


class ExhibitListResponse(BaseModel):
    total: int
    items: list[ExhibitResponse]


class ExhibitImportError(BaseModel):
    row: int
    field: str
    message: str


class ExhibitImportResponse(BaseModel):
    total_rows: int
    valid_rows: int
    imported_count: int
    errors: list[ExhibitImportError]
    items: list[ExhibitResponse]


class GraphNode(BaseModel):
    id: str
    label: str
    type: str


class GraphEdge(BaseModel):
    source: str
    target: str
    label: str
    type: str


class GraphResponse(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]


class GraphRagRequestFilters(BaseModel):
    theme: str | None = None
    material: str | None = None
    interaction: str | None = None
    venue_type: str | None = None
    status: str | None = None
    budget_min: int | None = Field(default=None, ge=0)
    budget_max: int | None = Field(default=None, ge=0)


class GraphRagSearchRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)
    filters: GraphRagRequestFilters | None = None


class GraphRagCitation(BaseModel):
    source_id: str
    source_type: str
    title: str
    snippet: str


class GraphRagSearchHit(BaseModel):
    exhibit: ExhibitResponse
    score: float
    reasons: list[str]
    citations: list[GraphRagCitation]
    graph: GraphResponse


class GraphRagSearchResponse(BaseModel):
    query: str
    total: int
    items: list[GraphRagSearchHit]


class HybridSearchFilters(BaseModel):
    category: str | None = None
    theme: str | None = None
    project_id: str | None = None
    material: str | None = None
    interaction: str | None = None
    venue_type: str | None = None
    status: str | None = None
    review_status: str | None = None
    budget_min: int | None = Field(default=None, ge=0)
    budget_max: int | None = Field(default=None, ge=0)


class HybridSearchRequest(BaseModel):
    query: str = Field(min_length=1)
    limit: int = Field(default=5, ge=1, le=20)
    filters: HybridSearchFilters | None = None


class HybridSearchHit(BaseModel):
    exhibit: ExhibitResponse
    score: float
    reasons: list[str]


class HybridSearchResponse(BaseModel):
    query: str
    total: int
    items: list[HybridSearchHit]


class GraphRagAnswerRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = Field(default=3, ge=1, le=10)
    filters: GraphRagRequestFilters | None = None


class GraphRagAnswerResponse(BaseModel):
    query: str
    answer: str
    citations: list[GraphRagCitation]
    items: list[GraphRagSearchHit]


class AuditLogEntry(BaseModel):
    id: str
    actor_role: str
    action: str
    resource_type: str
    resource_id: str
    summary: str
    created_at: str


class AuditLogListResponse(BaseModel):
    total: int
    items: list[AuditLogEntry]


class AuthLoginRequest(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)


class AuthUser(BaseModel):
    username: str
    role: str
    display_name: str


class AuthLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: AuthUser
