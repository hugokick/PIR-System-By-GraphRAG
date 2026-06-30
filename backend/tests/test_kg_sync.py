from app.kg.builder import build_exhibit_kg_snapshot
from app.kg.sync import sync_snapshot_after_delete, sync_snapshot_after_upsert
from app.repository import seed_exhibits
from app.schemas import EntityRef


def test_sync_snapshot_after_upsert_adds_new_exhibit_subgraph():
    base_exhibits = seed_exhibits[:2]
    base_snapshot = build_exhibit_kg_snapshot(base_exhibits)
    new_exhibit = seed_exhibits[0].model_copy(
        update={
            "id": "gear-lab",
            "name": "齿轮实验台",
            "related_exhibit_ids": ["lever-play"],
        }
    )

    synced = sync_snapshot_after_upsert(
        snapshot=base_snapshot,
        exhibit=new_exhibit,
        exhibits_after_change=[*base_exhibits, new_exhibit],
    )

    node_ids = {node.id for node in synced.nodes}
    assert "exhibit:gear-lab" in node_ids
    assert any(
        edge.source == "exhibit:gear-lab"
        and edge.target == "exhibit:lever-play"
        and edge.type == "similar_to"
        for edge in synced.edges
    )


def test_sync_snapshot_after_upsert_replaces_old_exhibit_relations():
    base_snapshot = build_exhibit_kg_snapshot(seed_exhibits)
    updated_exhibit = seed_exhibits[0].model_copy(
        update={
            "materials": [EntityRef(id="glass", name="玻璃")],
            "interactions": [EntityRef(id="rotation", name="旋转互动")],
        }
    )
    exhibits_after_change = [updated_exhibit, *seed_exhibits[1:]]

    synced = sync_snapshot_after_upsert(
        snapshot=base_snapshot,
        exhibit=updated_exhibit,
        exhibits_after_change=exhibits_after_change,
    )

    assert any(
        edge.source == "exhibit:lever-play"
        and edge.target == "material:glass"
        and edge.type == "uses_material"
        for edge in synced.edges
    )
    assert not any(
        edge.source == "exhibit:lever-play"
        and edge.target == "material:metal"
        and edge.type == "uses_material"
        for edge in synced.edges
    )


def test_sync_snapshot_after_delete_removes_exhibit_node_and_inbound_edges():
    base_exhibits = seed_exhibits[:2]
    base_snapshot = build_exhibit_kg_snapshot(base_exhibits)

    synced = sync_snapshot_after_delete(
        snapshot=base_snapshot,
        exhibit_id="pulley-wall",
        exhibits_after_delete=[seed_exhibits[0]],
    )

    node_ids = {node.id for node in synced.nodes}
    assert "exhibit:pulley-wall" not in node_ids
    assert not any(edge.target == "exhibit:pulley-wall" for edge in synced.edges)
