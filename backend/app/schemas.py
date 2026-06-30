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
