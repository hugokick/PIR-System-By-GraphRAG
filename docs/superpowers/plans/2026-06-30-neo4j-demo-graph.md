# Neo4j Demo Graph Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an isolated Neo4j demo graph branch that can seed exhibit-domain graph data, query a center exhibit neighborhood, map Neo4j results to `GraphResponse`-compatible `nodes/edges`, and fall back to the existing Python graph when Neo4j is unavailable.

**Architecture:** Add a dedicated `backend/app/neo4j_demo/` package with four focused responsibilities: seed generation, Cypher query composition, Neo4j result mapping, and a small service layer that prefers Neo4j then falls back to the current Python graph builder. Keep all functionality route-free and independent from CRUD, GraphRAG routes, vector search, and database dual-write.

**Tech Stack:** Python, Pydantic, existing `backend/app/schemas.py`, existing exhibit seed data, optional Neo4j Python driver compatibility via adapter-style interfaces, pytest.

---

### Task 1: Define Failing Neo4j Demo Tests

**Files:**
- Create: `backend/tests/test_neo4j_demo_seed.py`
- Create: `backend/tests/test_neo4j_demo_query.py`
- Create: `backend/tests/test_neo4j_demo_service.py`

- [ ] **Step 1: Write the failing seed coverage**

```python
from app.neo4j_demo.seed import build_demo_seed_statements
from app.repository import seed_exhibits


def test_build_demo_seed_statements_contains_expected_labels_and_relationships():
    statements = build_demo_seed_statements(seed_exhibits)
    script = "\n".join(statements)

    assert "MERGE (e:Exhibit" in script
    assert "MERGE (p:Project" in script
    assert "MERGE (o:Owner" in script
    assert "MERGE (s:Supplier" in script
    assert "MERGE (m:Material" in script
    assert "MERGE (t:Theme" in script
    assert "MERGE (i:Interaction" in script
    assert "MERGE (d:Document" in script
    assert "SIMILAR_TO" in script
```

- [ ] **Step 2: Write the failing query and mapping coverage**

```python
from app.neo4j_demo.query import build_exhibit_graph_cypher, map_neo4j_records_to_graph_response


def test_build_exhibit_graph_cypher_targets_exhibit_id():
    cypher = build_exhibit_graph_cypher("lever-play")

    assert "MATCH (center:Exhibit" in cypher
    assert "$exhibit_id" in cypher
    assert "OPTIONAL MATCH" in cypher


def test_map_neo4j_records_to_graph_response_returns_nodes_and_edges():
    records = [
        {
            "center": {"id": "lever-play", "name": "杠杆乐园", "label": "杠杆乐园"},
            "center_labels": ["Exhibit"],
            "neighbor": {"id": "qinghe-2024", "name": "青禾儿童科技馆更新项目", "label": "青禾儿童科技馆更新项目"},
            "neighbor_labels": ["Project"],
            "rel_type": "BELONGS_TO_PROJECT",
            "rel_label": "所属项目",
        }
    ]

    graph = map_neo4j_records_to_graph_response(records)

    assert any(node.id == "lever-play" and node.type == "Exhibit" for node in graph.nodes)
    assert any(node.id == "qinghe-2024" and node.type == "Project" for node in graph.nodes)
    assert any(edge.source == "lever-play" and edge.target == "qinghe-2024" for edge in graph.edges)
```

- [ ] **Step 3: Write the failing fallback service coverage**

```python
from app.neo4j_demo.service import Neo4jDemoGraphService
from app.schemas import GraphResponse


class FailingClient:
    def fetch_exhibit_graph(self, exhibit_id: str):
        raise RuntimeError("neo4j unavailable")


class EmptyClient:
    def fetch_exhibit_graph(self, exhibit_id: str):
        return []


def test_service_falls_back_when_client_errors():
    service = Neo4jDemoGraphService(client=FailingClient())

    result = service.get_exhibit_graph("lever-play")

    assert isinstance(result, GraphResponse)
    assert result.nodes
    assert result.edges


def test_service_falls_back_when_client_returns_no_rows():
    service = Neo4jDemoGraphService(client=EmptyClient())

    result = service.get_exhibit_graph("lever-play")

    assert isinstance(result, GraphResponse)
    assert result.nodes
```

- [ ] **Step 4: Run tests to verify they fail**

Run: `python -m pytest backend/tests/test_neo4j_demo_seed.py backend/tests/test_neo4j_demo_query.py backend/tests/test_neo4j_demo_service.py -q`
Expected: FAIL with `ModuleNotFoundError` for `app.neo4j_demo`

- [ ] **Step 5: Commit**

```bash
git add backend/tests/test_neo4j_demo_seed.py backend/tests/test_neo4j_demo_query.py backend/tests/test_neo4j_demo_service.py
git commit -m "test: add neo4j demo graph coverage"
```

### Task 2: Implement Neo4j Demo Seed and Query Layer

**Files:**
- Create: `backend/app/neo4j_demo/__init__.py`
- Create: `backend/app/neo4j_demo/seed.py`
- Create: `backend/app/neo4j_demo/query.py`

- [ ] **Step 1: Add package exports**

```python
from .query import build_exhibit_graph_cypher, map_neo4j_records_to_graph_response
from .seed import build_demo_seed_statements

__all__ = [
    "build_demo_seed_statements",
    "build_exhibit_graph_cypher",
    "map_neo4j_records_to_graph_response",
]
```

- [ ] **Step 2: Implement minimal seed generator**

```python
from app.schemas import ExhibitResponse


def build_demo_seed_statements(exhibits: list[ExhibitResponse]) -> list[str]:
    statements: list[str] = []
    for exhibit in exhibits:
        statements.append(
            f"MERGE (e:Exhibit {{id: '{exhibit.id}'}}) "
            f"SET e.name = '{exhibit.name}', e.label = '{exhibit.name}'"
        )
        statements.append(
            f"MERGE (p:Project {{id: '{exhibit.project.id}'}}) "
            f"SET p.name = '{exhibit.project.name}', p.label = '{exhibit.project.name}'"
        )
        statements.append(
            f"MERGE (o:Owner {{id: '{exhibit.owner.id}'}}) "
            f"SET o.name = '{exhibit.owner.name}', o.label = '{exhibit.owner.name}'"
        )
        statements.append(
            f"MERGE (s:Supplier {{id: '{exhibit.supplier.id}'}}) "
            f"SET s.name = '{exhibit.supplier.name}', s.label = '{exhibit.supplier.name}'"
        )
        statements.append(
            f"MERGE (t:Theme {{id: '{exhibit.theme.id}'}}) "
            f"SET t.name = '{exhibit.theme.name}', t.label = '{exhibit.theme.name}'"
        )
        statements.append(
            f"MERGE (e)-[:BELONGS_TO_PROJECT {{label: '所属项目'}}]->(p)"
        )
        statements.append(
            f"MERGE (e)-[:OWNED_BY {{label: '业主'}}]->(o)"
        )
        statements.append(
            f"MERGE (e)-[:SUPPLIED_BY {{label: '供应商'}}]->(s)"
        )
        statements.append(
            f"MERGE (e)-[:HAS_THEME {{label: '主题'}}]->(t)"
        )
        for material in exhibit.materials:
            statements.append(
                f"MERGE (m:Material {{id: '{material.id}'}}) "
                f"SET m.name = '{material.name}', m.label = '{material.name}'"
            )
            statements.append(
                f"MERGE (e)-[:USES_MATERIAL {{label: '使用材料'}}]->(m)"
            )
        for interaction in exhibit.interactions:
            statements.append(
                f"MERGE (i:Interaction {{id: '{interaction.id}'}}) "
                f"SET i.name = '{interaction.name}', i.label = '{interaction.name}'"
            )
            statements.append(
                f"MERGE (e)-[:HAS_INTERACTION {{label: '交互方式'}}]->(i)"
            )
        for document in exhibit.documents:
            statements.append(
                f"MERGE (d:Document {{id: '{document.id}'}}) "
                f"SET d.name = '{document.name}', d.label = '{document.name}'"
            )
            statements.append(
                f"MERGE (e)-[:HAS_DOCUMENT {{label: '文档资料'}}]->(d)"
            )
        for related_id in exhibit.related_exhibit_ids:
            statements.append(
                f"MERGE (target:Exhibit {{id: '{related_id}'}})"
            )
            statements.append(
                f"MERGE (e)-[:SIMILAR_TO {{label: '相似展项'}}]->(target)"
            )
    return statements
```

- [ ] **Step 3: Implement minimal query and mapping layer**

```python
from app.schemas import GraphEdge, GraphNode, GraphResponse


def build_exhibit_graph_cypher(exhibit_id: str) -> str:
    _ = exhibit_id
    return """
    MATCH (center:Exhibit {id: $exhibit_id})
    OPTIONAL MATCH (center)-[rel]->(neighbor)
    RETURN center, labels(center) AS center_labels,
           neighbor, labels(neighbor) AS neighbor_labels,
           type(rel) AS rel_type, rel.label AS rel_label
    """


def map_neo4j_records_to_graph_response(records: list[dict]) -> GraphResponse:
    nodes: dict[str, GraphNode] = {}
    edges: list[GraphEdge] = []

    for row in records:
        center = row["center"]
        center_type = row["center_labels"][0] if row.get("center_labels") else "Exhibit"
        nodes[center["id"]] = GraphNode(
            id=center["id"],
            label=center.get("label", center.get("name", center["id"])),
            type=center_type,
        )

        neighbor = row.get("neighbor")
        if not neighbor:
            continue

        neighbor_type = row["neighbor_labels"][0] if row.get("neighbor_labels") else "Node"
        nodes[neighbor["id"]] = GraphNode(
            id=neighbor["id"],
            label=neighbor.get("label", neighbor.get("name", neighbor["id"])),
            type=neighbor_type,
        )
        edges.append(
            GraphEdge(
                source=center["id"],
                target=neighbor["id"],
                label=row.get("rel_label") or row.get("rel_type") or "",
                type=row.get("rel_type") or "RELATED_TO",
            )
        )

    return GraphResponse(nodes=list(nodes.values()), edges=edges)
```

- [ ] **Step 4: Run targeted tests to verify they pass**

Run: `python -m pytest backend/tests/test_neo4j_demo_seed.py backend/tests/test_neo4j_demo_query.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/neo4j_demo/__init__.py backend/app/neo4j_demo/seed.py backend/app/neo4j_demo/query.py
git commit -m "feat: add neo4j demo seed and query layer"
```

### Task 3: Implement Neo4j Demo Service with Fallback

**Files:**
- Create: `backend/app/neo4j_demo/service.py`
- Modify: `backend/app/neo4j_demo/__init__.py`

- [ ] **Step 1: Implement service adapter and fallback behavior**

```python
from app.repository import seed_exhibits
from app.schemas import GraphResponse
from app.services.graph import build_exhibit_graph

from .query import build_exhibit_graph_cypher, map_neo4j_records_to_graph_response


class Neo4jDemoClientProtocol:
    def fetch_exhibit_graph(self, exhibit_id: str):
        raise NotImplementedError


class Neo4jDemoGraphService:
    def __init__(self, client=None, exhibits=None):
        self.client = client
        self.exhibits = list(exhibits or seed_exhibits)

    def get_exhibit_graph(self, exhibit_id: str) -> GraphResponse:
        if self.client is None:
            return self._fallback(exhibit_id)
        try:
            rows = self.client.fetch_exhibit_graph(exhibit_id)
        except Exception:
            return self._fallback(exhibit_id)
        if not rows:
            return self._fallback(exhibit_id)
        return map_neo4j_records_to_graph_response(rows)

    def build_query(self, exhibit_id: str) -> str:
        return build_exhibit_graph_cypher(exhibit_id)

    def _fallback(self, exhibit_id: str) -> GraphResponse:
        exhibit = next((item for item in self.exhibits if item.id == exhibit_id), None)
        if exhibit is None:
            return GraphResponse(nodes=[], edges=[])
        return build_exhibit_graph(exhibit, self.exhibits)
```

- [ ] **Step 2: Export service symbols**

```python
from .query import build_exhibit_graph_cypher, map_neo4j_records_to_graph_response
from .seed import build_demo_seed_statements
from .service import Neo4jDemoGraphService

__all__ = [
    "build_demo_seed_statements",
    "build_exhibit_graph_cypher",
    "map_neo4j_records_to_graph_response",
    "Neo4jDemoGraphService",
]
```

- [ ] **Step 3: Run service tests**

Run: `python -m pytest backend/tests/test_neo4j_demo_service.py -q`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add backend/app/neo4j_demo/service.py backend/app/neo4j_demo/__init__.py
git commit -m "feat: add neo4j demo fallback service"
```

### Task 4: Write Integration Documentation

**Files:**
- Create: `docs/neo4j-demo-graph-integration.md`

- [ ] **Step 1: Add operator-facing integration doc**

```markdown
# Neo4j 演示图谱接入说明

## 1. 目标

本支线用于提供 Neo4j 演示图谱能力，为前端知识图谱窗口提供可展示的 Neo4j 查询结果。

## 2. 如何启动 Neo4j

- 使用本地 Neo4j Desktop 或 Docker
- 推荐默认端口：`7474`（HTTP）与 `7687`（Bolt）

## 3. 如何导入演示数据

- 使用 `build_demo_seed_statements()` 生成 Cypher
- 在 Neo4j Browser 中执行生成脚本

## 4. 如何接入现有 `/api/exhibits/{id}/graph`

- 当前不直接修改该路由
- 后续主线可在 `services/graph.py` 外层增加开关：
  - 优先调用 `Neo4jDemoGraphService`
  - Neo4j 不可用时回退到当前 Python 图谱

## 5. 当前为什么不做双写同步

- 当前 Neo4j 仅用于演示
- 主库仍以现有存储为准
- 过早双写会增加一致性复杂度

## 6. 后续如何演进

- PostgreSQL 保持主库
- 通过定时或事件投影同步到 Neo4j
- Neo4j 只作为图谱查询投影库
```

- [ ] **Step 2: Commit**

```bash
git add docs/neo4j-demo-graph-integration.md
git commit -m "docs: add neo4j demo graph integration guide"
```

### Task 5: Final Verification and Push

**Files:**
- Verify only

- [ ] **Step 1: Run the full backend test suite**

Run: `python -m pytest backend/tests -q`
Expected: PASS with all tests green

- [ ] **Step 2: Confirm branch and worktree state**

Run: `git status --short --branch`
Expected: `## hermes/neo4j-demo-graph` and no pending changes

- [ ] **Step 3: Push feature branch**

Run: `git push -u origin hermes/neo4j-demo-graph`
Expected: remote branch created or updated successfully

- [ ] **Step 4: Commit any remaining tracked changes if needed**

```bash
git add -A
git commit -m "chore: finalize neo4j demo graph branch"
```

- [ ] **Step 5: Re-verify after push**

Run: `git status --short --branch && git log --oneline -n 5`
Expected: clean worktree and latest Neo4j demo commits visible
