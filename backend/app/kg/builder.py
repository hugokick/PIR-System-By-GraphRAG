from collections import defaultdict

from app.schemas import ExhibitResponse

from .extractors import document_evidences, exhibit_evidence, exhibit_node
from .models import KGEdge, KGNode, KGSnapshot


def build_exhibit_kg_snapshot(exhibits: list[ExhibitResponse]) -> KGSnapshot:
    nodes: dict[str, KGNode] = {}
    edges: list[KGEdge] = []
    evidences = []
    adjacency: dict[str, list[str]] = defaultdict(list)
    warnings: list[str] = []
    exhibits_by_id = {item.id: item for item in exhibits}

    def add_node(node: KGNode) -> None:
        nodes[node.id] = node

    def add_edge(edge: KGEdge) -> None:
        edges.append(edge)
        adjacency[edge.source].append(edge.target)

    for exhibit in exhibits:
        exhibit_node_id = f"exhibit:{exhibit.id}"
        add_node(exhibit_node(exhibit))
        evidences.append(exhibit_evidence(exhibit))
        evidences.extend(document_evidences(exhibit))

        single_relations = [
            ("project", exhibit.project.id, exhibit.project.name, "belongs_to_project", "所属项目"),
            ("owner", exhibit.owner.id, exhibit.owner.name, "owned_by", "业主"),
            ("supplier", exhibit.supplier.id, exhibit.supplier.name, "supplied_by", "供应商"),
            ("theme", exhibit.theme.id, exhibit.theme.name, "has_theme", "主题"),
        ]
        for node_type, raw_id, label, edge_type, edge_label in single_relations:
            target_id = f"{node_type}:{raw_id}"
            add_node(KGNode(id=target_id, type=node_type, label=label, source_refs=[f"exhibit:{exhibit.id}"]))
            add_edge(
                KGEdge(
                    source=exhibit_node_id,
                    target=target_id,
                    type=edge_type,
                    label=edge_label,
                    source_refs=[f"exhibit:{exhibit.id}"],
                )
            )

        for material in exhibit.materials:
            target_id = f"material:{material.id}"
            add_node(KGNode(id=target_id, type="material", label=material.name, source_refs=[f"exhibit:{exhibit.id}"]))
            add_edge(
                KGEdge(
                    source=exhibit_node_id,
                    target=target_id,
                    type="uses_material",
                    label="使用材料",
                    source_refs=[f"exhibit:{exhibit.id}"],
                )
            )

        for interaction in exhibit.interactions:
            target_id = f"interaction:{interaction.id}"
            add_node(
                KGNode(
                    id=target_id,
                    type="interaction",
                    label=interaction.name,
                    source_refs=[f"exhibit:{exhibit.id}"],
                )
            )
            add_edge(
                KGEdge(
                    source=exhibit_node_id,
                    target=target_id,
                    type="has_interaction",
                    label="交互方式",
                    source_refs=[f"exhibit:{exhibit.id}"],
                )
            )

        for asset in exhibit.media_assets:
            target_id = f"media_asset:{asset.id}"
            add_node(
                KGNode(
                    id=target_id,
                    type="media_asset",
                    label=asset.name,
                    source_refs=[f"exhibit:{exhibit.id}", f"media_asset:{asset.id}"],
                )
            )
            add_edge(
                KGEdge(
                    source=exhibit_node_id,
                    target=target_id,
                    type="has_media",
                    label="媒体资产",
                    source_refs=[f"exhibit:{exhibit.id}", f"media_asset:{asset.id}"],
                )
            )

        for document in exhibit.documents:
            target_id = f"document:{document.id}"
            add_node(
                KGNode(
                    id=target_id,
                    type="document",
                    label=document.name,
                    source_refs=[f"exhibit:{exhibit.id}", f"document:{document.id}"],
                )
            )
            add_edge(
                KGEdge(
                    source=exhibit_node_id,
                    target=target_id,
                    type="has_document",
                    label="文档资料",
                    source_refs=[f"exhibit:{exhibit.id}", f"document:{document.id}"],
                )
            )

        for related_id in exhibit.related_exhibit_ids:
            if related_id not in exhibits_by_id:
                warnings.append(f"Missing related exhibit target: {related_id}")
                continue
            add_edge(
                KGEdge(
                    source=exhibit_node_id,
                    target=f"exhibit:{related_id}",
                    type="similar_to",
                    label="相似展项",
                    source_refs=[f"exhibit:{exhibit.id}", f"exhibit:{related_id}"],
                )
            )

    return KGSnapshot(
        nodes=list(nodes.values()),
        edges=edges,
        evidences=evidences,
        adjacency=dict(adjacency),
        warnings=warnings,
    )
