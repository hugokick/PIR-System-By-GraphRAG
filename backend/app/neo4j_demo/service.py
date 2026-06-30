import os
import threading
from collections.abc import Iterable, Mapping
from typing import Any

from app.schemas import ExhibitResponse, GraphResponse
from app.services.graph import build_exhibit_graph

from .demo_data import neo4j_demo_exhibits
from .query import (
    build_demo_graph_cypher,
    build_exhibit_graph_cypher,
    map_neo4j_records_to_graph_response,
    map_neo4j_relationship_records_to_graph_response,
)
from .seed import build_demo_seed_statements


TRUTHY_VALUES = {"1", "true", "yes", "on"}
_demo_graph_seeded = False
_demo_graph_seed_lock = threading.Lock()


def _with_demo_exhibits(exhibits: Iterable[ExhibitResponse]) -> list[ExhibitResponse]:
    merged = {item.id: item for item in neo4j_demo_exhibits}
    for exhibit in exhibits:
        merged[exhibit.id] = exhibit
    return list(merged.values())


class Neo4jBoltGraphClient:
    """Thin adapter around a Neo4j-like driver that supports session().run()."""

    def __init__(self, driver: Any):
        self.driver = driver

    def fetch_exhibit_graph(self, exhibit_id: str) -> list[dict]:
        query = build_exhibit_graph_cypher(exhibit_id)
        with self.driver.session() as session:
            result = session.run(query, exhibit_id=exhibit_id)
            return [record.data() for record in result]

    def fetch_demo_graph(self) -> list[dict]:
        query = build_demo_graph_cypher()
        with self.driver.session() as session:
            result = session.run(query)
            return [record.data() for record in result]

    def execute_statements(self, statements: Iterable[str]) -> None:
        with self.driver.session() as session:
            for statement in statements:
                session.run(statement).consume()

    def close(self) -> None:
        self.driver.close()


class Neo4jDemoGraphService:
    def __init__(
        self,
        client: Any | None = None,
        exhibits: Iterable[ExhibitResponse] | None = None,
        auto_seed: bool = False,
    ):
        self.client = client
        self.exhibits = list(exhibits or neo4j_demo_exhibits)
        self.auto_seed = auto_seed

    def build_query(self, exhibit_id: str) -> str:
        return build_exhibit_graph_cypher(exhibit_id)

    def get_exhibit_graph(self, exhibit_id: str) -> GraphResponse:
        if self.client is None:
            return self._fallback(exhibit_id)

        try:
            if self.auto_seed:
                self._seed_once()
            rows = self.client.fetch_exhibit_graph(exhibit_id)
        except Exception:
            return self._fallback(exhibit_id)

        if not rows:
            return self._fallback(exhibit_id)

        graph = map_neo4j_records_to_graph_response(rows)
        fallback = self._fallback(exhibit_id)
        if not graph.nodes:
            return fallback
        if not graph.edges and fallback.edges:
            return fallback
        return graph

    def get_demo_graph(self) -> GraphResponse:
        if self.client is None:
            return self._fallback_demo_graph()

        try:
            if self.auto_seed:
                self._seed_once()
            rows = self.client.fetch_demo_graph()
        except Exception:
            return self._fallback_demo_graph()

        if not rows:
            return self._fallback_demo_graph()

        graph = map_neo4j_relationship_records_to_graph_response(rows)
        if not graph.nodes:
            return self._fallback_demo_graph()
        return graph

    def _fallback(self, exhibit_id: str) -> GraphResponse:
        exhibit = next((item for item in self.exhibits if item.id == exhibit_id), None)
        if exhibit is None:
            return GraphResponse(nodes=[], edges=[])
        return build_exhibit_graph(exhibit, self.exhibits)

    def _fallback_demo_graph(self) -> GraphResponse:
        nodes = {}
        edges = []
        edge_keys = set()
        for exhibit in self.exhibits:
            graph = build_exhibit_graph(exhibit, self.exhibits)
            for node in graph.nodes:
                nodes[node.id] = node
            for edge in graph.edges:
                edge_key = (edge.source, edge.target, edge.label, edge.type)
                if edge_key in edge_keys:
                    continue
                edge_keys.add(edge_key)
                edges.append(edge)
        return GraphResponse(nodes=list(nodes.values()), edges=edges)

    def close(self) -> None:
        if self.client is not None and hasattr(self.client, "close"):
            self.client.close()

    def _seed_once(self) -> None:
        global _demo_graph_seeded
        with _demo_graph_seed_lock:
            if _demo_graph_seeded:
                return
            if not hasattr(self.client, "execute_statements"):
                return
            self.client.execute_statements(build_demo_seed_statements(self.exhibits))
            _demo_graph_seeded = True


def create_neo4j_demo_graph_service(
    exhibits: Iterable[ExhibitResponse],
    env: Mapping[str, str] | None = None,
) -> Neo4jDemoGraphService:
    source = env if env is not None else os.environ
    graph_exhibits = _with_demo_exhibits(exhibits)
    enabled = source.get("NEO4J_DEMO_ENABLED", "").strip().lower() in TRUTHY_VALUES
    if not enabled:
        return Neo4jDemoGraphService(exhibits=graph_exhibits)

    uri = source.get("NEO4J_URI")
    password = source.get("NEO4J_PASSWORD")
    user = source.get("NEO4J_USER", "neo4j")
    if not uri or not password:
        return Neo4jDemoGraphService(exhibits=graph_exhibits)

    try:
        from neo4j import GraphDatabase
    except ImportError:
        return Neo4jDemoGraphService(exhibits=graph_exhibits)

    driver = GraphDatabase.driver(uri, auth=(user, password))
    auto_seed = source.get("NEO4J_DEMO_AUTO_SEED", "").strip().lower() in TRUTHY_VALUES
    return Neo4jDemoGraphService(
        client=Neo4jBoltGraphClient(driver),
        exhibits=graph_exhibits,
        auto_seed=auto_seed,
    )
