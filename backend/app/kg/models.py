from pydantic import BaseModel, Field


class KGNode(BaseModel):
    id: str
    type: str
    label: str
    attributes: dict[str, str | int | float | list[str] | None] = Field(default_factory=dict)
    source_refs: list[str] = Field(default_factory=list)


class KGEdge(BaseModel):
    source: str
    target: str
    type: str
    label: str
    weight: float = 1.0
    source_refs: list[str] = Field(default_factory=list)


class KGEvidence(BaseModel):
    evidence_id: str
    source_type: str
    source_id: str
    title: str
    snippet: str
    linked_node_ids: list[str] = Field(default_factory=list)
    linked_edge_ids: list[str] = Field(default_factory=list)


class KGSnapshot(BaseModel):
    nodes: list[KGNode]
    edges: list[KGEdge]
    evidences: list[KGEvidence]
    adjacency: dict[str, list[str]] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
