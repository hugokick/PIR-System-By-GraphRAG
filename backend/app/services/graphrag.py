from ..schemas import (
    ExhibitResponse,
    GraphRagAnswerResponse,
    GraphRagCitation,
    GraphRagSearchHit,
    GraphRagSearchResponse,
)
from .graph import build_exhibit_graph


def search_graphrag_context(
    query: str,
    exhibits: list[ExhibitResponse],
    top_k: int = 5,
) -> GraphRagSearchResponse:
    tokens = _query_tokens(query)
    hits = [
        hit
        for exhibit in exhibits
        if (hit := _score_exhibit(query, tokens, exhibit, exhibits)) is not None
    ]
    hits.sort(key=lambda item: (-item.score, item.exhibit.id))
    items = hits[:top_k]
    return GraphRagSearchResponse(query=query, total=len(items), items=items)


def answer_from_graphrag_context(
    query: str,
    exhibits: list[ExhibitResponse],
    top_k: int = 3,
) -> GraphRagAnswerResponse:
    search_response = search_graphrag_context(query, exhibits, top_k=top_k)
    citations = _deduplicate_citations(
        citation
        for item in search_response.items
        for citation in item.citations
    )

    if not search_response.items:
        return GraphRagAnswerResponse(
            query=query,
            answer=f"No evidence found in the exhibit library for: {query}",
            citations=[],
            items=[],
        )

    summaries = [
        f"{item.exhibit.id}: {item.exhibit.name} ({'; '.join(item.reasons)})"
        for item in search_response.items
    ]
    answer = (
        "Based on exhibit records and graph context, the strongest matches are "
        + " | ".join(summaries)
        + "."
    )
    return GraphRagAnswerResponse(
        query=query,
        answer=answer,
        citations=citations,
        items=search_response.items,
    )


def _score_exhibit(
    query: str,
    tokens: list[str],
    exhibit: ExhibitResponse,
    all_exhibits: list[ExhibitResponse],
) -> GraphRagSearchHit | None:
    fields = _search_fields(exhibit)
    reasons: list[str] = []
    score = 0.0
    normalized_query = query.strip().lower()

    for label, values in fields.items():
        joined = " ".join(values).lower()
        matches = [token for token in tokens if token and token in joined]
        if matches:
            field_score = len(set(matches)) * _field_weight(label)
            score += field_score
            reasons.append(f"matched {label}")

    if normalized_query and any(normalized_query in value.lower() for value in fields["identity"]):
        score += 5.0
        if "matched identity" not in reasons:
            reasons.insert(0, "matched identity")

    if score <= 0:
        return None

    return GraphRagSearchHit(
        exhibit=exhibit,
        score=score,
        reasons=reasons,
        citations=_citations_for_exhibit(exhibit),
        graph=build_exhibit_graph(exhibit, all_exhibits),
    )


def _query_tokens(query: str) -> list[str]:
    normalized = query.strip().lower()
    if not normalized:
        return []
    separators = ",，;；/|"
    for separator in separators:
        normalized = normalized.replace(separator, " ")
    return [token for token in normalized.split() if token]


def _search_fields(exhibit: ExhibitResponse) -> dict[str, list[str]]:
    return {
        "identity": [exhibit.id, exhibit.name],
        "classification": [exhibit.category, exhibit.theme.name, exhibit.venue_type, *exhibit.tags],
        "materials": [material.name for material in exhibit.materials],
        "interactions": [interaction.name for interaction in exhibit.interactions],
        "project": [exhibit.project.name, exhibit.owner.name, exhibit.supplier.name],
        "description": [exhibit.description],
        "documents": [
            value
            for document in exhibit.documents
            for value in [document.name, document.source_note or ""]
            if value
        ],
    }


def _field_weight(label: str) -> float:
    weights = {
        "identity": 4.0,
        "classification": 3.0,
        "materials": 2.0,
        "interactions": 2.0,
        "project": 2.0,
        "documents": 2.0,
        "description": 1.0,
    }
    return weights[label]


def _citations_for_exhibit(exhibit: ExhibitResponse) -> list[GraphRagCitation]:
    citations = [
        GraphRagCitation(
            source_id=exhibit.id,
            source_type="exhibit",
            title=exhibit.name,
            snippet=exhibit.description,
        )
    ]
    citations.extend(
        GraphRagCitation(
            source_id=document.id,
            source_type="document",
            title=document.name,
            snippet=document.source_note or document.url,
        )
        for document in exhibit.documents
    )
    return citations


def _deduplicate_citations(citations) -> list[GraphRagCitation]:
    seen: set[tuple[str, str]] = set()
    unique: list[GraphRagCitation] = []
    for citation in citations:
        key = (citation.source_type, citation.source_id)
        if key in seen:
            continue
        seen.add(key)
        unique.append(citation)
    return unique
