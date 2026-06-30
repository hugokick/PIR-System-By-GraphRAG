from ..schemas import ExhibitResponse, GraphEdge, GraphNode, GraphResponse


def build_exhibit_graph(exhibit: ExhibitResponse, all_exhibits: list[ExhibitResponse]) -> GraphResponse:
    nodes: dict[str, GraphNode] = {}
    edges: list[GraphEdge] = []

    def add_node(node_id: str, label: str, node_type: str) -> None:
        nodes[node_id] = GraphNode(id=node_id, label=label, type=node_type)

    def add_edge(target: str, label: str, edge_type: str) -> None:
        edges.append(
            GraphEdge(
                source=f"exhibit:{exhibit.id}",
                target=target,
                label=label,
                type=edge_type,
            )
        )

    add_node(f"exhibit:{exhibit.id}", exhibit.name, "exhibit")

    project_id = f"project:{exhibit.project.id}"
    add_node(project_id, exhibit.project.name, "project")
    add_edge(project_id, "所属项目", "belongs_to_project")

    owner_id = f"owner:{exhibit.owner.id}"
    add_node(owner_id, exhibit.owner.name, "owner")
    add_edge(owner_id, "业主", "owned_by")

    supplier_id = f"supplier:{exhibit.supplier.id}"
    add_node(supplier_id, exhibit.supplier.name, "supplier")
    add_edge(supplier_id, "供应商", "supplied_by")

    theme_id = f"theme:{exhibit.theme.id}"
    add_node(theme_id, exhibit.theme.name, "theme")
    add_edge(theme_id, "主题", "has_theme")

    for material in exhibit.materials:
        material_id = f"material:{material.id}"
        add_node(material_id, material.name, "material")
        add_edge(material_id, "使用材料", "uses_material")

    for interaction in exhibit.interactions:
        interaction_id = f"interaction:{interaction.id}"
        add_node(interaction_id, interaction.name, "interaction")
        add_edge(interaction_id, "交互方式", "has_interaction")

    for asset in exhibit.media_assets:
        asset_id = f"media_asset:{asset.id}"
        add_node(asset_id, asset.name, "media_asset")
        add_edge(asset_id, "媒体资产", "has_media")

    for document in exhibit.documents:
        document_id = f"document:{document.id}"
        add_node(document_id, document.name, "document")
        add_edge(document_id, "文档资料", "has_document")

    related_by_id = {item.id: item for item in all_exhibits}
    for related_id in exhibit.related_exhibit_ids:
        related = related_by_id.get(related_id)
        if related is None:
            continue
        node_id = f"exhibit:{related.id}"
        add_node(node_id, related.name, "exhibit")
        add_edge(node_id, "相似展项", "similar_to")

    return GraphResponse(nodes=list(nodes.values()), edges=edges)
