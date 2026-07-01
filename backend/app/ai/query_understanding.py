from pydantic import BaseModel, Field


class QueryUnderstandingResult(BaseModel):
    original_query: str
    normalized_query: str
    themes: list[str] = Field(default_factory=list)
    venue_types: list[str] = Field(default_factory=list)
    audience: list[str] = Field(default_factory=list)
    budget_intent: str = "unknown"
    budget_min: int | None = None
    budget_max: int | None = None
    materials: list[str] = Field(default_factory=list)
    interactions: list[str] = Field(default_factory=list)
    project_case: str | None = None
    tags: list[str] = Field(default_factory=list)
    exclusions: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    reasoning: list[str] = Field(default_factory=list)


def understand_query(query: str) -> QueryUnderstandingResult:
    return QueryUnderstandingResult(
        original_query=query,
        normalized_query=query.strip(),
    )
