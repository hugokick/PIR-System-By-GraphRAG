from app.kg.builder import build_exhibit_kg_snapshot
from app.repository import seed_exhibits


def test_build_snapshot_contains_fixed_node_and_edge_types():
    snapshot = build_exhibit_kg_snapshot(seed_exhibits)

    node_types = {node.type for node in snapshot.nodes}
    edge_types = {edge.type for edge in snapshot.edges}

    assert {
        "exhibit",
        "project",
        "owner",
        "supplier",
        "material",
        "theme",
        "interaction",
        "media_asset",
        "document",
    } <= node_types
    assert {
        "belongs_to_project",
        "owned_by",
        "supplied_by",
        "uses_material",
        "has_theme",
        "has_interaction",
        "has_media",
        "has_document",
        "similar_to",
    } <= edge_types


def test_build_snapshot_creates_evidence_and_adjacency_for_exhibits():
    snapshot = build_exhibit_kg_snapshot(seed_exhibits)

    exhibit_node_ids = {node.id for node in snapshot.nodes if node.type == "exhibit"}
    evidence_source_ids = {
        evidence.source_id for evidence in snapshot.evidences if evidence.source_type == "exhibit"
    }

    assert "exhibit:lever-play" in exhibit_node_ids
    assert "lever-play" in evidence_source_ids
    assert "exhibit:lever-play" in snapshot.adjacency
    assert snapshot.adjacency["exhibit:lever-play"]


def test_build_snapshot_skips_missing_similar_targets_and_records_warning():
    broken = seed_exhibits[0].model_copy(update={"related_exhibit_ids": ["missing-exhibit"]})

    snapshot = build_exhibit_kg_snapshot([broken])

    assert snapshot.warnings
    assert any("missing-exhibit" in warning for warning in snapshot.warnings)
    assert not any(edge.target == "exhibit:missing-exhibit" for edge in snapshot.edges)
