# 自然语言查询理解设计

## 1. 目标

本设计用于在项目内新增一个“自然语言查询理解”模块，将用户的自然语言检索问题解析成稳定、可测试的结构化检索意图。

本阶段只交付独立模块，不接入任何现有 API，不改前端，不调用真实外部 LLM。

典型输入包括：

- “找几个适合低龄儿童、预算不高、互动性强的力学展项”
- “有没有适合县级科技馆、维护成本低、机械互动的展品？”
- “找类似水循环沙盘但预算更低的方案”

输出将包含以下字段：

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

## 2. 范围与边界

### 2.1 本次范围

- 新增 `backend/app/ai/__init__.py`
- 新增 `backend/app/ai/query_understanding.py`
- 新增 `backend/tests/test_query_understanding.py`
- 新增 `docs/llm-query-understanding-contract.md`

### 2.2 明确不做

- 不修改 `/api/search/hybrid`
- 不修改 `/api/graphrag/search`
- 不修改前端
- 不调用真实外部 LLM
- 不依赖网络服务
- 不改变现有 Hybrid Search 与 GraphRAG 的请求/响应契约

### 2.3 成功标准

- 新增测试通过
- 现有 `backend/tests` 不被破坏
- 输出契约文档清晰描述未来如何接入 `hybrid_search` 与 GraphRAG

## 3. 推荐方案

采用“规则优先 + Provider 预留”的方案。

### 3.1 当前默认路径

默认使用规则/词典 fallback 完成解析：

- 纯函数调用
- 完全离线
- 行为稳定可测试
- 不依赖真实 LLM

### 3.2 未来扩展路径

预留 `QueryUnderstandingProvider` 接口。

未来若接入真实 LLM，应遵循以下优先顺序：

1. 先调用 provider 获取结构化结果
2. 若 provider 返回空结果、低置信结果或异常，则回退到规则解析
3. 最终仍输出同一份稳定契约

## 4. 模块设计

### 4.1 文件职责

- `backend/app/ai/__init__.py`
  - 导出查询理解模块公共入口与模型
- `backend/app/ai/query_understanding.py`
  - 定义输出模型、受控枚举、provider 协议、规则解析入口和内部词典
- `backend/tests/test_query_understanding.py`
  - 验证规则 fallback、枚举稳定性、弱查询处理和排除条件
- `docs/llm-query-understanding-contract.md`
  - 说明契约、字段含义、枚举说明，以及未来如何映射到 `hybrid_search` / GraphRAG

### 4.2 入口函数

建议提供以下纯函数入口：

```python
def understand_query(
    query: str,
    provider: QueryUnderstandingProvider | None = None,
) -> QueryUnderstandingResult:
    ...
```

该入口遵循：

- 保留原始输入
- 先做标准化
- 再执行槽位抽取
- 最终返回稳定结果

## 5. 输出契约

### 5.1 核心结果模型

建议定义 `QueryUnderstandingResult`，字段如下：

- `original_query: str`
- `normalized_query: str`
- `themes: list[str]`
- `venue_types: list[str]`
- `audience: list[str]`
- `budget_intent: str`
- `budget_min: int | None`
- `budget_max: int | None`
- `materials: list[str]`
- `interactions: list[str]`
- `project_case: str | None`
- `tags: list[str]`
- `exclusions: list[str]`
- `confidence: float`
- `reasoning: list[str]`

### 5.2 字段含义

- `original_query`
  - 原始用户输入，不做改写
- `normalized_query`
  - 去除冗余空白、统一表达后的查询文本
- `themes`
  - 识别出的主题，例如 `力学`、`天文`
- `venue_types`
  - 识别出的场馆类型，例如 `县级科技馆`
- `audience`
  - 受控枚举列表，用于表达面向人群
- `budget_intent`
  - 受控枚举，用于表达预算倾向
- `budget_min` / `budget_max`
  - 若识别到明确预算区间则填入整数；仅识别“预算不高”时可保留空值
- `materials`
  - 材料类线索，例如 `钢结构`
- `interactions`
  - 互动方式线索，例如 `机械互动`
- `project_case`
  - 指向“类似某案例”的参照对象，例如 `水循环沙盘`
- `tags`
  - 额外意图标签，例如 `维护成本低`、`互动性强`
- `exclusions`
  - 排除条件，例如 `不要水景`
- `confidence`
  - 0 到 1 的解析置信度
- `reasoning`
  - 对各槽位如何识别出的解释

## 6. 受控枚举设计

### 6.1 `budget_intent`

采用以下受控枚举：

- `unknown`
- `low`
- `medium`
- `high`
- `lower_than_reference`

映射建议：

- “预算不高” / “预算有限” / “低预算” -> `low`
- “预算更低” / “比 X 更低” -> `lower_than_reference`
- 未识别预算倾向 -> `unknown`

### 6.2 `audience`

采用以下受控枚举列表：

- `low_age_children`
- `primary_school`
- `teen`
- `family`
- `general`

映射建议：

- “低龄儿童” -> `low_age_children`
- “小学生” -> `primary_school`
- “青少年” -> `teen`
- “亲子” / “家庭” -> `family`
- 未识别时可为空列表；必要时由上层补 `general`

## 7. 规则解析策略

### 7.1 标准化

第一步将输入统一成便于规则匹配的文本：

- 去除多余空白
- 统一全角/半角标点
- 保留中文语义
- 为匹配需要生成简化文本副本

标准化后仍保留 `original_query`。

### 7.2 槽位抽取

规则解析器按槽位独立抽取：

- `themes`
- `venue_types`
- `audience`
- `budget_intent`
- `budget_min` / `budget_max`
- `materials`
- `interactions`
- `project_case`
- `tags`
- `exclusions`

每个槽位对应一个小型词典或规则集，避免把全部逻辑堆在一个大函数中。

### 7.3 典型规则

建议至少覆盖以下模式：

- 主题识别：
  - `力学`、`水循环`、`天文`
- 场馆类型识别：
  - `县级科技馆`
  - `综合科技馆`
- 人群识别：
  - `低龄儿童`
  - `亲子`
- 预算识别：
  - `预算不高`
  - `预算更低`
- 互动识别：
  - `机械互动`
  - `互动性强`
- 标签识别：
  - `维护成本低`
- 排除识别：
  - `不要`
  - `排除`
  - `不考虑`
- 参考案例识别：
  - “类似水循环沙盘”

### 7.4 空查询与弱查询

以下情况视为弱查询：

- 空字符串
- 仅包含“找几个”“有没有”“推荐一下”等弱意图词
- 不包含任何可识别业务槽位

弱查询的处理规则：

- 输出稳定空结构
- `confidence` 保持较低
- `reasoning` 明确说明“未识别出有效检索槽位”

## 8. Provider 设计

### 8.1 协议接口

建议定义：

```python
class QueryUnderstandingProvider(Protocol):
    def understand(self, query: str) -> QueryUnderstandingResult | None:
        ...
```

### 8.2 当前阶段限制

当前阶段：

- 不提供真实外部 LLM 实现
- 不在测试中 mock 外部网络调用
- 只验证 provider 接口存在且可回退

### 8.3 回退策略

若提供了 provider，则：

- provider 返回有效高置信结果 -> 使用 provider 结果
- provider 返回 `None`、抛异常、或结果明显不完整 -> 回退规则解析

规则 fallback 仍是当前模块的主实现。

## 9. 置信度设计

`confidence` 采用轻量可解释评分，不引入统计模型。

建议规则：

- 命中 1 个核心槽位 -> 基础置信度
- 命中多个独立槽位 -> 逐步提升
- 命中参照案例或显式排除条件 -> 额外加分
- 弱查询或空查询 -> 低置信

`reasoning` 需要和置信度形成对应解释，例如：

- “识别到主题：力学”
- “识别到预算倾向：low，来源于‘预算不高’”
- “识别到参照案例：水循环沙盘”

## 10. 测试设计

### 10.1 必测场景

至少覆盖以下测试：

- `低龄儿童` 被识别为 `low_age_children`
- `预算不高` 被识别为 `budget_intent = low`
- `力学` 被识别到 `themes`
- `机械互动` 被识别到 `interactions`
- `县级科技馆` 被识别到 `venue_types`
- 排除条件被写入 `exclusions`
- 空查询或弱查询返回低置信稳定结构

### 10.2 组合场景

建议增加两条组合测试：

- “找几个适合低龄儿童、预算不高、互动性强的力学展项”
- “找类似水循环沙盘但预算更低的方案”

这些测试用于确认多槽位同时命中时的稳定性。

### 10.3 不测内容

当前不测试：

- 真实 LLM 输出质量
- 外部模型连接
- API 层接入

## 11. 与现有检索链路的未来接入方式

### 11.1 接入 `hybrid_search`

未来可将解析结果映射到 `HybridSearchFilters`：

- `themes[0]` -> `theme`
- `venue_types[0]` -> `venue_type`
- `materials[0]` -> `material`
- `interactions[0]` -> `interaction`
- `budget_min` -> `budget_min`
- `budget_max` -> `budget_max`

以下字段不建议强行映射到现有过滤器：

- `audience`
- `budget_intent`
- `project_case`
- `exclusions`

这些字段更适合作为：

- query rewrite 线索
- reasons 增强线索
- rerank 信号

### 11.2 接入 GraphRAG

未来可将解析结果映射到 `GraphRagRequestFilters` 或 contract 输入：

- `themes[0]` -> `theme`
- `venue_types[0]` -> `venue_type`
- `materials[0]` -> `material`
- `interactions[0]` -> `interaction`
- `budget_min` / `budget_max` -> 同名字段

以下字段更适合进入：

- `reasoning`
- `query_text` 扩展
- provider 产生的辅助检索上下文

### 11.3 当前为何不接 API

当前阶段不直接接 `/api/search/hybrid` 与 `/api/graphrag/search`，原因如下：

- 先锁定查询理解契约，避免与现有 API 一起演化
- 先验证规则 fallback 的稳定性
- 后续接入时可单独审查“解析层 -> 检索层”的映射逻辑

## 12. 风险与缓解

### 风险 1：规则覆盖不足

缓解：

- 使用小词典逐步扩充
- 优先覆盖高频业务表达
- 保持 reasoning 可见，方便补规则

### 风险 2：字段过多导致耦合

缓解：

- 保持结果模型纯粹
- 不在本阶段强接 API
- 每个字段只承担一个明确职责

### 风险 3：未来 LLM 接入改变契约

缓解：

- 先固定 `QueryUnderstandingResult`
- provider 只能返回同结构结果
- 任何外部模型都必须服从 fallback 契约

## 13. 验收标准

本设计完成后，后续实现应证明：

- 规则 fallback 可独立工作
- provider 接口已预留但不依赖真实 LLM
- 新增测试覆盖核心槽位与弱查询
- 现有 `backend/tests` 不被破坏
- 契约文档清晰说明未来如何接入 `hybrid_search` 与 GraphRAG
