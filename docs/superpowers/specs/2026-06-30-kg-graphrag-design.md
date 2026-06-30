# KG + GraphRAG Parallel Design

## Context

This design defines an isolated parallel workstream for knowledge graph construction
and GraphRAG inside the exhibit atlas MVP project. The workstream must not disturb
the current MVP mainline. All implementation work stays inside the dedicated
worktree branch `hermes/graphrag-kg`.

The current MVP already provides:

- React/Vite frontend
- FastAPI backend
- PostgreSQL persistence
- exhibit CRUD API
- exhibit graph API
- cloud test deployment under `/pir-system/`

The goal of this parallel stream is to deepen graph and retrieval capabilities
without refactoring current repository, API routing, frontend flow, or deployment
configuration.

## Scope

### In Scope

- Fix the graph entity and relation vocabulary for the exhibit domain
- Design a deterministic graph construction flow from existing exhibit records
- Define how create/update exhibit operations will synchronize graph relations in a
  future integration phase
- Design and implement a rule-based GraphRAG pipeline using:
  - structured filtering
  - graph neighborhood expansion
  - exhibit and document evidence recall
  - citation generation
- Add isolated backend modules, tests, and design documents

### Out of Scope

- No frontend changes
- No API route changes in the current MVP during this phase
- No edits to `backend/app/main.py`
- No edits to `backend/app/repository.py`
- No edits to `docker-compose.cloud.yml`
- No edits to `deploy/nginx.conf`
- No pgvector integration in this phase
- No LLM generation in this phase
- No document chunking, OCR, or file pipeline changes in this phase

## Constraints

- Work only inside `.worktrees/hermes-graphrag-kg`
- Base the worktree on `main`
- Do not disturb current MVP mainline development
- Write docs and tests first, then add minimal runnable backend modules
- Restrict code additions to:
  - `backend/app/kg/`
  - `backend/app/graphrag/`
  - `backend/tests/test_kg_*.py`
  - `backend/tests/test_graphrag_*.py`
  - `docs/kg-construction-plan.md`
  - `docs/graphrag-design.md`

## Design Goals

- Keep graph logic independent from FastAPI routes
- Keep GraphRAG logic independent from current API contracts
- Use deterministic extraction from current structured exhibit data
- Produce testable and explainable retrieval outputs
- Preserve a clean path for future integration with file assets, Excel import,
  pgvector, and LLM answer generation

## Architecture

The isolated design introduces two independent backend domains:

### 1. `backend/app/kg/`

Purpose:

- Translate `ExhibitResponse` records into a graph snapshot
- Build normalized nodes, edges, evidences, and adjacency indexes
- Provide stable graph contracts that can later back the mainline graph API

Planned files:

- `models.py`
- `extractors.py`
- `builder.py`

### 2. `backend/app/graphrag/`

Purpose:

- Execute rule-based graph-aware retrieval
- Apply structured filters before scoring
- Expand one-hop graph neighborhood for candidate exhibits
- Assemble evidence and citations for explainable outputs

Planned files:

- `models.py`
- `search.py`

## Data Flow

1. Current repository or any upstream caller provides a list of `ExhibitResponse`
   records
2. `kg.builder` constructs a `KGSnapshot`
3. `graphrag.search` receives the query, optional filters, exhibit records, and an
   optional `KGSnapshot`
4. Search first filters exhibits using structured criteria
5. Remaining candidates are scored using deterministic field matching
6. Top candidates are enriched with one-hop graph neighborhood
7. Evidences and citations are deduplicated and returned with match reasons

This keeps construction and retrieval reusable in tests and future integrations
without requiring immediate route changes.

## Graph Domain Model

### Node Types

The graph fixes the following node types:

- `exhibit`
- `project`
- `owner`
- `supplier`
- `material`
- `theme`
- `interaction`
- `document`

### Edge Types

The graph fixes the following edge types:

- `belongs_to_project`
- `owned_by`
- `supplied_by`
- `uses_material`
- `has_theme`
- `has_interaction`
- `has_document`
- `similar_to`

### Node Contract

Each node should carry:

- `id`
- `type`
- `label`
- `attributes`
- `source_refs`

`source_refs` always point back to a source exhibit and, when applicable, a source
document.

### Edge Contract

Each edge should carry:

- `source`
- `target`
- `type`
- `label`
- `weight`
- `source_refs`

The initial `weight` defaults to `1.0`, keeping room for future confidence,
similarity, or ranking signals.

### Evidence Contract

Evidence is modeled separately from nodes and edges to support future citation and
RAG workflows.

Each evidence record should carry:

- `evidence_id`
- `source_type`
- `source_id`
- `title`
- `snippet`
- `linked_node_ids`
- `linked_edge_ids`

At least one exhibit-level evidence entry must exist per exhibit.

## Deterministic Extraction Rules

The first implementation uses only structured deterministic extraction.

### Exhibit

- Generate one `exhibit` node per exhibit record
- Preserve identity and summary fields inside `attributes`

### Project, Owner, Supplier, Theme

- Generate one node per referenced entity
- Create edges from the exhibit node using the fixed edge vocabulary

### Materials and Interactions

- Generate nodes for each listed item
- Create one edge per item from the exhibit node

### Documents

- Generate one `document` node per attached document
- Create a `has_document` edge from the exhibit node
- Add document evidence using document title and source note

### Similar Exhibits

- Map `related_exhibit_ids` to `similar_to` edges
- If the target exhibit does not exist, skip the edge and record a warning in
  snapshot metadata

## Graph Construction Lifecycle

This phase does not modify live CRUD flows, but it defines the future integration
contract:

- `create exhibit`:
  - create or connect exhibit-centered graph nodes
  - generate all deterministic edges
- `update exhibit`:
  - rebuild the exhibit-centered subgraph
  - replace current material, interaction, document, and similar exhibit relations
- `delete or archive exhibit`:
  - handled later by mainline integration and deletion policy

The key rule is replacement, not partial mutation, for exhibit-centered relations.
This avoids graph drift after edits.

## GraphRAG Design

The first GraphRAG version is rule-based and explainable.

### Retrieval Steps

1. Apply explicit structured filters:
   - `theme`
   - `material`
   - `interaction`
   - `venue_type`
   - `status`
2. Score remaining exhibits against the query
3. Select top candidates
4. Expand one-hop neighborhood using the graph snapshot
5. Collect exhibit and document evidences
6. Deduplicate citations
7. Return candidate results with reasons, citations, and neighborhood graph context

### Search Fields

The rule-based scoring phase matches against:

- exhibit identity: `id`, `name`
- classification: `category`, `theme`, `venue_type`, `tags`
- materials
- interactions
- project-side entities: `project`, `owner`, `supplier`
- exhibit description
- document title and source note

### Initial Weights

- identity: `4`
- classification: `3`
- materials: `2`
- interactions: `2`
- project-side entities: `2`
- documents: `2`
- description: `1`

Structured filtering does not add score. It narrows the candidate set before
ranking. Neighborhood signals may add a small boost later, for example when a
candidate shares the same project or is explicitly linked as a similar exhibit.

### Neighborhood Expansion

The first version uses one-hop expansion only.

Neighbor types:

- project
- owner
- supplier
- material
- theme
- interaction
- document
- similar exhibit

This is enough to make retrieval graph-aware while remaining deterministic and easy
to test.

### Citations

Each result must return:

- at least one exhibit citation
- document citations when documents contribute to retrieval evidence
- deduplicated citations by `source_type + source_id`

Future file chunks, Excel-derived evidences, and vector hits can extend this same
contract without breaking the result shape.

## Testing Strategy

Tests are written first and only cover the new isolated modules.

### KG Tests

Planned assertions:

- building a snapshot from sample exhibits succeeds
- node and edge counts are stable for the provided fixtures
- fixed node and edge types are present
- similar exhibit relations are generated correctly
- missing related exhibit targets do not crash construction
- each exhibit yields at least one evidence record

### GraphRAG Tests

Planned assertions:

- structured filters narrow the candidate set before scoring
- rule matching works for identity, theme, material, interaction, and project-side
  fields
- one-hop neighborhood is attached to results
- citations are deduplicated
- no-evidence queries return an explicit empty response
- returned results carry `score`, `reasons`, `citations`, and graph context

## Minimal Implementation Plan

The first runnable implementation should include only:

- `backend/app/kg/models.py`
- `backend/app/kg/extractors.py`
- `backend/app/kg/builder.py`
- `backend/app/graphrag/models.py`
- `backend/app/graphrag/search.py`
- `backend/tests/test_kg_builder.py`
- `backend/tests/test_graphrag_search.py`
- `docs/kg-construction-plan.md`
- `docs/graphrag-design.md`

No live route wiring is part of this phase.

## Future Integration Points

The design intentionally leaves three clear handoff points for the MVP mainline:

### 1. Repository Integration

The current repository can later pass `ExhibitResponse` records into
`kg.builder.build_exhibit_kg_snapshot()`.

### 2. Graph API Integration

The current exhibit graph API can later use graph snapshot data rather than
assembling graph nodes and edges ad hoc.

### 3. GraphRAG API Integration

Any future `/api/graphrag/*` endpoints can call the isolated `graphrag.search`
module instead of embedding retrieval logic inside route handlers.

## Deferred Work

The following work is intentionally deferred until file, Excel, and document
chunking flows stabilize:

- file asset pipeline integration
- Excel import derived graph construction
- document chunking
- pgvector indexing and retrieval
- LLM-based answer generation

This keeps the current phase small, deterministic, and compatible with MVP
mainline development.

## Risks and Mitigations

### Risk: Duplicate graph assembly logic

Mitigation:

- keep the new graph builder isolated
- document future replacement points clearly

### Risk: Rule retrieval is weaker than future vector retrieval

Mitigation:

- preserve an explainable result contract
- keep scoring modular so vector recall can be added later

### Risk: Graph drift on exhibit edits

Mitigation:

- design update behavior as full exhibit-centered relation replacement

## Success Criteria

This design is successful when:

- entity and relation vocabulary is fixed
- deterministic graph construction is testable
- rule-based GraphRAG is testable and explainable
- current MVP mainline remains untouched
- future pgvector and LLM upgrades can plug into the same retrieval contract
