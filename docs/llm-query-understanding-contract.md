# LLM Query Understanding Contract

## 模块目标

- 将自然语言检索问题解析为结构化检索意图
- 当前阶段不接入 API
- 默认使用规则 fallback

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

## 受控枚举

- `budget_intent`
  - `unknown`
  - `low`
  - `medium`
  - `high`
  - `lower_than_reference`
- `audience`
  - `low_age_children`
  - `primary_school`
  - `teen`
  - `family`
  - `general`

## 当前实现方式

- 纯函数入口：`understand_query(query, provider=None)`
- 若 provider 返回空、低置信或异常，则回退规则解析
- 当前不调用真实外部 LLM

## 未来接入 hybrid_search

- `themes[0]` 可映射到 `theme`
- `venue_types[0]` 可映射到 `venue_type`
- `materials[0]` 可映射到 `material`
- `interactions[0]` 可映射到 `interaction`
- `budget_min` / `budget_max` 可映射为预算过滤
- `audience`、`budget_intent`、`exclusions` 更适合作为 query rewrite 和 rerank 信号

## 未来接入 GraphRAG

- 主题、场馆、材料、互动、预算区间可映射到 GraphRAG 过滤条件
- `project_case` 与 `reasoning` 更适合作为 GraphRAG query context 扩展
- 当前不直接接 `/api/graphrag/search`
