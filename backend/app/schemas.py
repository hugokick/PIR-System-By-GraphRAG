from pydantic import BaseModel, Field


class EntityRef(BaseModel):
    id: str
    name: str


class MediaAsset(BaseModel):
    id: str
    type: str
    name: str
    url: str
    note: str | None = None


class DocumentAsset(BaseModel):
    id: str
    name: str
    file_type: str
    url: str
    source_note: str | None = None


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
    description: str
    tags: list[str] = Field(default_factory=list)
    media_assets: list[MediaAsset] = Field(default_factory=list)
    documents: list[DocumentAsset] = Field(default_factory=list)
    related_exhibit_ids: list[str] = Field(default_factory=list)

    def to_response(self) -> ExhibitResponse:
        return ExhibitResponse(**self.model_dump())


class ExhibitListResponse(BaseModel):
    total: int
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


class GraphRagSearchRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)


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


class GraphRagAnswerRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = Field(default=3, ge=1, le=10)


class GraphRagAnswerResponse(BaseModel):
    query: str
    answer: str
    citations: list[GraphRagCitation]
    items: list[GraphRagSearchHit]
