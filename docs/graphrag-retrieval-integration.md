# GraphRAG 检索强化集成说明

## 1. 模块边界

- `backend/app/graphrag/search.py`
  - 负责候选召回、基础排序和 reasons 生成
- `backend/app/graphrag/contract.py`
  - 负责 KG 邻域扩展、citation 归一化和 reasoning signals 组装
- `backend/app/services/graphrag.py`
  - 负责薄封装、API 模型转换和答案文本组织

## 2. 当前 API 契约

当前保持以下接口不变：

- `POST /api/graphrag/search`
- `POST /api/graphrag/answer`

当前保持以下响应结构不变：

- `GraphRagSearchResponse`
- `GraphRagAnswerResponse`

## 3. 当前检索链路

当前 GraphRAG 检索链路如下：

1. 路由层接收请求
2. `services/graphrag.py` 做薄封装
3. `contract.py` 负责查询契约和图上下文装配
4. `search.py` 完成检索候选与排序
5. 结果回写为稳定 API 响应

## 4. 真实 embedding / reranker 接入点

当前分支已经保留扩展方向，但默认仍以稳定规则链路为主。

- `search_graph_rag(..., semantic_scores=...)`
  - 可由上游注入真实向量召回分数
- 若未来接入 reranker
  - 建议只在 `backend/app/graphrag/search.py` 内部增加可选 adapter
- 当前默认行为
  - 未注入语义分数时，继续使用稳定规则匹配

## 5. 检索评测样例

当前评测样例位于：

- `backend/tests/fixtures/graphrag_eval_cases.json`

对应测试：

- `backend/tests/test_graphrag_eval_samples.py`

这些样例用于回归验证：

- 查询文本是否仍命中预期展项
- 检索链路改动后是否破坏基本排序

## 6. 最小 cherry-pick 顺序

建议主线按以下顺序 cherry-pick：

1. `backend/app/kg/` 与 `backend/app/graphrag/` 基础模块提交
2. GraphRAG API 契约恢复提交
3. `search.py` 强化提交
4. `contract.py` 强化提交
5. service adapter 行为测试提交
6. 检索评测样例与集成文档提交

## 7. 当前边界

本轮未触碰：

- 前端
- CRUD
- Neo4j demo graph 接口
- PostgreSQL-Neo4j 双写
- 云端部署配置

## 8. 后续建议

若下一步继续增强，建议优先做：

1. 将 `semantic_scores` 接到真实 embedding 检索结果
2. 将 document chunk 级证据与上游文档资产链路接通
3. 在 `search.py` 内补更细的分数子项解释
