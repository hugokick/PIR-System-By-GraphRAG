# 自然语言查询理解 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新增一个独立、可测试、可回退的自然语言查询理解模块，把中文检索问题解析成稳定的结构化检索意图，但本阶段不接入任何现有 API。

**Architecture:** 采用“规则优先 + Provider 预留”的方案，在 `backend/app/ai/query_understanding.py` 中定义结果模型、受控枚举、provider 协议和规则解析入口。先用规则/词典实现 stable fallback，后续真实 LLM 只能通过 `QueryUnderstandingProvider` 返回同结构结果，失败时自动回退到规则解析。由于当前 worktree 的 `main` 基线较早，尚不存在 `HybridSearchFilters` / `GraphRagRequestFilters`，因此本轮只交付独立模块、测试和契约文档，不接入现有检索服务。

**Tech Stack:** Python, Pydantic, Protocol typing, pytest, 纯函数解析器, 规则词典

---

## 文件结构

- Create: `backend/app/ai/__init__.py`
  - 导出查询理解公共类型与入口函数
- Create: `backend/app/ai/query_understanding.py`
  - 定义受控枚举、结果模型、provider 协议、规则 fallback 和内部词典
- Create: `backend/tests/test_query_understanding.py`
  - 覆盖低龄儿童、预算不高、力学主题、机械互动、场馆类型、排除条件、空查询/弱查询、provider 回退
- Create: `docs/llm-query-understanding-contract.md`
  - 说明输出契约、字段含义、枚举值、未来如何映射到 hybrid_search 和 GraphRAG

## 基线现实

当前独立 worktree 来自较早的 `main` 基线，仅包含：

- `backend/app/main.py`
- `backend/app/repository.py`
- `backend/app/schemas.py`
- `backend/app/services/graph.py`

当前不存在：

- `backend/app/ai/`
- `backend/app/services/hybrid_search.py`
- `backend/app/services/graphrag.py`
- `HybridSearchFilters`
- `GraphRagRequestFilters`

因此本计划不会尝试接入这些模块，而是在文档中清晰说明“未来映射方式”。

---

### Task 1: 建立查询理解契约与最小失败测试

**Files:**
- Create: `backend/tests/test_query_understanding.py`
- Create: `backend/app/ai/query_understanding.py`

- [ ] **Step 1: 先写失败测试，锁定输出结构与核心槽位**

创建 `backend/tests/test_query_understanding.py`，先写以下测试：

```python
from app.ai.query_understanding import understand_query


def test_understand_query_extracts_low_age_children_low_budget_and_theme():
    result = understand_query("找几个适合低龄儿童、预算不高、互动性强的力学展项")

    assert result.original_query == "找几个适合低龄儿童、预算不高、互动性强的力学展项"
    assert result.normalized_query
    assert result.themes == ["力学"]
    assert result.audience == ["low_age_children"]
    assert result.budget_intent == "low"
    assert "互动性强" in result.tags
    assert result.confidence > 0.5


def test_understand_query_extracts_venue_type_interaction_and_tag():
    result = understand_query("有没有适合县级科技馆、维护成本低、机械互动的展品？")

    assert result.venue_types == ["县级科技馆"]
    assert result.interactions == ["机械互动"]
    assert "维护成本低" in result.tags


def test_understand_query_extracts_reference_case_and_lower_budget_intent():
    result = understand_query("找类似水循环沙盘但预算更低的方案")

    assert result.project_case == "水循环沙盘"
    assert result.budget_intent == "lower_than_reference"


def test_understand_query_extracts_exclusions():
    result = understand_query("找力学展项，但不要水景，也不考虑沉浸影像")

    assert result.themes == ["力学"]
    assert result.exclusions == ["水景", "沉浸影像"]


def test_understand_query_returns_low_confidence_for_empty_or_weak_query():
    result = understand_query("推荐一下")

    assert result.themes == []
    assert result.venue_types == []
    assert result.audience == []
    assert result.budget_intent == "unknown"
    assert result.confidence < 0.4
    assert any("未识别出有效检索槽位" in item for item in result.reasoning)
```

- [ ] **Step 2: 运行测试确认它们确实失败**

Run:

```bash
python -m pytest backend/tests/test_query_understanding.py -q
```

Expected:

- FAIL
- 失败原因应为 `ModuleNotFoundError: No module named 'app.ai'` 或 `cannot import name 'understand_query'`

- [ ] **Step 3: 建立最小骨架让导入可用**

创建 `backend/app/ai/query_understanding.py` 最小骨架：

```python
from pydantic import BaseModel, Field


class QueryUnderstandingResult(BaseModel):
    original_query: str
    normalized_query: str
    themes: list[str] = Field(default_factory=list)
    venue_types: list[str] = Field(default_factory=list)
    audience: list[str] = Field(default_factory=list)
    budget_intent: str = "unknown"
    budget_min: int | None = None
    budget_max: int | None = None
    materials: list[str] = Field(default_factory=list)
    interactions: list[str] = Field(default_factory=list)
    project_case: str | None = None
    tags: list[str] = Field(default_factory=list)
    exclusions: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    reasoning: list[str] = Field(default_factory=list)


def understand_query(query: str) -> QueryUnderstandingResult:
    return QueryUnderstandingResult(
        original_query=query,
        normalized_query=query.strip(),
    )
```

创建 `backend/app/ai/__init__.py`：

```python
from .query_understanding import QueryUnderstandingResult, understand_query

__all__ = ["QueryUnderstandingResult", "understand_query"]
```

- [ ] **Step 4: 重新运行测试，确认从导入错误变为行为失败**

Run:

```bash
python -m pytest backend/tests/test_query_understanding.py -q
```

Expected:

- 仍然 FAIL
- 但失败应转为断言失败，说明测试已经准确锁定行为

- [ ] **Step 5: 提交测试与骨架**

```bash
git add backend/app/ai/__init__.py backend/app/ai/query_understanding.py backend/tests/test_query_understanding.py
git commit -m "test: add query understanding contract coverage"
```

---

### Task 2: 实现规则 fallback 与受控枚举

**Files:**
- Modify: `backend/app/ai/query_understanding.py`
- Test: `backend/tests/test_query_understanding.py`

- [ ] **Step 1: 在测试中补 provider 回退红灯**

向 `backend/tests/test_query_understanding.py` 追加：

```python
class NoneProvider:
    def understand(self, query: str):
        return None


def test_understand_query_falls_back_to_rules_when_provider_returns_none():
    result = understand_query("低龄儿童 力学", provider=NoneProvider())

    assert result.themes == ["力学"]
    assert result.audience == ["low_age_children"]
    assert result.budget_intent == "unknown"
```

- [ ] **Step 2: 运行测试，确认 provider 回退测试失败**

Run:

```bash
python -m pytest backend/tests/test_query_understanding.py -q
```

Expected:

- FAIL
- 原因通常为 `understand_query()` 不接受 `provider`

- [ ] **Step 3: 实现规则 fallback、标准化、槽位抽取和 provider 协议**

将 `backend/app/ai/query_understanding.py` 扩展为最小可用实现：

```python
from typing import Protocol
import re

from pydantic import BaseModel, Field


BUDGET_UNKNOWN = "unknown"
BUDGET_LOW = "low"
BUDGET_MEDIUM = "medium"
BUDGET_HIGH = "high"
BUDGET_LOWER_THAN_REFERENCE = "lower_than_reference"

AUDIENCE_LOW_AGE_CHILDREN = "low_age_children"
AUDIENCE_PRIMARY_SCHOOL = "primary_school"
AUDIENCE_TEEN = "teen"
AUDIENCE_FAMILY = "family"
AUDIENCE_GENERAL = "general"

THEME_SIGNALS = ("力学", "水循环", "天文")
VENUE_TYPE_SIGNALS = ("县级科技馆", "综合科技馆")
INTERACTION_SIGNALS = ("机械互动", "沉浸影像")
TAG_SIGNALS = ("维护成本低", "互动性强")
WEAK_QUERY_SIGNALS = ("找几个", "有没有", "推荐一下", "推荐")


class QueryUnderstandingProvider(Protocol):
    def understand(self, query: str) -> "QueryUnderstandingResult | None":
        ...


class QueryUnderstandingResult(BaseModel):
    original_query: str
    normalized_query: str
    themes: list[str] = Field(default_factory=list)
    venue_types: list[str] = Field(default_factory=list)
    audience: list[str] = Field(default_factory=list)
    budget_intent: str = BUDGET_UNKNOWN
    budget_min: int | None = None
    budget_max: int | None = None
    materials: list[str] = Field(default_factory=list)
    interactions: list[str] = Field(default_factory=list)
    project_case: str | None = None
    tags: list[str] = Field(default_factory=list)
    exclusions: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    reasoning: list[str] = Field(default_factory=list)


def understand_query(
    query: str,
    provider: QueryUnderstandingProvider | None = None,
) -> QueryUnderstandingResult:
    if provider is not None:
        try:
            provided = provider.understand(query)
        except Exception:
            provided = None
        if provided is not None and provided.confidence >= 0.6:
            return provided
    return _rule_based_understand(query)


def _rule_based_understand(query: str) -> QueryUnderstandingResult:
    normalized_query = _normalize(query)
    reasoning: list[str] = []
    themes = _matched_signals(normalized_query, THEME_SIGNALS, reasoning, "主题")
    venue_types = _matched_signals(normalized_query, VENUE_TYPE_SIGNALS, reasoning, "场馆类型")
    interactions = _matched_signals(normalized_query, INTERACTION_SIGNALS, reasoning, "互动")
    tags = _matched_signals(normalized_query, TAG_SIGNALS, reasoning, "标签")

    audience: list[str] = []
    if "低龄儿童" in normalized_query:
        audience.append(AUDIENCE_LOW_AGE_CHILDREN)
        reasoning.append("识别到人群：low_age_children，来源于‘低龄儿童’")
    elif "亲子" in normalized_query or "家庭" in normalized_query:
        audience.append(AUDIENCE_FAMILY)
        reasoning.append("识别到人群：family，来源于‘亲子/家庭’")

    budget_intent = BUDGET_UNKNOWN
    if "预算更低" in normalized_query or ("更低" in normalized_query and "类似" in normalized_query):
        budget_intent = BUDGET_LOWER_THAN_REFERENCE
        reasoning.append("识别到预算倾向：lower_than_reference")
    elif any(signal in normalized_query for signal in ("预算不高", "预算有限", "低预算", "预算低")):
        budget_intent = BUDGET_LOW
        reasoning.append("识别到预算倾向：low，来源于预算表达")

    project_case = None
    case_match = re.search(r"类似(.+?)(?:但|，|,|的方案|方案|$)", normalized_query)
    if case_match:
        project_case = case_match.group(1).strip()
        reasoning.append(f"识别到参照案例：{project_case}")

    exclusions = _extract_exclusions(normalized_query, reasoning)

    confidence = _confidence(
        themes=themes,
        venue_types=venue_types,
        audience=audience,
        budget_intent=budget_intent,
        interactions=interactions,
        tags=tags,
        project_case=project_case,
        exclusions=exclusions,
        normalized_query=normalized_query,
        reasoning=reasoning,
    )

    if confidence < 0.4 and not reasoning:
        reasoning.append("未识别出有效检索槽位")

    return QueryUnderstandingResult(
        original_query=query,
        normalized_query=normalized_query,
        themes=themes,
        venue_types=venue_types,
        audience=audience,
        budget_intent=budget_intent,
        interactions=interactions,
        project_case=project_case,
        tags=tags,
        exclusions=exclusions,
        confidence=confidence,
        reasoning=reasoning,
    )
```

并补齐以下 helper：

```python
def _normalize(query: str) -> str:
    return re.sub(r"\s+", "", query.strip())


def _matched_signals(query: str, signals: tuple[str, ...], reasoning: list[str], label: str) -> list[str]:
    matched = [signal for signal in signals if signal in query]
    for signal in matched:
        reasoning.append(f"识别到{label}：{signal}")
    return matched


def _extract_exclusions(query: str, reasoning: list[str]) -> list[str]:
    matches = re.findall(r"(?:不要|排除|不考虑)([^，,。；;]+)", query)
    exclusions: list[str] = []
    for match in matches:
        for item in re.split(r"[、和及与]", match):
            cleaned = item.strip()
            if cleaned:
                exclusions.append(cleaned)
                reasoning.append(f"识别到排除条件：{cleaned}")
    return exclusions


def _confidence(**kwargs) -> float:
    score = 0.0
    if kwargs["themes"]:
        score += 0.2
    if kwargs["venue_types"]:
        score += 0.15
    if kwargs["audience"]:
        score += 0.15
    if kwargs["budget_intent"] != BUDGET_UNKNOWN:
        score += 0.15
    if kwargs["interactions"]:
        score += 0.15
    if kwargs["tags"]:
        score += 0.1
    if kwargs["project_case"]:
        score += 0.1
    if kwargs["exclusions"]:
        score += 0.1
    if not kwargs["normalized_query"] or kwargs["normalized_query"] in WEAK_QUERY_SIGNALS:
        return 0.2
    return round(min(score, 0.95), 2)
```

- [ ] **Step 4: 运行测试，确认规则 fallback 全部通过**

Run:

```bash
python -m pytest backend/tests/test_query_understanding.py -q
```

Expected:

- PASS
- 低龄儿童、预算不高、力学主题、机械互动、场馆类型、排除条件、弱查询、provider 回退全部通过

- [ ] **Step 5: 提交规则 fallback 实现**

```bash
git add backend/app/ai/query_understanding.py backend/tests/test_query_understanding.py
git commit -m "feat: add stable query understanding fallback"
```

---

### Task 3: 收敛模块导出与枚举稳定性

**Files:**
- Modify: `backend/app/ai/__init__.py`
- Modify: `backend/tests/test_query_understanding.py`

- [ ] **Step 1: 先写导出与枚举稳定性测试**

向 `backend/tests/test_query_understanding.py` 追加：

```python
from app.ai import (
    AUDIENCE_LOW_AGE_CHILDREN,
    BUDGET_LOW,
    BUDGET_LOWER_THAN_REFERENCE,
    QueryUnderstandingResult,
    understand_query,
)


def test_ai_module_exports_stable_constants_and_entrypoint():
    result = understand_query("低龄儿童 力学")

    assert AUDIENCE_LOW_AGE_CHILDREN == "low_age_children"
    assert BUDGET_LOW == "low"
    assert BUDGET_LOWER_THAN_REFERENCE == "lower_than_reference"
    assert isinstance(result, QueryUnderstandingResult)
```

- [ ] **Step 2: 运行测试确认导出尚未完成**

Run:

```bash
python -m pytest backend/tests/test_query_understanding.py -q
```

Expected:

- FAIL
- 原因应为 `app.ai` 尚未导出这些常量

- [ ] **Step 3: 补齐 `__init__.py` 导出**

更新 `backend/app/ai/__init__.py`：

```python
from .query_understanding import (
    AUDIENCE_FAMILY,
    AUDIENCE_GENERAL,
    AUDIENCE_LOW_AGE_CHILDREN,
    AUDIENCE_PRIMARY_SCHOOL,
    AUDIENCE_TEEN,
    BUDGET_HIGH,
    BUDGET_LOW,
    BUDGET_LOWER_THAN_REFERENCE,
    BUDGET_MEDIUM,
    BUDGET_UNKNOWN,
    QueryUnderstandingProvider,
    QueryUnderstandingResult,
    understand_query,
)

__all__ = [
    "AUDIENCE_FAMILY",
    "AUDIENCE_GENERAL",
    "AUDIENCE_LOW_AGE_CHILDREN",
    "AUDIENCE_PRIMARY_SCHOOL",
    "AUDIENCE_TEEN",
    "BUDGET_HIGH",
    "BUDGET_LOW",
    "BUDGET_LOWER_THAN_REFERENCE",
    "BUDGET_MEDIUM",
    "BUDGET_UNKNOWN",
    "QueryUnderstandingProvider",
    "QueryUnderstandingResult",
    "understand_query",
]
```

- [ ] **Step 4: 运行测试确认模块导出稳定**

Run:

```bash
python -m pytest backend/tests/test_query_understanding.py -q
```

Expected:

- PASS
- 导出符号和枚举值稳定

- [ ] **Step 5: 提交导出稳定性改动**

```bash
git add backend/app/ai/__init__.py backend/tests/test_query_understanding.py
git commit -m "refactor: export query understanding contract symbols"
```

---

### Task 4: 编写契约文档与未来接入说明

**Files:**
- Create: `docs/llm-query-understanding-contract.md`

- [ ] **Step 1: 先写文档存在性测试**

向 `backend/tests/test_query_understanding.py` 追加一个轻量文档测试：

```python
from pathlib import Path


def test_query_understanding_contract_doc_mentions_hybrid_and_graphrag_mapping():
    content = Path("docs/llm-query-understanding-contract.md").read_text(encoding="utf-8")

    assert "hybrid_search" in content
    assert "GraphRAG" in content
    assert "budget_intent" in content
    assert "audience" in content
```

- [ ] **Step 2: 运行测试确认因缺少文档而失败**

Run:

```bash
python -m pytest backend/tests/test_query_understanding.py -q
```

Expected:

- FAIL
- 原因应为文档不存在

- [ ] **Step 3: 编写契约文档**

创建 `docs/llm-query-understanding-contract.md`，至少包含以下内容：

```markdown
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
- `budget_intent`: `unknown`, `low`, `medium`, `high`, `lower_than_reference`
- `audience`: `low_age_children`, `primary_school`, `teen`, `family`, `general`

## 当前实现方式
- 纯函数入口：`understand_query(query, provider=None)`
- 若 provider 返回空或异常，则回退规则解析
- 当前不调用真实外部 LLM

## 未来接入 hybrid_search
- `themes[0]` 可映射到 `theme`
- `venue_types[0]` 可映射到 `venue_type`
- `materials[0]` 可映射到 `material`
- `interactions[0]` 可映射到 `interaction`
- `budget_min` / `budget_max` 可映射为预算过滤
- `audience` / `budget_intent` / `exclusions` 更适合作为 query rewrite 和 rerank 信号

## 未来接入 GraphRAG
- 主题、场馆、材料、互动、预算区间可映射到过滤条件
- `project_case` 与 `reasoning` 更适合作为 GraphRAG query context 扩展
- 当前不直接接 `/api/graphrag/search`
```

- [ ] **Step 4: 运行测试确认文档测试通过**

Run:

```bash
python -m pytest backend/tests/test_query_understanding.py -q
```

Expected:

- PASS
- 文档测试和行为测试全部通过

- [ ] **Step 5: 提交契约文档**

```bash
git add docs/llm-query-understanding-contract.md backend/tests/test_query_understanding.py
git commit -m "docs: add llm query understanding contract"
```

---

### Task 5: 最终验证与交付

**Files:**
- Modify: 当前分支所有新增文件

- [ ] **Step 1: 运行新增模块测试与全量后端测试**

Run:

```bash
python -m pytest backend/tests/test_query_understanding.py -q
python -m pytest backend/tests -q
```

Expected:

- 查询理解测试全绿
- 现有 `backend/tests` 不被破坏

- [ ] **Step 2: 运行诊断检查最近文件**

重点检查：

```python
backend/app/ai/query_understanding.py
backend/app/ai/__init__.py
backend/tests/test_query_understanding.py
```

Expected:

- 无新的 diagnostics

- [ ] **Step 3: 检查工作树与提交历史**

Run:

```bash
git status --short --branch
git log --oneline -n 6
```

Expected:

- 工作树干净
- 提交历史包含：测试/规则 fallback/导出稳定/文档

- [ ] **Step 4: 推送分支**

```bash
git push -u origin trae/llm-query-understanding
```

Expected:

- 远端出现 `trae/llm-query-understanding`

- [ ] **Step 5: 输出交付摘要**

最终交付说明应包含：

```markdown
- 新增独立 `backend/app/ai/query_understanding.py`
- 规则/词典 fallback 可独立运行
- `QueryUnderstandingProvider` 已预留但未接真实 LLM
- 测试覆盖低龄儿童、预算不高、力学主题、机械互动、场馆类型、排除条件、弱查询
- 契约文档已说明未来如何接入 hybrid_search 和 GraphRAG
```

---

## 自检

### Spec 覆盖

- 规则/词典 stable fallback：Task 2
- `QueryUnderstandingProvider` 预留：Task 2 与 Task 3
- 不调用真实外部 LLM：Task 2
- 不改 `/api/search/hybrid`、`/api/graphrag/search`、前端：全部任务都只新增独立模块和文档
- 测试覆盖低龄儿童、预算不高、力学主题、机械互动、场馆类型、排除条件、空查询或弱查询：Task 1 与 Task 2
- 契约文档说明如何接入 hybrid_search 和 GraphRAG：Task 4

### 占位符扫描

- 无 `TODO` / `TBD`
- 每个任务都包含具体文件、命令和最小代码片段

### 类型一致性

- 统一使用 `QueryUnderstandingResult`
- 统一使用 `QueryUnderstandingProvider`
- 统一使用 `understand_query(query, provider=None)` 作为入口
