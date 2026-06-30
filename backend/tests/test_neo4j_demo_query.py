from app.neo4j_demo.query import (
    build_demo_graph_cypher,
    build_exhibit_graph_cypher,
    map_neo4j_records_to_graph_response,
    map_neo4j_relationship_records_to_graph_response,
)


def test_build_exhibit_graph_cypher_targets_exhibit_id():
    cypher = build_exhibit_graph_cypher("lever-play")

    assert "MATCH (center:Exhibit {id: $exhibit_id})" in cypher
    assert "OPTIONAL MATCH (center)-[rel]->(neighbor)" in cypher
    assert "RETURN center, labels(center) AS center_labels" in cypher


def test_build_demo_graph_cypher_returns_all_demo_relationships():
    cypher = build_demo_graph_cypher()

    assert "MATCH (source)-[rel]->(target)" in cypher
    assert "RETURN source, labels(source) AS source_labels" in cypher
    assert "$exhibit_id" not in cypher


def test_map_neo4j_records_to_graph_response_returns_prefixed_nodes_and_edges():
    records = [
        {
            "center": {"id": "lever-play", "name": "杠杆乐园", "label": "杠杆乐园"},
            "center_labels": ["Exhibit"],
            "neighbor": {
                "id": "qinghe-2024",
                "name": "青禾儿童科技馆更新项目",
                "label": "青禾儿童科技馆更新项目",
            },
            "neighbor_labels": ["Project"],
            "rel_type": "BELONGS_TO_PROJECT",
            "rel_label": "所属项目",
        }
    ]

    graph = map_neo4j_records_to_graph_response(records)

    assert any(node.id == "exhibit:lever-play" and node.type == "exhibit" for node in graph.nodes)
    assert any(node.id == "project:qinghe-2024" and node.type == "project" for node in graph.nodes)
    assert [edge.model_dump() for edge in graph.edges] == [
        {
            "source": "exhibit:lever-play",
            "target": "project:qinghe-2024",
            "label": "所属项目",
            "type": "belongs_to_project",
        }
    ]


def test_map_neo4j_records_to_graph_response_deduplicates_nodes():
    records = [
        {
            "center": {"id": "lever-play", "name": "杠杆乐园"},
            "center_labels": ["Exhibit"],
            "neighbor": {"id": "mechanics", "name": "力学"},
            "neighbor_labels": ["Theme"],
            "rel_type": "HAS_THEME",
            "rel_label": "主题",
        },
        {
            "center": {"id": "lever-play", "name": "杠杆乐园"},
            "center_labels": ["Exhibit"],
            "neighbor": {"id": "qisi", "name": "启思互动工坊"},
            "neighbor_labels": ["Supplier"],
            "rel_type": "SUPPLIED_BY",
            "rel_label": "供应商",
        },
    ]

    graph = map_neo4j_records_to_graph_response(records)

    exhibit_nodes = [node for node in graph.nodes if node.id == "exhibit:lever-play"]
    assert len(exhibit_nodes) == 1


def test_map_neo4j_records_to_graph_response_deduplicates_edges():
    record = {
        "center": {"id": "lever-play", "name": "鏉犳潌涔愬洯"},
        "center_labels": ["Exhibit"],
        "neighbor": {"id": "mechanics", "name": "鍔涘"},
        "neighbor_labels": ["Theme"],
        "rel_type": "HAS_THEME",
        "rel_label": "theme",
    }

    graph = map_neo4j_records_to_graph_response([record, record])

    assert [edge.type for edge in graph.edges] == ["has_theme"]


def test_map_neo4j_relationship_records_to_graph_response_maps_all_edges():
    records = [
        {
            "source": {"id": "lever-play", "name": "Lever Play"},
            "source_labels": ["Exhibit"],
            "target": {"id": "qisi", "name": "Qisi Supplier"},
            "target_labels": ["Supplier"],
            "rel_type": "SUPPLIED_BY",
            "rel_label": "supplier",
        },
        {
            "source": {"id": "space-dome", "name": "Space Dome"},
            "source_labels": ["Exhibit"],
            "target": {"id": "astronomy", "name": "Astronomy"},
            "target_labels": ["Theme"],
            "rel_type": "HAS_THEME",
            "rel_label": "theme",
        },
    ]

    graph = map_neo4j_relationship_records_to_graph_response(records)

    node_ids = {node.id for node in graph.nodes}
    edge_types = {edge.type for edge in graph.edges}
    assert {"exhibit:lever-play", "supplier:qisi", "exhibit:space-dome", "theme:astronomy"} <= node_ids
    assert {"supplied_by", "has_theme"} <= edge_types
