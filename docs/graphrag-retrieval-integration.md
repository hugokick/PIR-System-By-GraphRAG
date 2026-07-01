# GraphRAG 检索增强整合记录

## 整合原则

本次整合基于独立 worktree `.worktrees/hermes-graphrag-retrieval` / 分支 `hermes/graphrag-retrieval` 的审查结果，不直接合并整条分支。

保持不变：

- 不改前端
- 不改 CRUD
- 不改 Neo4j demo graph
- 不做 PostgreSQL-Neo4j 双写
- 保持 `/api/graphrag/search` 和 `/api/graphrag/answer` 请求/响应结构不变
- 保留主线已有的 `semantic_scores`、KG projection、document chunk、pgvector 召回链路

## 已整合的最小子集

1. 检索评测样例
   - `backend/tests/fixtures/graphrag_eval_cases.json`
   - `backend/tests/test_graphrag_eval_samples.py`

2. document chunk 契约模块
   - `backend/app/graphrag/document_chunks.py`
   - `backend/tests/test_document_chunks_contract.py`

3. KG 邻域增强
   - `query_subgraph_by_exhibit_id` 的中心子图支持一跳入边
   - 对相同 `source/type/target` 的边去重

4. reasoning signals 细分
   - `semantic_recall`
   - `document_chunk_match`
   - `graph_neighbor_match`
   - `rule_match`

## 未整合内容

未整文件覆盖以下模块，因为主线当前版本已经包含更多能力：

- `backend/app/graphrag/search.py`
- `backend/app/graphrag/contract.py`
- `backend/app/services/graphrag.py`

尤其保留了主线已有的：

- `venue_type` / `status` / `review_status` 过滤
- `semantic_scores` 参数传递
- `total_matches`
- 当前文档上传与 `DocumentAsset.chunks` 引用链路

## 后续建议

下一步如继续整合 GraphRAG 检索增强，建议仍按最小变更进行：

1. 为 `search.py` 的排序子项增加更细粒度评测用例。
2. 将 `document_chunks.py` 契约逐步接入上传解析链路，但不要替换现有 `DocumentAsset.chunks` API 字段。
3. 如需增强召回排序，优先在 `search_graph_rag` 内部增加可测的分数子项，而不是改变 `/api/graphrag/*` 响应结构。
