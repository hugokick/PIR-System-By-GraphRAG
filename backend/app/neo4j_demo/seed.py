from collections.abc import Iterable

from app.schemas import ExhibitResponse


def _quote(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")


def _merge_node_statement(alias: str, label: str, node_id: str, name: str) -> str:
    return (
        f"MERGE ({alias}:{label} {{id: '{_quote(node_id)}'}}) "
        f"SET {alias}.name = '{_quote(name)}', {alias}.label = '{_quote(name)}'"
    )


def _merge_edge_statement(
    source_label: str,
    source_id: str,
    rel_type: str,
    rel_label: str,
    target_label: str,
    target_id: str,
) -> str:
    return (
        f"MATCH (source:{source_label} {{id: '{_quote(source_id)}'}}), "
        f"(target:{target_label} {{id: '{_quote(target_id)}'}}) "
        f"MERGE (source)-[:{rel_type} {{label: '{_quote(rel_label)}'}}]->(target)"
    )


def build_demo_seed_statements(exhibits: Iterable[ExhibitResponse]) -> list[str]:
    statements = ["MATCH (n) DETACH DELETE n"]

    for exhibit in exhibits:
        statements.extend(
            [
                _merge_node_statement("e", "Exhibit", exhibit.id, exhibit.name),
                _merge_node_statement("p", "Project", exhibit.project.id, exhibit.project.name),
                _merge_node_statement("o", "Owner", exhibit.owner.id, exhibit.owner.name),
                _merge_node_statement("s", "Supplier", exhibit.supplier.id, exhibit.supplier.name),
                _merge_node_statement("t", "Theme", exhibit.theme.id, exhibit.theme.name),
                _merge_edge_statement("Exhibit", exhibit.id, "BELONGS_TO_PROJECT", "project", "Project", exhibit.project.id),
                _merge_edge_statement("Exhibit", exhibit.id, "OWNED_BY", "owner", "Owner", exhibit.owner.id),
                _merge_edge_statement("Exhibit", exhibit.id, "SUPPLIED_BY", "supplier", "Supplier", exhibit.supplier.id),
                _merge_edge_statement("Exhibit", exhibit.id, "HAS_THEME", "theme", "Theme", exhibit.theme.id),
            ]
        )

        for material in exhibit.materials:
            statements.append(_merge_node_statement("m", "Material", material.id, material.name))
            statements.append(
                _merge_edge_statement("Exhibit", exhibit.id, "USES_MATERIAL", "material", "Material", material.id)
            )

        for interaction in exhibit.interactions:
            statements.append(_merge_node_statement("i", "Interaction", interaction.id, interaction.name))
            statements.append(
                _merge_edge_statement(
                    "Exhibit",
                    exhibit.id,
                    "HAS_INTERACTION",
                    "interaction",
                    "Interaction",
                    interaction.id,
                )
            )

        for document in exhibit.documents:
            statements.append(_merge_node_statement("d", "Document", document.id, document.name))
            statements.append(
                _merge_edge_statement("Exhibit", exhibit.id, "HAS_DOCUMENT", "document", "Document", document.id)
            )

        for related_id in exhibit.related_exhibit_ids:
            statements.append(
                f"MERGE (target:Exhibit {{id: '{_quote(related_id)}'}}) "
                "SET target.label = coalesce(target.label, target.id), "
                "target.name = coalesce(target.name, target.id)"
            )
            statements.append(
                _merge_edge_statement("Exhibit", exhibit.id, "SIMILAR_TO", "similar exhibit", "Exhibit", related_id)
            )

    return statements


def build_demo_seed_script(exhibits: Iterable[ExhibitResponse]) -> str:
    statements = build_demo_seed_statements(exhibits)
    header = [
        "// Neo4j demo graph seed",
        "// Paste this script into Neo4j Browser to create the exhibit demo graph.",
    ]
    return "\n".join([*header, *statements]) + "\n"
