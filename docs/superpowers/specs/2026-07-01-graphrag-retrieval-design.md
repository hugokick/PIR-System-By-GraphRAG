# GraphRAG 检索强化设计

## 1. 目标

本设计用于在保持当前 API 契约和调用形态不变的前提下，强化项目现有的 GraphRAG 检索链路：

- `search -> contract -> services/graphrag.py -> API`
- `POST /api/graphrag/search`
- `POST /api/graphrag/answer`

本次强化重点包括：

- 更强的候选召回
- 更好的排序与解释信号
- 更丰富的 KG 邻域扩展
- 支持 document chunk 级引用
- 保留稳定的语义检索 fallback
- 补齐后端测试与检索评测样例

本设计不会修改前端代码、CRUD 流程、Neo4j 演示图谱接口、云端部署配置，也不会改变现有 API 的请求/响应结构。

## 2. 范围与约束

### 2.1 变更范围

- `backend/app/graphrag/search.py`
- `backend/app/graphrag/contract.py`
- `backend/app/services/graphrag.py`
- GraphRAG 相关后端测试
- 检索评测样例文件
- 集成说明与 cherry-pick 文档

### 2.2 明确不做

- 前端请求与展示改动
- `main.py` 路由定义改动
- CRUD 或 repository 写入链路改动
- PostgreSQL 与 Neo4j 双写
- Neo4j demo graph 模块改动
- 云端部署或 CI 配置改动

### 2.3 兼容性要求

- 保持 `GraphRagSearchRequest` 与 `GraphRagAnswerRequest` 不变
- 保持 `GraphRagSearchResponse` 与 `GraphRagAnswerResponse` 不变
- 保持 `search_graphrag_context()` 与 `answer_from_graphrag_context()` 作为服务层入口
- 保持 `query_graphrag_contract()` 作为契约层入口
- 当缺少语义检索信号时，必须保留稳定 fallback 行为

## 3. 当前状态

当前 GraphRAG 链路已经具备较清晰的分层：

1. `search.py` scores exhibits through field token matching and filters
2. `contract.py` converts retrieval hits into graph context, citations, and reasoning signals
3. `services/graphrag.py` adapts contract output into API models and grounded answer text
4. `main.py` routes remain thin wrappers

当前优点：

- 已有稳定的 API 契约
- 已支持通过 `semantic_scores` 注入语义召回
- 答案生成已具备来源约束
- 命中结果已附带图上下文

当前不足：

- 候选召回仍以规则和字段命中为主
- 排序信号较粗，难以审查
- 图谱邻域扩展较浅，基本只覆盖中心节点直接边
- 引用仍以 exhibit/document 为主，缺少 chunk 粒度
- 服务层虽然不重，但还需要进一步收敛为纯薄封装

## 4. 推荐架构

采用“分层强化、外部契约不变”的方式增强现有 GraphRAG。

### 4.1 Search 层职责

`backend/app/graphrag/search.py` 作为检索引擎，负责：

- 候选生成
- 分数子项计算
- 命中排序
- 底层解释原因生成

它不应依赖 API 响应模型。

### 4.2 Contract 层职责

`backend/app/graphrag/contract.py` 继续作为语义桥接层，负责：

- 调用 search 层
- 为返回展项扩展 KG 邻域
- 将引用归一化为稳定契约模型
- 将原始评分子项转换为结构化 reasoning signals

它不负责最终答案文案生成。

### 4.3 Service 层职责

`backend/app/services/graphrag.py` 保持薄封装，只负责：

- 将请求 filters 映射为 contract filters
- 将 contract 结果映射为 API 响应模型
- 基于已准备好的 hits 和 citations 组织回答文本

它不应承载检索核心逻辑。

## 5. Search 强化设计

### 5.1 候选召回

候选召回应改为“多通道并集召回，再统一排序”：

- 展项文本字段召回
- 结构化 filter 约束下召回
- 来自 `semantic_scores` 的语义召回
- 来自展项文档与 chunk 文本的文档召回
- 由 theme、material、interaction、project、owner、supplier、similar exhibit 等相关节点辅助的图谱召回

search 层先汇总所有通道返回的 exhibit ID，再计算统一排序分数。

### 5.2 分数子项

每个 exhibit hit 内部应追踪以下分数子项：

- `lexical_score`
- `semantic_score`
- `document_score`
- `graph_score`
- `rerank_score`
- `final_score`

当前 API 响应仍只暴露 `final_score`，其他子项用于生成 reasons 和 contract reasoning signals。

### 5.3 语义 fallback

检索链路必须支持三种语义模式：

1. 由调用方传入外部 semantic scores
2. 未来可接入真实 embedding 或 reranker adapter
3. 在以上都不可用时使用稳定 fallback

fallback 路径必须保持当前行为可预测、可测试。

### 5.4 未来接入点

search 层可以预留可选 adapter 接口，例如：

- semantic scorer
- reranker

这些接入点必须是可选的，不能成为当前分支运行的前置依赖。

## 6. KG 邻域扩展

`contract.py` 将把图上下文从“仅中心节点直连边”扩展为更可解释的邻域子图。

### 6.1 扩展策略

对每个命中的 exhibit，至少应包含：

- 中心 exhibit 节点
- 1-hop 类型化邻居节点
- 中心节点到邻居节点的边
- 当需要解释 citation 或 chunk 来源时，按需纳入少量二级节点

### 6.2 优先覆盖的关系类型

扩展邻域优先覆盖：

- `has_theme`
- `uses_material`
- `has_interaction`
- `belongs_to_project`
- `owned_by`
- `supplied_by`
- `has_document`
- `similar_to`

### 6.3 去重

当多个命中结果共享邻居时，contract 层应按稳定 ID 对节点和边去重，保证 `graph_context` 紧凑且可复现。

## 7. Document Chunk 引用设计

### 7.1 引用优先级

GraphRAG 应优先使用粒度更细、解释性更强的证据：

1. document chunk citation
2. document citation
3. exhibit citation

如果存在 chunk 级证据，应优先输出，并优先用于答案引用编号。

### 7.2 Chunk 来源要求

chunk 引用支持应基于现有数据或新增的证据组装逻辑实现，但不新增上传、解析或 OCR 流程。

预期 chunk 级证据字段包括：

- exhibit ID
- document ID
- chunk ID
- file name 或标题
- snippet 文本
- 若可用则包含 source locator

### 7.3 向后兼容

如果当前数据集缺少 chunk 级证据，contract 层应自动回退到 document 级引用，保证 API 行为稳定。

## 8. Reasoning Signal 设计

当前 API 已通过每个 hit 的 `reasons` 暴露字符串解释，contract 层还暴露 `reasoning_signals`。

强化后建议区分以下信号类型：

- `rule_match`
- `semantic_recall`
- `document_chunk_match`
- `graph_neighbor_match`
- `rerank_boost`

每个 reasoning signal 应包含：

- exhibit ID
- signal type
- 可读的 detail
- 对应分数贡献

hit 的 `reasons` 仍保持为紧凑字符串列表，由该 exhibit 最强的若干信号生成。

## 9. Service 层收敛

`backend/app/services/graphrag.py` 应继续保持薄封装，只保留：

- request-to-contract filter mapping
- contract-to-API result mapping
- citation de-duplication for answer generation
- grounded answer text assembly

service 层不应负责计算检索分数、候选池或图扩展规则。

## 10. 测试策略

### 10.1 Search 测试

新增或扩展以下测试：

- 多通道候选召回
- lexical 与 semantic 分数合并
- 缺少 semantic scores 时的稳定 fallback
- 多通道命中同一 exhibit 时的排序稳定性
- filter 行为保持兼容

### 10.2 Contract 测试

新增或扩展以下测试：

- 扩展邻域覆盖
- chunk citation 优先于 document citation
- reasoning signal 类型与分数归因
- 图节点、边和引用去重

### 10.3 API 测试

保留当前 API schema 测试，并补充以下行为测试：

- 响应结构不变
- reasons 增强但字段兼容
- answer 响应仍然具备来源约束与编号引用

### 10.4 检索评测样例

新增轻量级检索评测样例，可采用 Markdown 或 JSON，至少覆盖：

- query 文本
- 可选 filters
- 期望 top 命中 exhibit IDs
- 期望 citation 特征
- 期望 explanation 特征

这些样例用于回归验证和审查，不用于构建复杂 benchmark 服务。

## 11. 实施顺序

建议按以下顺序实施：

1. strengthen `search.py` candidate recall and scoring internals
2. strengthen `contract.py` graph expansion, chunk citation assembly, and reasoning signals
3. trim `services/graphrag.py` to a thin adapter and answer composer
4. add tests and retrieval evaluation samples
5. write integration and cherry-pick documentation

## 12. Cherry-pick 方案

建议的最小 cherry-pick 顺序：

1. core GraphRAG search reinforcement under `backend/app/graphrag/`
2. service adapter updates in `backend/app/services/graphrag.py`
3. tests and evaluation samples
4. integration documentation

这一顺序便于主线先审核心检索逻辑，再逐步接入服务层、测试和文档。

## 13. 风险与缓解

### 风险 1：排序变化影响既有演示结果顺序

缓解方式：

- lock ranking behavior with focused tests
- keep score component thresholds deterministic

### 风险 2：Chunk 级证据可用性不稳定

Mitigation:

- treat chunk citations as preferred, not required
- always fall back to document or exhibit evidence

### 风险 3：Service 层再次堆积检索复杂度

Mitigation:

- keep all retrieval-specific helpers inside `backend/app/graphrag/`
- review service file for adapter-only responsibilities

### 风险 4：未来 embedding 接入过早改变现有行为

Mitigation:

- design adapter points but keep stable fallback as the default path
- avoid mandatory external model dependencies in this branch

## 14. 验收标准

后续实现完成后，应能证明：

- current `/api/graphrag/search` and `/api/graphrag/answer` request and response structures stay unchanged
- candidate recall improves through multiple retrieval channels
- graph context includes richer and deduplicated neighborhood information
- citations prefer chunk-level evidence when available
- reasoning signals explain why each exhibit was returned
- service layer stays thin
- backend tests and retrieval evaluation samples cover the reinforced behavior
