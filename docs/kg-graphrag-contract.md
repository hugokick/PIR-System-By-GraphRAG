# KG / GraphRAG 共享查询契约

## 目标

本文档定义展项知识图谱与 GraphRAG 检索之间的主线共享契约。当前主线只接入可演示、可测试的最小子集：展项子图查询、结构化过滤、规则版 GraphRAG 候选召回、引用来源与推理信号。

合同层保持为纯 Python 模块，不直接绑定 FastAPI 路由。路由层负责把现有 API 请求映射到合同层输入，并把结果包装成当前前端已经使用的响应结构。

## 模块位置

- `backend/app/kg/models.py`：图谱节点、边、证据与快照模型。
- `backend/app/kg/builder.py`：从展项档案构建轻量 KG 快照。
- `backend/app/kg/sync.py`：为后续新增、编辑、删除展项后的图谱同步保留入口。
- `backend/app/services/documents.py`：文本类上传资料的轻量文本抽取与切片。
- `backend/app/graphrag/contract.py`：主线共享查询契约。
- `backend/app/services/graphrag.py`：现有 API 服务薄封装，委托给合同层。

## 输入契约

### 展项中心子图

使用 `KGSubgraphQueryInput`：

- `exhibit_id`：展项 ID。

入口：

```python
query_subgraph_by_exhibit_id(query, exhibits, snapshot=None)
```

### GraphRAG 候选查询

使用 `GraphRAGContractQueryInput`：

- `query_text`：自然语言查询文本。
- `top_k`：候选数量。
- `filters`：结构化过滤条件，可为空。

`GraphRAGContractFilters` 当前支持：

- `theme`
- `material`
- `interaction`
- `venue_type`
- `status`
- `budget_min`
- `budget_max`

## 返回契约

两类查询统一返回 `KGGraphRAGQueryResult`：

- `matched_exhibits`：命中的展项候选，包含展项档案与分数。
- `graph_context`：本次查询涉及的 KG 节点、边与 warning。
- `citations`：引用来源，覆盖展项档案证据和文档证据。
- `reasoning_signals`：命中原因信号，用于解释召回结果。
- `source_nodes`：参与本次结果构成的节点。
- `source_edges`：参与本次结果构成的边。

## 主线调用方式

GraphRAG 搜索示例：

```python
from app.graphrag.contract import (
    GraphRAGContractFilters,
    GraphRAGContractQueryInput,
    query_graphrag_contract,
)

result = query_graphrag_contract(
    GraphRAGContractQueryInput(
        query_text="力学 启思互动工坊",
        top_k=5,
        filters=GraphRAGContractFilters(theme="力学"),
    ),
    exhibits=repository.list_exhibits(),
)
```

展项中心子图示例：

```python
from app.graphrag.contract import KGSubgraphQueryInput, query_subgraph_by_exhibit_id

result = query_subgraph_by_exhibit_id(
    KGSubgraphQueryInput(exhibit_id="lever-play"),
    exhibits=repository.list_exhibits(),
)
```

## 与现有 `/api/graphrag/*` 的关系

主线保留一套路由语义：

- `POST /api/graphrag/search`
- `POST /api/graphrag/answer`

现有服务层 `backend/app/services/graphrag.py` 不再维护独立 GraphRAG 核心逻辑，而是作为薄封装调用 `backend/app/graphrag/contract.py`。这样可以避免主线和并行 KG/GraphRAG 工作产生两套查询语义。

## 文档切片边界

当前主线已在 `DocumentAsset` 内接入轻量 `chunks` 字段。上传 `txt`、`md`、`csv`、`tsv`、`json`、`log` 等文本类资料以及可抽取文本的 `pdf` 文件时，后端会抽取文本、归一化并生成 chunk；KG evidence 和 GraphRAG 检索会使用这些 chunk，citation 仍指回原始 `document.id`。

本阶段仍不引入独立 `document_chunks` 表或模块，也不做 Word / CAD 的深度解析。PDF 仅支持基础文本抽取，不处理扫描件 OCR、版面复原或表格结构。后续当文档解析、对象存储、引用定位和 embedding 生命周期稳定后，再把 chunk 从 `DocumentAsset` 内嵌字段升级为独立持久化资源。

## 验收标准

- 可按展项 ID 返回中心子图。
- 可按自然语言文本返回候选展项、图谱上下文、引用来源和推理信号。
- 上传的文本类资料可作为 GraphRAG 检索文本，并返回文档 citation。
- 可叠加主题、材质、互动方式、场馆类型、状态、预算区间过滤。
- 合同层不依赖 FastAPI 响应对象。
- 主线 API 服务层只做请求/响应适配，不重复实现 GraphRAG 核心逻辑。
