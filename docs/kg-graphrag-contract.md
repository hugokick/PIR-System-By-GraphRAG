# KG / GraphRAG 共享查询契约

## 1. 目标

本文件定义 KG 与 GraphRAG 的共享查询契约，用于给主线后续接入提供稳定的输入输出模型。

当前实现保持为纯 Python 模块，不接 FastAPI 路由、不接 `main.py`、不修改现有 CRUD 逻辑。

## 2. 模块位置

共享查询契约位于：

- `backend/app/graphrag/contract.py`

主线后续接入时，优先直接调用该模块暴露的纯函数，而不是先写路由再回填逻辑。

## 3. 输入契约

### 3.1 展项中心子图查询

使用 `KGSubgraphQueryInput`：

- `exhibit_id`

对应入口：

- `query_subgraph_by_exhibit_id(query, exhibits, snapshot=None)`

### 3.2 GraphRAG 候选查询

使用 `GraphRAGContractQueryInput`：

- `query_text`
- `top_k`
- `filters`

其中 `filters` 使用 `GraphRAGContractFilters`，当前支持：

- `theme`
- `material`
- `interaction`
- `budget_min`
- `budget_max`

## 4. 稳定返回结构

两类查询共用同一返回模型 `KGGraphRAGQueryResult`，固定字段如下：

- `matched_exhibits`
- `graph_context`
- `citations`
- `reasoning_signals`
- `source_nodes`
- `source_edges`

### 4.1 matched_exhibits

候选展项列表，元素包含：

- `exhibit`
- `score`

### 4.2 graph_context

统一图上下文，包含：

- `nodes`
- `edges`
- `warnings`

### 4.3 citations

稳定引用结构，包含：

- `evidence_id`
- `source_type`
- `source_id`
- `title`
- `snippet`

### 4.4 reasoning_signals

用于解释命中原因，当前包含：

- `exhibit_id`
- `signal_type`
- `detail`
- `score`

### 4.5 source_nodes / source_edges

当前用于显式暴露参与本次查询结果构成的节点和边，方便主线后续：

- 做图谱面板渲染
- 做引用来源高亮
- 做调试与日志输出

## 5. 主线如何调用

主线后续推荐调用方式如下：

1. 通过当前 repository 取出 `ExhibitResponse` 列表
2. 可选地先构建 `KGSnapshot`
3. 调用共享契约层纯函数
4. 再由主线路由层将结果序列化为 API 响应

示例：

```python
from app.graphrag.contract import (
    GraphRAGContractQueryInput,
    GraphRAGContractFilters,
    query_graphrag_contract,
)

items = repository.list_exhibits()
result = query_graphrag_contract(
    GraphRAGContractQueryInput(
        query_text="力学 启思互动工坊",
        top_k=5,
        filters=GraphRAGContractFilters(theme="力学"),
    ),
    exhibits=items,
)
```

展项中心子图查询示例：

```python
from app.graphrag.contract import KGSubgraphQueryInput, query_subgraph_by_exhibit_id

items = repository.list_exhibits()
result = query_subgraph_by_exhibit_id(
    KGSubgraphQueryInput(exhibit_id="lever-play"),
    exhibits=items,
)
```

## 6. 当前不接入路由的原因

当前阶段不接入 `/api/graphrag/*` 路由，原因如下：

- 主线仍在推进 CRUD、文件、导入和图谱 API，过早接路由会增加接口冲突风险
- 当前共享契约仍需主线确认字段映射、错误语义和返回包装方式
- 先稳定纯函数契约，可降低后续主线接入成本
- 可以避免在并行开发阶段出现两套 `/api/graphrag/*` 行为不一致的问题

## 7. 后续接入 /api/graphrag/* 的建议映射

建议主线后续只保留一套路由，对共享契约做薄封装：

### 7.1 查询接口

建议路由层读取：

- `query`
- `top_k`
- `theme`
- `material`
- `interaction`
- `budget_min`
- `budget_max`

然后映射为：

- `GraphRAGContractQueryInput`

### 7.2 子图接口

建议主线若需要“按展项 ID 查图”，可以新增或复用如下语义：

- `GET /api/graphrag/subgraph/{exhibit_id}`

其内部直接映射为：

- `KGSubgraphQueryInput(exhibit_id=...)`

### 7.3 返回映射

路由层可直接返回 `KGGraphRAGQueryResult.model_dump()`，也可在外层增加：

- `query`
- `total`
- `request_id`

但建议不要改动内部字段名，以保持前后端和测试用例的一致性。

## 8. 与当前模块的关系

当前共享契约层内部复用了：

- `app.kg.builder.build_exhibit_kg_snapshot`
- `app.graphrag.search.search_graph_rag`

因此：

- 构图逻辑仍在 `kg` 模块中
- 规则版 GraphRAG 仍在 `graphrag.search` 中
- 对主线暴露的稳定查询界面则由 `graphrag.contract` 负责

## 9. 当前边界

本阶段明确不做：

- 新增 FastAPI 路由
- 修改 `main.py`
- 修改主线 CRUD
- 修改前端请求层
- 引入 pgvector
- 引入 LLM 推理

## 10. 验收标准

本契约完成后，应满足：

- 能按展项 ID 返回中心子图
- 能按文本查询返回候选展项和引用来源
- 返回结构不依赖 FastAPI 路由层
- 主线后续可直接将该契约层包进 `/api/graphrag/*`
