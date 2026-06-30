from collections.abc import Mapping

from app.schemas import GraphEdge, GraphNode, GraphResponse


REL_TYPE_MAP = {
    "BELONGS_TO_PROJECT": "belongs_to_project",
    "OWNED_BY": "owned_by",
    "SUPPLIED_BY": "supplied_by",
    "USES_MATERIAL": "uses_material",
    "HAS_THEME": "has_theme",
    "HAS_INTERACTION": "has_interaction",
    "HAS_DOCUMENT": "has_document",
    "SIMILAR_TO": "similar_to",
}


def _node_type(label: str | None) -> str:
    return (label or "node").lower()


def _node_id(label: str | None, raw_id: str) -> str:
    return f"{_node_type(label)}:{raw_id}"


def build_exhibit_graph_cypher(exhibit_id: str) -> str:
    _ = exhibit_id
    return "\n".join(
        [
            "MATCH (center:Exhibit {id: $exhibit_id})",
            "OPTIONAL MATCH (center)-[rel]->(neighbor)",
            "RETURN center, labels(center) AS center_labels,",
            "       neighbor, labels(neighbor) AS neighbor_labels,",
            "       type(rel) AS rel_type, rel.label AS rel_label",
        ]
    )


def build_demo_graph_cypher() -> str:
    return "\n".join(
        [
            "MATCH (source)-[rel]->(target)",
            "RETURN source, labels(source) AS source_labels,",
            "       target, labels(target) AS target_labels,",
            "       type(rel) AS rel_type, rel.label AS rel_label",
        ]
    )


def _node_from_record(payload: Mapping[str, str], labels: list[str] | None) -> GraphNode:
    primary_label = labels[0] if labels else "Node"
    raw_id = payload["id"]
    label = payload.get("label") or payload.get("name") or raw_id
    return GraphNode(
        id=_node_id(primary_label, raw_id),
        label=label,
        type=_node_type(primary_label),
    )


def map_neo4j_records_to_graph_response(records: list[dict]) -> GraphResponse:
    nodes: dict[str, GraphNode] = {}
    edges: list[GraphEdge] = []
    edge_keys: set[tuple[str, str, str, str]] = set()

    for row in records:
        center_payload = row.get("center")
        if not center_payload:
            continue

        center_node = _node_from_record(center_payload, row.get("center_labels"))
        nodes[center_node.id] = center_node

        neighbor_payload = row.get("neighbor")
        rel_type = row.get("rel_type")
        if not neighbor_payload or not rel_type:
            continue

        neighbor_node = _node_from_record(neighbor_payload, row.get("neighbor_labels"))
        nodes[neighbor_node.id] = neighbor_node
        edge_label = row.get("rel_label") or rel_type
        edge_type = REL_TYPE_MAP.get(rel_type, rel_type.lower())
        edge_key = (center_node.id, neighbor_node.id, edge_label, edge_type)
        if edge_key in edge_keys:
            continue
        edge_keys.add(edge_key)
        edges.append(
            GraphEdge(
                source=center_node.id,
                target=neighbor_node.id,
                label=edge_label,
                type=edge_type,
            )
        )

    return GraphResponse(nodes=list(nodes.values()), edges=edges)


def map_neo4j_relationship_records_to_graph_response(records: list[dict]) -> GraphResponse:
    nodes: dict[str, GraphNode] = {}
    edges: list[GraphEdge] = []
    edge_keys: set[tuple[str, str, str, str]] = set()

    for row in records:
        source_payload = row.get("source")
        target_payload = row.get("target")
        rel_type = row.get("rel_type")
        if not source_payload or not target_payload or not rel_type:
            continue

        source_node = _node_from_record(source_payload, row.get("source_labels"))
        target_node = _node_from_record(target_payload, row.get("target_labels"))
        nodes[source_node.id] = source_node
        nodes[target_node.id] = target_node

        edge_label = row.get("rel_label") or rel_type
        edge_type = REL_TYPE_MAP.get(rel_type, rel_type.lower())
        edge_key = (source_node.id, target_node.id, edge_label, edge_type)
        if edge_key in edge_keys:
            continue
        edge_keys.add(edge_key)
        edges.append(
            GraphEdge(
                source=source_node.id,
                target=target_node.id,
                label=edge_label,
                type=edge_type,
            )
        )

    return GraphResponse(nodes=list(nodes.values()), edges=edges)
