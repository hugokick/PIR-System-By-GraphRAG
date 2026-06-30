from collections.abc import Iterable
from typing import Any

from app.repository import seed_exhibits
from app.schemas import ExhibitResponse, GraphResponse
from app.services.graph import build_exhibit_graph

from .query import build_exhibit_graph_cypher, map_neo4j_records_to_graph_response


class Neo4jBoltGraphClient:
    """Thin adapter around a Neo4j-like driver that supports session().run()."""

    def __init__(self, driver: Any):
        self.driver = driver

    def fetch_exhibit_graph(self, exhibit_id: str) -> list[dict]:
        query = build_exhibit_graph_cypher(exhibit_id)
        with self.driver.session() as session:
            result = session.run(query, exhibit_id=exhibit_id)
            return [record.data() for record in result]


class Neo4jDemoGraphService:
    def __init__(
        self,
        client: Any | None = None,
        exhibits: Iterable[ExhibitResponse] | None = None,
    ):
        self.client = client
        self.exhibits = list(exhibits or seed_exhibits)

    def build_query(self, exhibit_id: str) -> str:
        return build_exhibit_graph_cypher(exhibit_id)

    def get_exhibit_graph(self, exhibit_id: str) -> GraphResponse:
        if self.client is None:
            return self._fallback(exhibit_id)

        try:
            rows = self.client.fetch_exhibit_graph(exhibit_id)
        except Exception:
            return self._fallback(exhibit_id)

        if not rows:
            return self._fallback(exhibit_id)

        graph = map_neo4j_records_to_graph_response(rows)
        if not graph.nodes:
            return self._fallback(exhibit_id)
        return graph

    def _fallback(self, exhibit_id: str) -> GraphResponse:
        exhibit = next((item for item in self.exhibits if item.id == exhibit_id), None)
        if exhibit is None:
            return GraphResponse(nodes=[], edges=[])
        return build_exhibit_graph(exhibit, self.exhibits)
