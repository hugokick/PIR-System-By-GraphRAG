from collections.abc import Iterable

from app.schemas import ExhibitResponse


def _quote(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")


def _merge_node_statement(label: str, node_id: str, name: str) -> str:
    return (
        f"MERGE (n:{label} {{id: '{_quote(node_id)}'}}) "
        f"SET n.name = '{_quote(name)}', n.label = '{_quote(name)}'"
    )


def _merge_edge_statement(
    source_alias: str,
    rel_type: str,
    rel_label: str,
    target_alias: str,
) -> str:
    return f"MERGE ({source_alias})-[:{rel_type} {{label: '{_quote(rel_label)}'}}]->({target_alias})"


def build_demo_seed_statements(exhibits: Iterable[ExhibitResponse]) -> list[str]:
    statements = ["MATCH (n) DETACH DELETE n"]

    for exhibit in exhibits:
        statements.extend(
            [
                _merge_node_statement("Exhibit", exhibit.id, exhibit.name).replace("(n:", "(e:"),
                _merge_node_statement("Project", exhibit.project.id, exhibit.project.name).replace("(n:", "(p:"),
                _merge_node_statement("Owner", exhibit.owner.id, exhibit.owner.name).replace("(n:", "(o:"),
                _merge_node_statement("Supplier", exhibit.supplier.id, exhibit.supplier.name).replace("(n:", "(s:"),
                _merge_node_statement("Theme", exhibit.theme.id, exhibit.theme.name).replace("(n:", "(t:"),
                _merge_edge_statement("e", "BELONGS_TO_PROJECT", "所属项目", "p"),
                _merge_edge_statement("e", "OWNED_BY", "业主", "o"),
                _merge_edge_statement("e", "SUPPLIED_BY", "供应商", "s"),
                _merge_edge_statement("e", "HAS_THEME", "主题", "t"),
            ]
        )

        for material in exhibit.materials:
            statements.append(
                _merge_node_statement("Material", material.id, material.name).replace("(n:", "(m:")
            )
            statements.append(_merge_edge_statement("e", "USES_MATERIAL", "使用材料", "m"))

        for interaction in exhibit.interactions:
            statements.append(
                _merge_node_statement("Interaction", interaction.id, interaction.name).replace("(n:", "(i:")
            )
            statements.append(_merge_edge_statement("e", "HAS_INTERACTION", "交互方式", "i"))

        for document in exhibit.documents:
            statements.append(
                _merge_node_statement("Document", document.id, document.name).replace("(n:", "(d:")
            )
            statements.append(_merge_edge_statement("e", "HAS_DOCUMENT", "文档资料", "d"))

        for related_id in exhibit.related_exhibit_ids:
            statements.append(
                f"MERGE (target:Exhibit {{id: '{_quote(related_id)}'}})"
            )
            statements.append(
                "SET target.label = coalesce(target.label, target.id), "
                "target.name = coalesce(target.name, target.id)"
            )
            statements.append(_merge_edge_statement("e", "SIMILAR_TO", "相似展项", "target"))

    return statements


def build_demo_seed_script(exhibits: Iterable[ExhibitResponse]) -> str:
    statements = build_demo_seed_statements(exhibits)
    header = [
        "// Neo4j demo graph seed",
        "// Paste this script into Neo4j Browser to create the exhibit demo graph.",
    ]
    return "\n".join([*header, *statements]) + "\n"
