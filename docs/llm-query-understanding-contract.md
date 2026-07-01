# LLM Query Understanding Contract

## 目标

本模块用于把中文自然语言检索问题解析为结构化检索意图，为混合检索和 GraphRAG 排序提供补充信号。

当前 MVP 阶段不调用外部 LLM，默认使用可测试的规则 fallback；后续可通过 `provider` 接口接入真实 LLM，但不改变现有 `/api/search/hybrid`、`/api/graphrag/search`、`/api/graphrag/answer` 请求/响应结构。

## 输出字段

- `original_query`
- `normalized_query`
- `themes`
- `venue_types`
- `audience`
- `budget_intent`
- `budget_min`
- `budget_max`
- `materials`
- `interactions`
- `project_case`
- `tags`
- `exclusions`
- `confidence`
- `reasoning`

## 当前接入

- `hybrid_search`：将主题、人群、预算、材料、互动、标签、排除项作为排序和匹配原因补充。
- `GraphRAG search`：将解析出的槽位加入 query rewrite / rerank，并返回 `查询理解：...` reasoning signals。

## 受控枚举

`budget_intent`：

- `unknown`
- `low`
- `medium`
- `high`
- `lower_than_reference`

`audience`：

- `low_age_children`
- `primary_school`
- `teen`
- `family`
- `general`
