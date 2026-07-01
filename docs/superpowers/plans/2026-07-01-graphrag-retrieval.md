# GraphRAG 检索强化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 `main` 基线上补齐已审查的 GraphRAG/KG 基础能力，并在不改变 `/api/graphrag/search` 与 `/api/graphrag/answer` 请求/响应结构的前提下，完成分层强化的候选召回、邻域扩展、chunk 引用和解释信号。

**Architecture:** 先把 `hermes/graphrag-kg` 上已经审查过的基础模块作为前置能力引入到当前独立分支，再在 `backend/app/graphrag/search.py -> backend/app/graphrag/contract.py -> backend/app/services/graphrag.py -> API` 这条链路中做强化。检索核心逻辑只放在 `backend/app/graphrag/`，服务层保持薄封装，真实 embedding/reranker 只预留接入点，默认仍走稳定 fallback。

**Tech Stack:** FastAPI, Pydantic, Python, pytest, 纯函数契约, Git cherry-pick, 规则检索 + 稳定 embedding fallback

---

## 基线现实

当前 `main` 基线早于 GraphRAG 开发期，缺少以下前置模块：

- `backend/app/kg/`
- `backend/app/graphrag/`
- `backend/app/services/graphrag.py`
- `backend/tests/test_graphrag_*.py`
- GraphRAG 请求/响应 schema 与路由

因此，这份计划第一阶段不是“直接强化现有 GraphRAG”，而是：

1. 先把已经在 `hermes/graphrag-kg` 审查过的基础模块带入当前分支
2. 再在当前分支上做检索强化

这样既满足“从 `main` 新开隔离 worktree”的要求，也避免重复手写已经稳定过的基础代码。

## 文件结构

### 基础模块

- Create: `backend/app/kg/__init__.py`
- Create: `backend/app/kg/models.py`
- Create: `backend/app/kg/extractors.py`
- Create: `backend/app/kg/builder.py`
- Create: `backend/app/kg/sync.py`
- Create: `backend/app/graphrag/__init__.py`
- Create: `backend/app/graphrag/models.py`
- Create: `backend/app/graphrag/search.py`
- Create: `backend/app/graphrag/contract.py`
- Create: `backend/app/graphrag/document_chunks.py`

### API 适配层

- Modify: `backend/app/schemas.py`
- Create: `backend/app/services/graphrag.py`
- Modify: `backend/app/main.py`

### 测试

- Create: `backend/tests/test_graphrag_search.py`
- Create: `backend/tests/test_kg_graphrag_contract.py`
- Create: `backend/tests/test_graphrag_api.py`
- Create: `backend/tests/test_graphrag_eval_samples.py`

### 评测与文档

- Create: `backend/tests/fixtures/graphrag_eval_cases.json`
- Create: `docs/graphrag-retrieval-integration.md`

---

### Task 1: 引入已审查的 KG / GraphRAG 基础模块

**Files:**
- Create: `backend/app/kg/*.py`
- Create: `backend/app/graphrag/*.py`
- Test: `backend/tests/test_kg_builder.py`
- Test: `backend/tests/test_kg_sync.py`
- Test: `backend/tests/test_graphrag_search.py`
- Test: `backend/tests/test_kg_graphrag_contract.py`

- [ ] **Step 1: 确认当前分支与前置提交**

使用以下命令确认分支状态与可复用提交：

```bash
git status --short --branch
git log --oneline --decorate -n 2
git log --oneline --decorate -n 10 hermes/graphrag-kg
```

预期：

- 当前分支是 `hermes/graphrag-retrieval`
- 工作树干净
- 可以看到这些基础提交：
  - `6058d96 test: add kg builder coverage`
  - `2b71a5c feat: add isolated kg builder module`
  - `a768faa test: add graphrag search coverage`
  - `decedab feat: add isolated graphrag search module`
  - `f5b9fe8 test: add kg sync coverage`
  - `5449a16 feat: add kg snapshot sync helpers`
  - `d05a299 test: add kg graphrag contract coverage`
  - `2224ed3 feat: add kg graphrag query contract`
  - `b75fe54 test: add rag document chunk contract coverage`
  - `a755b69 feat: add rag document chunk contract`

- [ ] **Step 2: 顺序 cherry-pick 基础提交**

按测试先行的顺序引入基础能力：

```bash
git cherry-pick 6058d96
git cherry-pick 2b71a5c
git cherry-pick a768faa
git cherry-pick decedab
git cherry-pick f5b9fe8
git cherry-pick 5449a16
git cherry-pick d05a299
git cherry-pick 2224ed3
git cherry-pick b75fe54
git cherry-pick a755b69
```

预期：

- `backend/app/kg/` 与 `backend/app/graphrag/` 基础模块出现
- 对应测试文件进入当前分支

- [ ] **Step 3: 运行基础模块测试确认基线成立**

运行：

```bash
python -m pytest \
  backend/tests/test_kg_builder.py \
  backend/tests/test_kg_sync.py \
  backend/tests/test_graphrag_search.py \
  backend/tests/test_kg_graphrag_contract.py -q
```

预期：

- 全部通过
- 当前分支具备可强化的 GraphRAG/KG 基础

- [ ] **Step 4: 检查当前基础模块接口**

核对以下函数已经存在：

```python
from app.graphrag.search import search_graph_rag
from app.graphrag.contract import query_graphrag_contract
from app.graphrag.document_chunks import chunk_document_source
from app.kg.builder import build_exhibit_kg_snapshot
```

预期：

- 导入全部成功
- 后续强化不需要重写基础模块

- [ ] **Step 5: 提交或保留 cherry-pick 历史**

本任务原则上直接保留 cherry-pick 提交历史，不额外 squash。若中途解决冲突产生修改，使用：

```bash
git status --short
git add backend/app/kg backend/app/graphrag backend/tests
git commit -m "chore: reconcile graphrag kg foundation on main"
```

---

### Task 2: 恢复 GraphRAG API 契约到当前 `main` 基线

**Files:**
- Modify: `backend/app/schemas.py`
- Create: `backend/app/services/graphrag.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_graphrag_api.py`

- [ ] **Step 1: 先写失败的 API 契约测试**

在 `backend/tests/test_graphrag_api.py` 中先写最小失败用例：

```python
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_graphrag_search_returns_contract_shape():
    response = client.post("/api/graphrag/search", json={"query": "力学", "top_k": 2})

    assert response.status_code == 200
    payload = response.json()
    assert set(payload.keys()) == {"query", "total", "items"}
    assert isinstance(payload["items"], list)


def test_graphrag_answer_returns_grounded_shape():
    response = client.post("/api/graphrag/answer", json={"query": "杠杆", "top_k": 1})

    assert response.status_code == 200
    payload = response.json()
    assert set(payload.keys()) == {"query", "answer", "citations", "items"}
```

- [ ] **Step 2: 运行测试确认当前基线失败**

运行：

```bash
python -m pytest backend/tests/test_graphrag_api.py -q
```

预期：

- 失败，通常表现为 `404 Not Found` 或缺少 GraphRAG 相关 schema / service

- [ ] **Step 3: 最小实现 schema、service 和 route**

在 `backend/app/schemas.py` 追加 GraphRAG API 模型，在 `backend/app/services/graphrag.py` 建立薄封装，并在 `backend/app/main.py` 接入两个 POST 路由。

关键代码片段：

```python
class GraphRagRequestFilters(BaseModel):
    theme: str | None = None
    material: str | None = None
    interaction: str | None = None
    venue_type: str | None = None
    status: str | None = None
    budget_min: int | None = Field(default=None, ge=0)
    budget_max: int | None = Field(default=None, ge=0)


class GraphRagSearchRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)
    filters: GraphRagRequestFilters | None = None


class GraphRagCitation(BaseModel):
    source_id: str
    source_type: str
    title: str
    snippet: str


class GraphRagSearchHit(BaseModel):
    exhibit: ExhibitResponse
    score: float
    reasons: list[str]
    citations: list[GraphRagCitation]
    graph: GraphResponse


class GraphRagSearchResponse(BaseModel):
    query: str
    total: int
    items: list[GraphRagSearchHit]


class GraphRagAnswerRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = Field(default=3, ge=1, le=10)
    filters: GraphRagRequestFilters | None = None


class GraphRagAnswerResponse(BaseModel):
    query: str
    answer: str
    citations: list[GraphRagCitation]
    items: list[GraphRagSearchHit]
```

```python
@app.post("/api/graphrag/search", response_model=GraphRagSearchResponse)
def graphrag_search(payload: GraphRagSearchRequest) -> GraphRagSearchResponse:
    return search_graphrag_context(
        payload.query,
        repository.list_exhibits(),
        top_k=payload.top_k,
        filters=payload.filters,
    )


@app.post("/api/graphrag/answer", response_model=GraphRagAnswerResponse)
def graphrag_answer(payload: GraphRagAnswerRequest) -> GraphRagAnswerResponse:
    return answer_from_graphrag_context(
        payload.query,
        repository.list_exhibits(),
        top_k=payload.top_k,
        filters=payload.filters,
    )
```

- [ ] **Step 4: 运行 API 契约测试确认通过**

运行：

```bash
python -m pytest backend/tests/test_graphrag_api.py -q
```

预期：

- 两个接口返回 200
- 请求/响应结构与目标契约一致

- [ ] **Step 5: 提交 API 契约恢复**

```bash
git add backend/app/schemas.py backend/app/services/graphrag.py backend/app/main.py backend/tests/test_graphrag_api.py
git commit -m "feat: restore graphrag api contract on main baseline"
```

---

### Task 3: 强化 `search.py` 的候选召回与排序

**Files:**
- Modify: `backend/app/graphrag/search.py`
- Modify: `backend/app/graphrag/models.py`
- Test: `backend/tests/test_graphrag_search.py`

- [ ] **Step 1: 先写失败的 search 强化测试**

在 `backend/tests/test_graphrag_search.py` 增加以下失败测试：

```python
from app.graphrag.models import GraphRAGFilters
from app.graphrag.search import search_graph_rag
from app.repository import seed_exhibits


def test_search_graph_rag_merges_semantic_and_rule_recall():
    response = search_graph_rag(
        query="液体城市系统",
        exhibits=seed_exhibits,
        semantic_scores={"water-cycle": 0.91},
        top_k=1,
    )

    assert response.items[0].exhibit.id == "water-cycle"
    assert any("向量召回" in reason for reason in response.items[0].reasons)


def test_search_graph_rag_prefers_document_evidence_when_query_hits_document_text():
    response = search_graph_rag(
        query="样例文档 来源链路",
        exhibits=seed_exhibits,
        filters=GraphRAGFilters(theme="力学"),
        top_k=1,
    )

    assert response.items[0].exhibit.id == "lever-play"
    assert response.items[0].citations
```

- [ ] **Step 2: 运行定向测试确认失败**

运行：

```bash
python -m pytest backend/tests/test_graphrag_search.py -q
```

预期：

- 失败，通常表现为 `search_graph_rag()` 不支持 `semantic_scores`
- 或 reasons / citations 不满足新断言

- [ ] **Step 3: 编写最小实现，建立多通道召回与分数子项**

在 `backend/app/graphrag/search.py` 内增加内部 helper，保持对外 `GraphRAGHit` / `GraphRAGSearchResponse` 不变。

关键实现片段：

```python
def search_graph_rag(
    query: str,
    exhibits: list[ExhibitResponse],
    snapshot: KGSnapshot | None = None,
    filters: GraphRAGFilters | None = None,
    top_k: int = 5,
    semantic_scores: Mapping[str, float] | None = None,
) -> GraphRAGSearchResponse:
    active_snapshot = snapshot or build_exhibit_kg_snapshot(exhibits)
    filtered = _apply_filters(exhibits, filters)
    candidate_ids = _collect_candidate_ids(query, filtered, semantic_scores or {})
    hits = [
        hit
        for exhibit in filtered
        if exhibit.id in candidate_ids
        if (hit := _score_exhibit(query, exhibit, active_snapshot, semantic_scores or {})) is not None
    ]
    hits.sort(key=lambda item: (-item.score, item.exhibit.id))
    return GraphRAGSearchResponse(query=query, total=len(hits), items=hits[:top_k])


def _collect_candidate_ids(
    query: str,
    exhibits: list[ExhibitResponse],
    semantic_scores: Mapping[str, float],
) -> set[str]:
    tokens = [token for token in query.replace("，", " ").split() if token]
    candidate_ids = set(semantic_scores.keys())
    for exhibit in exhibits:
        searchable = " ".join(
            [
                exhibit.id,
                exhibit.name,
                exhibit.category,
                exhibit.theme.name,
                exhibit.venue_type,
                exhibit.project.name,
                exhibit.owner.name,
                exhibit.supplier.name,
                exhibit.description,
                *[item.name for item in exhibit.materials],
                *[item.name for item in exhibit.interactions],
                *[document.name for document in exhibit.documents],
                *[document.source_note or "" for document in exhibit.documents],
                *exhibit.tags,
            ]
        )
        if any(token in searchable for token in tokens):
            candidate_ids.add(exhibit.id)
    return candidate_ids
```

- [ ] **Step 4: 运行 search 测试确认通过**

运行：

```bash
python -m pytest backend/tests/test_graphrag_search.py -q
```

预期：

- 所有 search 相关测试通过
- `response.total` 仍表示“top_k 截断前总命中数”

- [ ] **Step 5: 提交 search 强化**

```bash
git add backend/app/graphrag/search.py backend/app/graphrag/models.py backend/tests/test_graphrag_search.py
git commit -m "feat: reinforce graphrag search recall and ranking"
```

---

### Task 4: 强化 `contract.py` 的邻域扩展、chunk 引用和 reasoning signals

**Files:**
- Modify: `backend/app/graphrag/contract.py`
- Modify: `backend/app/graphrag/document_chunks.py`
- Test: `backend/tests/test_kg_graphrag_contract.py`

- [ ] **Step 1: 先写失败的 contract 强化测试**

在 `backend/tests/test_kg_graphrag_contract.py` 增加失败测试：

```python
from app.graphrag.contract import GraphRAGContractQueryInput, KGGraphRAGQueryResult, query_graphrag_contract
from app.repository import seed_exhibits


def test_query_graphrag_contract_expands_neighborhood_and_dedupes_edges():
    result = query_graphrag_contract(
        GraphRAGContractQueryInput(query_text="力学 启思互动工坊", top_k=2),
        exhibits=seed_exhibits,
    )

    assert isinstance(result, KGGraphRAGQueryResult)
    assert any(edge.type == "belongs_to_project" for edge in result.graph_context.edges)
    assert any(edge.type == "supplied_by" for edge in result.graph_context.edges)


def test_query_graphrag_contract_prefers_chunk_level_reasoning_signal_when_available():
    result = query_graphrag_contract(
        GraphRAGContractQueryInput(query_text="样例文档 来源链路", top_k=1),
        exhibits=seed_exhibits,
    )

    assert any(signal.signal_type == "document_chunk_match" for signal in result.reasoning_signals)
```

- [ ] **Step 2: 运行定向测试确认失败**

运行：

```bash
python -m pytest backend/tests/test_kg_graphrag_contract.py -q
```

预期：

- 失败，原因是当前 graph context 扩展仍偏浅
- 或 `reasoning_signals` 未区分 `document_chunk_match`

- [ ] **Step 3: 实现邻域扩展、citation 优先级和信号类型**

在 `backend/app/graphrag/contract.py` 中实现以下 helper：

```python
def _expanded_subgraph(snapshot: KGSnapshot, center_id: str) -> tuple[list[KGNode], list[KGEdge]]:
    first_hop_ids = set(snapshot.adjacency.get(center_id, []))
    node_ids = {center_id, *first_hop_ids}
    edges = [
        edge
        for edge in snapshot.edges
        if (edge.source == center_id and edge.target in node_ids)
        or (edge.target == center_id and edge.source in node_ids)
    ]
    return (
        [node for node in snapshot.nodes if node.id in node_ids],
        _dedupe_by_id(edges, key=lambda edge: f"{edge.source}|{edge.type}|{edge.target}"),
    )


def _reasoning_signal_type(reason: str) -> str:
    if reason.startswith("向量召回"):
        return "semantic_recall"
    if reason.startswith("文档切片命中"):
        return "document_chunk_match"
    if reason.startswith("图谱邻居命中"):
        return "graph_neighbor_match"
    return "rule_match"
```

同时把 contract 中原来的 `_center_subgraph()` 调整为 `_expanded_subgraph()`，并在 citations 组装时遵循：

1. chunk 级证据
2. document 级证据
3. exhibit 级证据

- [ ] **Step 4: 运行 contract 测试确认通过**

运行：

```bash
python -m pytest backend/tests/test_kg_graphrag_contract.py -q
```

预期：

- 图上下文命中更多解释性边
- reasoning signals 出现更细的 signal type
- citations 保持去重与稳定顺序

- [ ] **Step 5: 提交 contract 强化**

```bash
git add backend/app/graphrag/contract.py backend/app/graphrag/document_chunks.py backend/tests/test_kg_graphrag_contract.py
git commit -m "feat: reinforce graphrag contract graph context and citations"
```

---

### Task 5: 收敛 `services/graphrag.py` 为薄封装并增强答案组织

**Files:**
- Modify: `backend/app/services/graphrag.py`
- Modify: `backend/tests/test_graphrag_api.py`

- [ ] **Step 1: 先写服务层行为测试**

在 `backend/tests/test_graphrag_api.py` 中增加以下失败断言：

```python
def test_graphrag_search_uses_contract_results_without_reimplementing_scoring(monkeypatch):
    from app.services import graphrag as graphrag_service

    called = {}

    def fake_query_contract(query_input, exhibits, snapshot=None, semantic_scores=None):
        called["query_text"] = query_input.query_text
        from app.graphrag.contract import KGGraphRAGQueryResult
        return KGGraphRAGQueryResult()

    monkeypatch.setattr(graphrag_service, "query_graphrag_contract", fake_query_contract)
    client.post("/api/graphrag/search", json={"query": "力学", "top_k": 1})

    assert called["query_text"] == "力学"


def test_graphrag_answer_keeps_grounded_numbered_citations():
    response = client.post("/api/graphrag/answer", json={"query": "杠杆", "top_k": 1})

    assert response.status_code == 200
    payload = response.json()
    assert "根据库内资料" in payload["answer"]
    if payload["citations"]:
        assert "[1]" in payload["answer"]
```

- [ ] **Step 2: 运行 API 测试确认存在失败或薄封装不充分**

运行：

```bash
python -m pytest backend/tests/test_graphrag_api.py -q
```

预期：

- 失败，或需要进一步收敛服务层职责

- [ ] **Step 3: 最小实现薄封装与回答组织**

`backend/app/services/graphrag.py` 只保留：

```python
def search_graphrag_context(
    query: str,
    exhibits: list[ExhibitResponse],
    top_k: int = 5,
    filters: GraphRagRequestFilters | None = None,
    semantic_scores: Mapping[str, float] | None = None,
    snapshot: KGSnapshot | None = None,
) -> GraphRagSearchResponse:
    contract_result = query_graphrag_contract(
        GraphRAGContractQueryInput(
            query_text=query,
            top_k=top_k,
            filters=_contract_filters(filters),
        ),
        exhibits=exhibits,
        snapshot=snapshot,
        semantic_scores=semantic_scores,
    )
    return _contract_to_search_response(query, contract_result)
```

```python
def answer_from_graphrag_context(...):
    search_response = search_graphrag_context(...)
    citations = _deduplicate_citations(
        citation
        for item in search_response.items
        for citation in item.citations
    )
    answer = _compose_grounded_answer(query, search_response.items, citations)
    return GraphRagAnswerResponse(
        query=query,
        answer=answer,
        citations=citations,
        items=search_response.items,
    )
```

- [ ] **Step 4: 运行 API 测试确认通过**

运行：

```bash
python -m pytest backend/tests/test_graphrag_api.py -q
```

预期：

- 服务层只充当 contract 到 API 的适配器
- `/api/graphrag/search` 与 `/api/graphrag/answer` 响应结构稳定

- [ ] **Step 5: 提交服务层收敛**

```bash
git add backend/app/services/graphrag.py backend/tests/test_graphrag_api.py
git commit -m "refactor: keep graphrag service as thin adapter"
```

---

### Task 6: 增加检索评测样例与集成说明

**Files:**
- Create: `backend/tests/fixtures/graphrag_eval_cases.json`
- Create: `backend/tests/test_graphrag_eval_samples.py`
- Create: `docs/graphrag-retrieval-integration.md`

- [ ] **Step 1: 先写评测样例测试**

先创建测试文件：

```python
import json
from pathlib import Path

from app.repository import seed_exhibits
from app.services.graphrag import search_graphrag_context


def test_graphrag_eval_cases_remain_stable():
    cases = json.loads(
        Path("backend/tests/fixtures/graphrag_eval_cases.json").read_text(encoding="utf-8")
    )

    for case in cases:
        response = search_graphrag_context(
            case["query"],
            seed_exhibits,
            top_k=case.get("top_k", 3),
        )
        returned_ids = [item.exhibit.id for item in response.items]
        assert returned_ids[: len(case["expected_top_ids"])] == case["expected_top_ids"]
```

- [ ] **Step 2: 运行测试确认因缺少样例文件而失败**

运行：

```bash
python -m pytest backend/tests/test_graphrag_eval_samples.py -q
```

预期：

- 失败，原因通常是 fixture 文件不存在

- [ ] **Step 3: 创建样例文件与集成文档**

`backend/tests/fixtures/graphrag_eval_cases.json` 最小内容：

```json
[
  {
    "query": "力学 亲子互动",
    "top_k": 2,
    "expected_top_ids": ["lever-play"]
  },
  {
    "query": "液体城市系统",
    "top_k": 1,
    "expected_top_ids": ["water-cycle"]
  }
]
```

`docs/graphrag-retrieval-integration.md` 需要覆盖：

```markdown
# GraphRAG 检索强化集成说明

## 模块边界
- `backend/app/graphrag/search.py`: 候选召回与排序
- `backend/app/graphrag/contract.py`: 邻域扩展、citation、reasoning signals
- `backend/app/services/graphrag.py`: 薄封装和答案组织

## 真实 embedding / reranker 接入点
- 保留 `semantic_scores` 注入点
- 默认继续使用稳定 fallback

## 最小 cherry-pick 顺序
1. `backend/app/kg/` 与 `backend/app/graphrag/` 基础模块
2. GraphRAG API 契约恢复
3. Search 强化
4. Contract 强化
5. Service 层收敛
6. 测试、评测样例、文档
```

- [ ] **Step 4: 运行评测样例和全量后端测试**

运行：

```bash
python -m pytest backend/tests/test_graphrag_eval_samples.py -q
python -m pytest backend/tests -q
```

预期：

- 评测样例测试通过
- 后端全量测试通过

- [ ] **Step 5: 提交评测样例和集成文档**

```bash
git add backend/tests/fixtures/graphrag_eval_cases.json backend/tests/test_graphrag_eval_samples.py docs/graphrag-retrieval-integration.md
git commit -m "docs: add graphrag retrieval integration guide and eval samples"
```

---

### Task 7: 最终验证与推送

**Files:**
- Modify: 当前分支所有已变更文件

- [ ] **Step 1: 运行最终验证命令**

```bash
python -m pytest backend/tests -q
git status --short --branch
git log --oneline -n 8
```

预期：

- 后端测试全绿
- 工作树干净
- 提交历史体现“基础 -> API 契约 -> search -> contract -> service -> docs”

- [ ] **Step 2: 如有诊断问题，修复后复跑**

在 VS Code / Trae 里运行诊断并修正最近修改的文件，重点检查：

```python
backend/app/graphrag/search.py
backend/app/graphrag/contract.py
backend/app/services/graphrag.py
```

- [ ] **Step 3: 推送分支**

```bash
git push -u origin hermes/graphrag-retrieval
```

预期：

- 远端出现独立强化分支

- [ ] **Step 4: 输出审查摘要**

整理以下内容到最终交付说明：

```markdown
- 本次只增强 GraphRAG 检索链路
- API 请求/响应结构保持兼容
- stable embedding fallback 仍保留
- 评测样例可用于回归
- cherry-pick 顺序已在集成文档列出
```

- [ ] **Step 5: 最终提交（仅当还有未提交修复时）**

```bash
git add backend docs
git commit -m "chore: finalize graphrag retrieval reinforcement"
```

若工作树已干净，则跳过此步。

---

## 自检

### Spec 覆盖

- 候选召回与排序：Task 3
- KG 邻域扩展、chunk citation、reasoning signals：Task 4
- 服务层薄封装：Task 5
- stable fallback：Task 3 与 Task 5
- 后端测试与评测样例：Task 3 / Task 4 / Task 5 / Task 6
- 集成说明与 cherry-pick 建议：Task 6

### 占位符扫描

- 无 `TODO` / `TBD`
- 每个任务都给出了具体文件、命令和最小代码片段

### 类型一致性

- API 层统一使用 `GraphRagSearchRequest` / `GraphRagAnswerRequest`
- 服务层统一以 `query_graphrag_contract()` 作为 contract 入口
- Search 强化不改变外部 `GraphRAGSearchResponse`

