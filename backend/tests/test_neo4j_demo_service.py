from app.neo4j_demo.service import Neo4jDemoGraphService
from app.repository import seed_exhibits
from app.schemas import GraphResponse


class FailingClient:
    def fetch_exhibit_graph(self, exhibit_id: str):
        raise RuntimeError("neo4j unavailable")


class EmptyClient:
    def fetch_exhibit_graph(self, exhibit_id: str):
        return []


class CenterOnlyClient:
    def fetch_exhibit_graph(self, exhibit_id: str):
        return [
            {
                "center": {"id": exhibit_id, "name": "Source Exhibit"},
                "center_labels": ["Exhibit"],
                "neighbor": None,
                "neighbor_labels": None,
                "rel_type": None,
                "rel_label": None,
            }
        ]


class HappyClient:
    def fetch_exhibit_graph(self, exhibit_id: str):
        return [
            {
                "center": {"id": exhibit_id, "name": "杠杆乐园"},
                "center_labels": ["Exhibit"],
                "neighbor": {"id": "qisi", "name": "启思互动工坊"},
                "neighbor_labels": ["Supplier"],
                "rel_type": "SUPPLIED_BY",
                "rel_label": "供应商",
            }
        ]

    def fetch_demo_graph(self):
        return [
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


class SeedingClient(HappyClient):
    def __init__(self):
        self.seeded_statements = []

    def execute_statements(self, statements):
        self.seeded_statements.extend(statements)


def test_service_falls_back_when_client_errors():
    service = Neo4jDemoGraphService(client=FailingClient())

    result = service.get_exhibit_graph("lever-play")

    assert isinstance(result, GraphResponse)
    assert result.nodes
    assert result.edges
    assert any(edge.type == "belongs_to_project" for edge in result.edges)


def test_service_falls_back_when_client_returns_no_rows():
    service = Neo4jDemoGraphService(client=EmptyClient())

    result = service.get_exhibit_graph("lever-play")

    assert isinstance(result, GraphResponse)
    assert result.nodes
    assert any(node.id == "exhibit:lever-play" for node in result.nodes)


def test_service_falls_back_when_neo4j_returns_center_without_relationships():
    source = seed_exhibits[0].model_copy(update={"id": "source-demo", "related_exhibit_ids": ["target-demo"]})
    target = seed_exhibits[1].model_copy(update={"id": "target-demo", "related_exhibit_ids": []})
    service = Neo4jDemoGraphService(client=CenterOnlyClient(), exhibits=[source, target])

    result = service.get_exhibit_graph("source-demo")

    assert any(edge.type == "similar_to" and edge.target == "exhibit:target-demo" for edge in result.edges)


def test_service_default_fallback_uses_demo_exhibits():
    service = Neo4jDemoGraphService(client=EmptyClient())

    result = service.get_exhibit_graph("space-dome")

    assert isinstance(result, GraphResponse)
    assert any(node.id == "exhibit:space-dome" for node in result.nodes)
    assert any(edge.type == "has_document" for edge in result.edges)


def test_service_prefers_neo4j_rows_when_available():
    service = Neo4jDemoGraphService(client=HappyClient())

    result = service.get_exhibit_graph("lever-play")

    assert isinstance(result, GraphResponse)
    assert any(node.id == "supplier:qisi" for node in result.nodes)
    assert result.edges[0].type == "supplied_by"


def test_service_returns_full_demo_graph_from_neo4j_rows_when_available():
    service = Neo4jDemoGraphService(client=HappyClient())

    result = service.get_demo_graph()

    node_ids = {node.id for node in result.nodes}
    edge_types = {edge.type for edge in result.edges}
    assert {"exhibit:lever-play", "supplier:qisi", "exhibit:space-dome", "theme:astronomy"} <= node_ids
    assert {"supplied_by", "has_theme"} <= edge_types


def test_service_full_demo_graph_fallback_includes_all_four_demo_exhibits():
    service = Neo4jDemoGraphService(client=EmptyClient())

    result = service.get_demo_graph()

    exhibit_node_ids = {node.id for node in result.nodes if node.type == "exhibit"}
    assert {"exhibit:lever-play", "exhibit:pulley-wall", "exhibit:water-cycle", "exhibit:space-dome"} <= exhibit_node_ids
    assert len(result.edges) >= 20


def test_service_build_query_exposes_cypher_for_review():
    service = Neo4jDemoGraphService(client=HappyClient())

    query = service.build_query("lever-play")

    assert "MATCH (center:Exhibit {id: $exhibit_id})" in query


def test_service_auto_seeds_before_fetch_when_configured():
    client = SeedingClient()
    service = Neo4jDemoGraphService(client=client, auto_seed=True)

    result = service.get_exhibit_graph("lever-play")

    assert result.nodes
    assert client.seeded_statements
    assert client.seeded_statements[0] == "MATCH (n) DETACH DELETE n"
