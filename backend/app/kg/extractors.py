from app.schemas import ExhibitResponse

from .models import KGEvidence, KGNode


def exhibit_node(exhibit: ExhibitResponse) -> KGNode:
    return KGNode(
        id=f"exhibit:{exhibit.id}",
        type="exhibit",
        label=exhibit.name,
        attributes={
            "category": exhibit.category,
            "theme": exhibit.theme.name,
            "venue_type": exhibit.venue_type,
            "status": exhibit.status,
            "project_year": exhibit.project_year,
        },
        source_refs=[f"exhibit:{exhibit.id}"],
    )


def exhibit_evidence(exhibit: ExhibitResponse) -> KGEvidence:
    return KGEvidence(
        evidence_id=f"evidence:exhibit:{exhibit.id}",
        source_type="exhibit",
        source_id=exhibit.id,
        title=exhibit.name,
        snippet=exhibit.description,
        linked_node_ids=[f"exhibit:{exhibit.id}"],
        linked_edge_ids=[],
    )


def document_evidences(exhibit: ExhibitResponse) -> list[KGEvidence]:
    return [
        KGEvidence(
            evidence_id=f"evidence:document:{document.id}",
            source_type="document",
            source_id=document.id,
            title=document.name,
            snippet=document.source_note or document.url,
            linked_node_ids=[f"exhibit:{exhibit.id}", f"document:{document.id}"],
            linked_edge_ids=[f"exhibit:{exhibit.id}:has_document:document:{document.id}"],
        )
        for document in exhibit.documents
    ]
