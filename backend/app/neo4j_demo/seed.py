from collections.abc import Iterable

from app.schemas import ExhibitResponse


def _quote(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")


def _merge_node_statement(
    alias: str,
    label: str,
    node_id: str,
    name: str,
    extra_fields: dict[str, str] | None = None,
) -> str:
    assignments = [
        f"{alias}.name = '{_quote(name)}'",
        f"{alias}.label = '{_quote(name)}'",
        f"{alias}.名称 = '{_quote(name)}'",
    ]
    for key, value in (extra_fields or {}).items():
        assignments.append(f"{alias}.{key} = '{_quote(value)}'")
    return f"MERGE ({alias}:{label} {{id: '{_quote(node_id)}'}}) SET " + ", ".join(assignments)


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
                _merge_node_statement(
                    "e",
                    "Exhibit",
                    exhibit.id,
                    exhibit.name,
                    {
                        "类别": exhibit.category,
                        "主题": exhibit.theme.name,
                        "馆型": exhibit.venue_type,
                        "供应商名称": exhibit.supplier.name,
                        "业主名称": exhibit.owner.name,
                        "状态": exhibit.status,
                        "项目年份": str(exhibit.project_year),
                    },
                ),
                _merge_node_statement("p", "Project", exhibit.project.id, exhibit.project.name),
                _merge_node_statement("o", "Owner", exhibit.owner.id, exhibit.owner.name),
                _merge_node_statement("s", "Supplier", exhibit.supplier.id, exhibit.supplier.name),
                _merge_node_statement("t", "Theme", exhibit.theme.id, exhibit.theme.name),
                _merge_edge_statement("e", "BELONGS_TO_PROJECT", "所属项目", "p"),
                _merge_edge_statement("e", "OWNED_BY", "业主", "o"),
                _merge_edge_statement("e", "SUPPLIED_BY", "供应商", "s"),
                _merge_edge_statement("e", "HAS_THEME", "主题", "t"),
            ]
        )

        for material in exhibit.materials:
            statements.append(
                _merge_node_statement("m", "Material", material.id, material.name)
            )
            statements.append(_merge_edge_statement("e", "USES_MATERIAL", "使用材料", "m"))

        for interaction in exhibit.interactions:
            statements.append(
                _merge_node_statement("i", "Interaction", interaction.id, interaction.name)
            )
            statements.append(_merge_edge_statement("e", "HAS_INTERACTION", "交互方式", "i"))

        for document in exhibit.documents:
            statements.append(
                _merge_node_statement("d", "Document", document.id, document.name)
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
