from app.neo4j_demo.service import Neo4jDemoGraphService
from app.schemas import GraphResponse


class FailingClient:
    def fetch_exhibit_graph(self, exhibit_id: str):
        raise RuntimeError("neo4j unavailable")


class EmptyClient:
    def fetch_exhibit_graph(self, exhibit_id: str):
        return []


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
