# KG + GraphRAG Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build isolated backend KG construction and rule-based GraphRAG modules, with docs and tests first, without modifying the current MVP mainline flow.

**Architecture:** The implementation adds two pure-Python domains under `backend/app/kg/` and `backend/app/graphrag/`. `kg` converts `ExhibitResponse` records into a reusable graph snapshot, while `graphrag` applies structured filters, rule scoring, one-hop neighborhood expansion, and citation assembly on top of that snapshot.

**Tech Stack:** Python 3, Pydantic, pytest, FastAPI project contracts (`ExhibitResponse`, `EntityRef`, `DocumentAsset`)

---

## File Map

- Create: `backend/app/kg/__init__.py`
- Create: `backend/app/kg/models.py`
- Create: `backend/app/kg/extractors.py`
- Create: `backend/app/kg/builder.py`
- Create: `backend/app/graphrag/__init__.py`
- Create: `backend/app/graphrag/models.py`
- Create: `backend/app/graphrag/search.py`
- Create: `backend/tests/test_kg_builder.py`
- Create: `backend/tests/test_graphrag_search.py`
- Create: `docs/kg-construction-plan.md`
- Modify: `docs/graphrag-design.md`

## Task 1: Land User-Facing Design Docs

**Files:**
- Create: `docs/kg-construction-plan.md`
- Modify: `docs/graphrag-design.md`

- [ ] **Step 1: Write the KG construction plan doc**

```md
# KG Construction Plan

## Fixed Entity Vocabulary

- exhibit
- project
- owner
- supplier
- material
- theme
- interaction
- document

## Fixed Relation Vocabulary

- belongs_to_project
- owned_by
- supplied_by
- uses_material
- has_theme
- has_interaction
- has_document
- similar_to

## Deterministic Build Flow

1. Read `ExhibitResponse` records from the current repository layer.
2. Create one exhibit-centered node set per record.
3. Derive nodes and edges from project, owner, supplier, theme, materials, interactions, documents, and similar exhibits.
4. Emit a `KGSnapshot` with `nodes`, `edges`, `evidences`, `adjacency`, and `warnings`.
5. In a future integration phase, rebuild the exhibit-centered subgraph on create or update.
```

- [ ] **Step 2: Write the GraphRAG design doc update**

```md
# GraphRAG Design

## Current Rule-Based Scope

This phase only implements:

- structured filtering
- rule-based candidate scoring
- one-hop graph neighborhood expansion
- exhibit/document evidence recall
- citation deduplication

## Deferred Scope

- file chunking
- Excel-derived document slices
- pgvector retrieval
- LLM answer generation

## Integration Rule

The isolated module is callable from future route handlers, but no current FastAPI route is changed in this phase.
```

- [ ] **Step 3: Run a quick content check**

Run: `python - <<'PY'\nfrom pathlib import Path\nfor path in [Path('docs/kg-construction-plan.md'), Path('docs/graphrag-design.md')]:\n    text = path.read_text(encoding='utf-8')\n    assert 'TBD' not in text and 'TODO' not in text\nprint('docs-ok')\nPY`

Expected: `docs-ok`

- [ ] **Step 4: Commit**

```bash
git add docs/kg-construction-plan.md docs/graphrag-design.md
git commit -m "docs: add kg and graphrag design docs"
```

## Task 2: Write the KG Tests First

**Files:**
- Create: `backend/tests/test_kg_builder.py`
- Read: `backend/app/schemas.py`
- Read: `backend/app/repository.py`

- [ ] **Step 1: Write the failing KG builder tests**

```python
from app.repository import seed_exhibits
from app.kg.builder import build_exhibit_kg_snapshot


def test_build_snapshot_contains_fixed_node_and_edge_types():
    snapshot = build_exhibit_kg_snapshot(seed_exhibits)

    node_types = {node.type for node in snapshot.nodes}
    edge_types = {edge.type for edge in snapshot.edges}

    assert {"exhibit", "project", "owner", "supplier", "material", "theme", "interaction", "document"} <= node_types
    assert {"belongs_to_project", "owned_by", "supplied_by", "uses_material", "has_theme", "has_interaction", "has_document", "similar_to"} <= edge_types


def test_build_snapshot_creates_evidence_and_adjacency_for_exhibits():
    snapshot = build_exhibit_kg_snapshot(seed_exhibits)

    exhibit_node_ids = {node.id for node in snapshot.nodes if node.type == "exhibit"}
    evidence_source_ids = {evidence.source_id for evidence in snapshot.evidences if evidence.source_type == "exhibit"}

    assert "exhibit:lever-play" in exhibit_node_ids
    assert "lever-play" in evidence_source_ids
    assert "exhibit:lever-play" in snapshot.adjacency
    assert snapshot.adjacency["exhibit:lever-play"]


def test_build_snapshot_skips_missing_similar_targets_and_records_warning():
    broken = seed_exhibits[0].model_copy(update={"related_exhibit_ids": ["missing-exhibit"]})

    snapshot = build_exhibit_kg_snapshot([broken])

    assert snapshot.warnings
    assert any("missing-exhibit" in warning for warning in snapshot.warnings)
    assert not any(edge.target == "exhibit:missing-exhibit" for edge in snapshot.edges)
```

- [ ] **Step 2: Run the KG test file to verify it fails**

Run: `python -m pytest backend/tests/test_kg_builder.py -q`

Expected: FAIL with `ModuleNotFoundError: No module named 'app.kg'`

- [ ] **Step 3: Commit the failing test**

```bash
git add backend/tests/test_kg_builder.py
git commit -m "test: add kg builder coverage"
```

## Task 3: Implement the KG Snapshot Module

**Files:**
- Create: `backend/app/kg/__init__.py`
- Create: `backend/app/kg/models.py`
- Create: `backend/app/kg/extractors.py`
- Create: `backend/app/kg/builder.py`
- Test: `backend/tests/test_kg_builder.py`

- [ ] **Step 1: Add the KG data models**

```python
# backend/app/kg/models.py
from pydantic import BaseModel, Field


class KGNode(BaseModel):
    id: str
    type: str
    label: str
    attributes: dict[str, str | int | float | list[str] | None] = Field(default_factory=dict)
    source_refs: list[str] = Field(default_factory=list)


class KGEdge(BaseModel):
    source: str
    target: str
    type: str
    label: str
    weight: float = 1.0
    source_refs: list[str] = Field(default_factory=list)


class KGEvidence(BaseModel):
    evidence_id: str
    source_type: str
    source_id: str
    title: str
    snippet: str
    linked_node_ids: list[str] = Field(default_factory=list)
    linked_edge_ids: list[str] = Field(default_factory=list)


class KGSnapshot(BaseModel):
    nodes: list[KGNode]
    edges: list[KGEdge]
    evidences: list[KGEvidence]
    adjacency: dict[str, list[str]] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
```

- [ ] **Step 2: Add deterministic extractors**

```python
# backend/app/kg/extractors.py
from app.schemas import ExhibitResponse
from .models import KGEdge, KGEvidence, KGNode


def exhibit_node(exhibit: ExhibitResponse) -> KGNode:
    return KGNode(
        id=f"exhibit:{exhibit.id}",
        type="exhibit",
        label=exhibit.name,
        attributes={
            "category": exhibit.category,
            "theme": exhibit.theme.name,
            "venue_type": exhibit.venue_type,
            "status": exhibit.status,
            "project_year": exhibit.project_year,
        },
        source_refs=[f"exhibit:{exhibit.id}"],
    )


def exhibit_evidence(exhibit: ExhibitResponse) -> KGEvidence:
    return KGEvidence(
        evidence_id=f"evidence:exhibit:{exhibit.id}",
        source_type="exhibit",
        source_id=exhibit.id,
        title=exhibit.name,
        snippet=exhibit.description,
        linked_node_ids=[f"exhibit:{exhibit.id}"],
        linked_edge_ids=[],
    )


def document_evidences(exhibit: ExhibitResponse) -> list[KGEvidence]:
    return [
        KGEvidence(
            evidence_id=f"evidence:document:{document.id}",
            source_type="document",
            source_id=document.id,
            title=document.name,
            snippet=document.source_note or document.url,
            linked_node_ids=[f"exhibit:{exhibit.id}", f"document:{document.id}"],
            linked_edge_ids=[f"exhibit:{exhibit.id}:has_document:document:{document.id}"],
        )
        for document in exhibit.documents
    ]
```

- [ ] **Step 3: Add the graph builder**

```python
# backend/app/kg/builder.py
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
    by_id = {item.id: item for item in exhibits}

    def add_node(node: KGNode) -> None:
        nodes[node.id] = node

    def add_edge(edge: KGEdge) -> None:
        edges.append(edge)
        adjacency[edge.source].append(edge.target)

    for exhibit in exhibits:
        exhibit_id = f"exhibit:{exhibit.id}"
        add_node(exhibit_node(exhibit))
        evidences.append(exhibit_evidence(exhibit))
        evidences.extend(document_evidences(exhibit))

        mappings = [
            ("project", exhibit.project.id, exhibit.project.name, "belongs_to_project", "所属项目"),
            ("owner", exhibit.owner.id, exhibit.owner.name, "owned_by", "业主"),
            ("supplier", exhibit.supplier.id, exhibit.supplier.name, "supplied_by", "供应商"),
            ("theme", exhibit.theme.id, exhibit.theme.name, "has_theme", "主题"),
        ]
        for kind, raw_id, label, edge_type, edge_label in mappings:
            target = f"{kind}:{raw_id}"
            add_node(KGNode(id=target, type=kind, label=label, source_refs=[f"exhibit:{exhibit.id}"]))
            add_edge(KGEdge(source=exhibit_id, target=target, type=edge_type, label=edge_label, source_refs=[f"exhibit:{exhibit.id}"]))

        for material in exhibit.materials:
            target = f"material:{material.id}"
            add_node(KGNode(id=target, type="material", label=material.name, source_refs=[f"exhibit:{exhibit.id}"]))
            add_edge(KGEdge(source=exhibit_id, target=target, type="uses_material", label="使用材料", source_refs=[f"exhibit:{exhibit.id}"]))

        for interaction in exhibit.interactions:
            target = f"interaction:{interaction.id}"
            add_node(KGNode(id=target, type="interaction", label=interaction.name, source_refs=[f"exhibit:{exhibit.id}"]))
            add_edge(KGEdge(source=exhibit_id, target=target, type="has_interaction", label="交互方式", source_refs=[f"exhibit:{exhibit.id}"]))

        for document in exhibit.documents:
            target = f"document:{document.id}"
            add_node(KGNode(id=target, type="document", label=document.name, source_refs=[f"exhibit:{exhibit.id}", f"document:{document.id}"]))
            add_edge(KGEdge(source=exhibit_id, target=target, type="has_document", label="文档资料", source_refs=[f"exhibit:{exhibit.id}", f"document:{document.id}"]))

        for related_id in exhibit.related_exhibit_ids:
            if related_id not in by_id:
                warnings.append(f"Missing related exhibit target: {related_id}")
                continue
            target = f"exhibit:{related_id}"
            add_edge(KGEdge(source=exhibit_id, target=target, type="similar_to", label="相似展项", source_refs=[f"exhibit:{exhibit.id}", f"exhibit:{related_id}"]))

    return KGSnapshot(
        nodes=list(nodes.values()),
        edges=edges,
        evidences=evidences,
        adjacency=dict(adjacency),
        warnings=warnings,
    )
```

- [ ] **Step 4: Add the package export**

```python
# backend/app/kg/__init__.py
from .builder import build_exhibit_kg_snapshot
from .models import KGEdge, KGEvidence, KGNode, KGSnapshot

__all__ = ["build_exhibit_kg_snapshot", "KGEdge", "KGEvidence", "KGNode", "KGSnapshot"]
```

- [ ] **Step 5: Run the KG tests**

Run: `python -m pytest backend/tests/test_kg_builder.py -q`

Expected: `3 passed`

- [ ] **Step 6: Commit**

```bash
git add backend/app/kg/__init__.py backend/app/kg/models.py backend/app/kg/extractors.py backend/app/kg/builder.py backend/tests/test_kg_builder.py
git commit -m "feat: add isolated kg builder module"
```

## Task 4: Write the GraphRAG Tests First

**Files:**
- Create: `backend/tests/test_graphrag_search.py`
- Read: `backend/app/repository.py`
- Read: `backend/app/kg/builder.py`

- [ ] **Step 1: Write the failing GraphRAG tests**

```python
from app.repository import seed_exhibits
from app.kg.builder import build_exhibit_kg_snapshot
from app.graphrag.search import GraphRAGFilters, search_graph_rag


def test_search_graph_rag_filters_before_scoring():
    snapshot = build_exhibit_kg_snapshot(seed_exhibits)

    response = search_graph_rag(
        query="力学",
        exhibits=seed_exhibits,
        snapshot=snapshot,
        filters=GraphRAGFilters(theme="力学", status="已落地"),
        top_k=5,
    )

    assert response.total == 1
    assert response.items[0].exhibit.id == "lever-play"


def test_search_graph_rag_returns_reasons_citations_and_neighborhood():
    snapshot = build_exhibit_kg_snapshot(seed_exhibits)

    response = search_graph_rag(query="杠杆乐园 启思互动工坊", exhibits=seed_exhibits, snapshot=snapshot, top_k=3)

    assert response.items
    first = response.items[0]
    assert first.exhibit.id == "lever-play"
    assert first.score > 0
    assert first.reasons
    assert first.citations
    assert any(node.type == "project" for node in first.neighborhood.nodes)


def test_search_graph_rag_returns_empty_response_when_no_evidence():
    snapshot = build_exhibit_kg_snapshot(seed_exhibits)

    response = search_graph_rag(query="完全不存在的展项", exhibits=seed_exhibits, snapshot=snapshot, top_k=3)

    assert response.total == 0
    assert response.items == []
```

- [ ] **Step 2: Run the GraphRAG test file to verify it fails**

Run: `python -m pytest backend/tests/test_graphrag_search.py -q`

Expected: FAIL with `ModuleNotFoundError: No module named 'app.graphrag'`

- [ ] **Step 3: Commit the failing test**

```bash
git add backend/tests/test_graphrag_search.py
git commit -m "test: add graphrag search coverage"
```

## Task 5: Implement the Rule-Based GraphRAG Module

**Files:**
- Create: `backend/app/graphrag/__init__.py`
- Create: `backend/app/graphrag/models.py`
- Create: `backend/app/graphrag/search.py`
- Test: `backend/tests/test_graphrag_search.py`

- [ ] **Step 1: Add GraphRAG result models**

```python
# backend/app/graphrag/models.py
from pydantic import BaseModel, Field

from app.kg.models import KGSnapshot, KGEvidence
from app.schemas import ExhibitResponse


class GraphRAGFilters(BaseModel):
    theme: str | None = None
    material: str | None = None
    interaction: str | None = None
    venue_type: str | None = None
    status: str | None = None


class GraphRAGHit(BaseModel):
    exhibit: ExhibitResponse
    score: float
    reasons: list[str] = Field(default_factory=list)
    citations: list[KGEvidence] = Field(default_factory=list)
    neighborhood: KGSnapshot


class GraphRAGSearchResponse(BaseModel):
    query: str
    total: int
    items: list[GraphRAGHit] = Field(default_factory=list)
```

- [ ] **Step 2: Add the GraphRAG search implementation**

```python
# backend/app/graphrag/search.py
from app.kg.builder import build_exhibit_kg_snapshot
from app.kg.models import KGEvidence, KGSnapshot
from app.repository import ExhibitRepository
from app.schemas import ExhibitResponse
from .models import GraphRAGFilters, GraphRAGHit, GraphRAGSearchResponse


def search_graph_rag(
    query: str,
    exhibits: list[ExhibitResponse],
    snapshot: KGSnapshot | None = None,
    filters: GraphRAGFilters | None = None,
    top_k: int = 5,
) -> GraphRAGSearchResponse:
    active_snapshot = snapshot or build_exhibit_kg_snapshot(exhibits)
    filtered = _apply_filters(exhibits, filters)
    hits = [hit for exhibit in filtered if (hit := _score_exhibit(query, exhibit, active_snapshot)) is not None]
    hits.sort(key=lambda item: (-item.score, item.exhibit.id))
    items = hits[:top_k]
    return GraphRAGSearchResponse(query=query, total=len(items), items=items)


def _apply_filters(exhibits: list[ExhibitResponse], filters: GraphRAGFilters | None) -> list[ExhibitResponse]:
    if filters is None:
        return exhibits
    matcher = ExhibitRepository([])
    return [
        exhibit
        for exhibit in exhibits
        if matcher._matches(
            exhibit,
            keyword=None,
            venue_type=filters.venue_type,
            category=None,
            theme=filters.theme,
            material=filters.material,
            interaction=filters.interaction,
            status=filters.status,
            budget_min=None,
            budget_max=None,
        )
    ]


def _score_exhibit(query: str, exhibit: ExhibitResponse, snapshot: KGSnapshot) -> GraphRAGHit | None:
    tokens = [token for token in query.replace("，", " ").split() if token]
    fields = {
        "identity": [exhibit.id, exhibit.name],
        "classification": [exhibit.category, exhibit.theme.name, exhibit.venue_type, *exhibit.tags],
        "materials": [item.name for item in exhibit.materials],
        "interactions": [item.name for item in exhibit.interactions],
        "project": [exhibit.project.name, exhibit.owner.name, exhibit.supplier.name],
        "documents": [value for document in exhibit.documents for value in [document.name, document.source_note or ""] if value],
        "description": [exhibit.description],
    }
    weights = {"identity": 4.0, "classification": 3.0, "materials": 2.0, "interactions": 2.0, "project": 2.0, "documents": 2.0, "description": 1.0}

    reasons: list[str] = []
    score = 0.0
    for label, values in fields.items():
        joined = " ".join(values)
        matched = [token for token in tokens if token in joined]
        if matched:
            score += len(set(matched)) * weights[label]
            reasons.append(f"matched {label}")

    if score <= 0:
        return None

    exhibit_node_id = f"exhibit:{exhibit.id}"
    neighbor_ids = [exhibit_node_id, *snapshot.adjacency.get(exhibit_node_id, [])]
    neighborhood = KGSnapshot(
        nodes=[node for node in snapshot.nodes if node.id in neighbor_ids],
        edges=[edge for edge in snapshot.edges if edge.source == exhibit_node_id and edge.target in neighbor_ids],
        evidences=[],
        adjacency={exhibit_node_id: snapshot.adjacency.get(exhibit_node_id, [])},
        warnings=[],
    )
    citations = _dedupe_citations(
        [evidence for evidence in snapshot.evidences if exhibit_node_id in evidence.linked_node_ids]
    )
    return GraphRAGHit(exhibit=exhibit, score=score, reasons=reasons, citations=citations, neighborhood=neighborhood)


def _dedupe_citations(evidences: list[KGEvidence]) -> list[KGEvidence]:
    seen: set[tuple[str, str]] = set()
    unique: list[KGEvidence] = []
    for evidence in evidences:
        key = (evidence.source_type, evidence.source_id)
        if key in seen:
            continue
        seen.add(key)
        unique.append(evidence)
    return unique
```

- [ ] **Step 3: Add the package export**

```python
# backend/app/graphrag/__init__.py
from .models import GraphRAGFilters, GraphRAGHit, GraphRAGSearchResponse
from .search import search_graph_rag

__all__ = ["GraphRAGFilters", "GraphRAGHit", "GraphRAGSearchResponse", "search_graph_rag"]
```

- [ ] **Step 4: Run the GraphRAG tests**

Run: `python -m pytest backend/tests/test_graphrag_search.py -q`

Expected: `3 passed`

- [ ] **Step 5: Commit**

```bash
git add backend/app/graphrag/__init__.py backend/app/graphrag/models.py backend/app/graphrag/search.py backend/tests/test_graphrag_search.py
git commit -m "feat: add isolated graphrag search module"
```

## Task 6: Final Verification and Handoff

**Files:**
- Verify: `backend/app/kg/*.py`
- Verify: `backend/app/graphrag/*.py`
- Verify: `backend/tests/test_kg_builder.py`
- Verify: `backend/tests/test_graphrag_search.py`
- Verify: `docs/kg-construction-plan.md`
- Verify: `docs/graphrag-design.md`

- [ ] **Step 1: Run focused backend tests**

Run: `python -m pytest backend/tests/test_kg_builder.py backend/tests/test_graphrag_search.py -q`

Expected: `6 passed`

- [ ] **Step 2: Run the full backend test suite**

Run: `python -m pytest backend/tests -q`

Expected: PASS with the existing suite plus the two new test files

- [ ] **Step 3: Check git status**

Run: `git status --short`

Expected:

```text
<no output>
```

- [ ] **Step 4: Commit final verification or doc touch-ups if needed**

```bash
git add backend/app/kg backend/app/graphrag backend/tests docs
git commit -m "test: verify kg graphrag isolated modules"
```

- [ ] **Step 5: Prepare the handoff summary**

```text
- Added isolated modules under backend/app/kg and backend/app/graphrag
- Added docs/kg-construction-plan.md and refreshed docs/graphrag-design.md
- Added backend/tests/test_kg_builder.py and backend/tests/test_graphrag_search.py
- Verified pytest passes in the isolated worktree
- Mainline integration points remain future work: repository call site, graph API source, GraphRAG API route wiring
```
