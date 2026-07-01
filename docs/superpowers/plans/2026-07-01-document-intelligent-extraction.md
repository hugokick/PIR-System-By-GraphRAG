# Document Intelligent Extraction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建一个独立的“上传资料字段抽取建议”模块，从文档全文或 chunk 中生成展项建档建议值与可追溯来源，但不接入上传 API、不自动写库。

**Architecture:** 在 `backend/app/ai/document_extraction.py` 中实现纯函数规则抽取器，定义输入模型、结果模型、来源模型和 `DocumentExtractionProvider` 接口。默认走规则/词典 fallback，若未来传入 provider，则 provider 失败、空结果或低置信时回退规则解析；服务层与 API 层本阶段完全不改。

**Tech Stack:** Python 3.11, Pydantic, pytest, 规则词典, 正则表达式

---

## File Map

- Create: `backend/app/ai/__init__.py`
  - 导出 `DocumentExtractionInput`、`DocumentTextInput`、`SuggestedFieldSource`、`DocumentExtractionResult`、`DocumentExtractionProvider`、`extract_document_suggestions`
- Create: `backend/app/ai/document_extraction.py`
  - 定义模型、provider 协议、文本标准化、预算/主题/材料/互动/名称/摘要抽取与来源定位
- Create: `backend/tests/test_document_extraction.py`
  - 覆盖预算区间、材料、互动、主题、摘要、多 chunk 来源、空建议、provider 回退
- Create: `docs/document-extraction-contract.md`
  - 说明输出契约、字段含义、`field_sources` 结构、未来如何在 `upload_exhibit_asset` 后进入人工确认流程
- Create: `docs/superpowers/plans/2026-07-01-document-intelligent-extraction.md`
  - 当前实施计划

## Task 1: 建立契约骨架与失败测试

**Files:**
- Create: `backend/tests/test_document_extraction.py`
- Create: `backend/app/ai/document_extraction.py`
- Create: `backend/app/ai/__init__.py`

- [ ] **Step 1: 写出最小失败测试，锁定入口和空建议结构**

```python
from app.ai.document_extraction import (
    DocumentExtractionInput,
    extract_document_suggestions,
)


def test_empty_text_returns_empty_suggestions():
    result = extract_document_suggestions(
        DocumentExtractionInput(
            document_id="doc-empty",
            file_name="empty.txt",
            file_type="txt",
            source_note=None,
            text="",
            chunks=[],
        )
    )

    assert result.document_id == "doc-empty"
    assert result.exhibit_name is None
    assert result.theme is None
    assert result.budget_min is None
    assert result.budget_max is None
    assert result.materials == []
    assert result.interactions == []
    assert result.tags == []
    assert result.summary == ""
    assert result.field_sources == {}
    assert 0.0 <= result.confidence <= 0.2
```

- [ ] **Step 2: 运行单测确认红灯**

Run: `python -m pytest backend/tests/test_document_extraction.py::test_empty_text_returns_empty_suggestions -q`

Expected: `ModuleNotFoundError: No module named 'app.ai'` 或 `ImportError`

- [ ] **Step 3: 写最小实现骨架**

```python
from typing import Protocol

from pydantic import BaseModel, Field


class DocumentTextInput(BaseModel):
    chunk_id: str | None = None
    text: str
    sequence: int | None = None
    source_locator: str | None = None


class DocumentExtractionInput(BaseModel):
    document_id: str
    file_name: str
    file_type: str
    source_note: str | None = None
    text: str | None = None
    chunks: list[DocumentTextInput] = Field(default_factory=list)


class SuggestedFieldSource(BaseModel):
    document_id: str
    field_name: str
    chunk_id: str | None = None
    source_locator: str | None = None
    snippet: str
    reason: str


class DocumentExtractionResult(BaseModel):
    document_id: str
    file_name: str
    file_type: str
    source_note: str | None = None
    exhibit_name: str | None = None
    category: str | None = None
    theme: str | None = None
    venue_type: str | None = None
    budget_min: int | None = None
    budget_max: int | None = None
    materials: list[str] = Field(default_factory=list)
    interactions: list[str] = Field(default_factory=list)
    supplier: str | None = None
    owner: str | None = None
    project_year: int | None = None
    tags: list[str] = Field(default_factory=list)
    summary: str = ""
    confidence: float = 0.0
    field_sources: dict[str, list[SuggestedFieldSource]] = Field(default_factory=dict)


class DocumentExtractionProvider(Protocol):
    def extract(self, payload: DocumentExtractionInput) -> DocumentExtractionResult | None:
        ...


def extract_document_suggestions(
    payload: DocumentExtractionInput,
    provider: DocumentExtractionProvider | None = None,
) -> DocumentExtractionResult:
    _ = provider
    return DocumentExtractionResult(
        document_id=payload.document_id,
        file_name=payload.file_name,
        file_type=payload.file_type,
        source_note=payload.source_note,
    )
```

- [ ] **Step 4: 导出公共符号**

```python
from .document_extraction import (
    DocumentExtractionInput,
    DocumentExtractionProvider,
    DocumentExtractionResult,
    DocumentTextInput,
    SuggestedFieldSource,
    extract_document_suggestions,
)

__all__ = [
    "DocumentExtractionInput",
    "DocumentExtractionProvider",
    "DocumentExtractionResult",
    "DocumentTextInput",
    "SuggestedFieldSource",
    "extract_document_suggestions",
]
```

- [ ] **Step 5: 运行单测确认绿灯**

Run: `python -m pytest backend/tests/test_document_extraction.py::test_empty_text_returns_empty_suggestions -q`

Expected: `1 passed`

- [ ] **Step 6: 提交**

```bash
git add backend/app/ai/__init__.py backend/app/ai/document_extraction.py backend/tests/test_document_extraction.py
git commit -m "test: add document extraction contract skeleton"
```

## Task 2: 实现预算区间与主题抽取

**Files:**
- Modify: `backend/tests/test_document_extraction.py`
- Modify: `backend/app/ai/document_extraction.py`

- [ ] **Step 1: 写预算与主题失败测试**

```python
def test_extract_budget_range_and_theme_from_text():
    result = extract_document_suggestions(
        DocumentExtractionInput(
            document_id="doc-budget",
            file_name="water-plan.txt",
            file_type="txt",
            source_note="预算方案初稿",
            text="城市水循环沙盘围绕水循环主题设计，预算控制在 80 万至 120 万。",
            chunks=[],
        )
    )

    assert result.theme == "水循环"
    assert result.category == "生态环保"
    assert result.budget_min == 800000
    assert result.budget_max == 1200000
    assert "theme" in result.field_sources
    assert "budget_min" in result.field_sources
    assert "budget_max" in result.field_sources
```

- [ ] **Step 2: 运行定向测试确认失败**

Run: `python -m pytest backend/tests/test_document_extraction.py::test_extract_budget_range_and_theme_from_text -q`

Expected: `AssertionError`，因为当前 `theme` 和预算字段仍为空

- [ ] **Step 3: 实现文本标准化、主题词典和预算正则**

```python
THEME_KEYWORDS = {
    "力学": "基础科学",
    "水循环": "生态环保",
    "流体": "生态环保",
    "天文": "宇宙探索",
    "宇宙探索": "宇宙探索",
}

BUDGET_RANGE_PATTERNS = [
    re.compile(r"(?P<min>\d+(?:\.\d+)?)\s*万\s*(?:到|至|-|~)\s*(?P<max>\d+(?:\.\d+)?)\s*万"),
    re.compile(r"(?P<min>\d+(?:\.\d+)?)\s*万元\s*(?:到|至|-|~)\s*(?P<max>\d+(?:\.\d+)?)\s*万元"),
]


def normalize_text(text: str) -> str:
    return " ".join(text.replace("\u3000", " ").split())


def amount_to_yuan(value: str) -> int:
    return int(float(value) * 10000)


def extract_theme(text: str) -> tuple[str | None, str | None]:
    for theme, category in THEME_KEYWORDS.items():
        if theme in text:
            return theme, category
    return None, None


def extract_budget_range(text: str) -> tuple[int | None, int | None]:
    for pattern in BUDGET_RANGE_PATTERNS:
        match = pattern.search(text)
        if match:
            return amount_to_yuan(match.group("min")), amount_to_yuan(match.group("max"))
    return None, None
```

- [ ] **Step 4: 在主入口挂接抽取结果与来源**

```python
normalized_text = build_searchable_text(payload)
theme, category = extract_theme(normalized_text)
budget_min, budget_max = extract_budget_range(normalized_text)

result = DocumentExtractionResult(
    document_id=payload.document_id,
    file_name=payload.file_name,
    file_type=payload.file_type,
    source_note=payload.source_note,
    theme=theme,
    category=category,
    budget_min=budget_min,
    budget_max=budget_max,
    field_sources=build_field_sources(...),
    confidence=estimate_confidence(...),
)
```

- [ ] **Step 5: 运行当前测试文件**

Run: `python -m pytest backend/tests/test_document_extraction.py -q`

Expected: 至少当前 2 个测试通过

- [ ] **Step 6: 提交**

```bash
git add backend/app/ai/document_extraction.py backend/tests/test_document_extraction.py
git commit -m "feat: extract document budget and theme suggestions"
```

## Task 3: 实现材料、互动、摘要与展项名称建议

**Files:**
- Modify: `backend/tests/test_document_extraction.py`
- Modify: `backend/app/ai/document_extraction.py`

- [ ] **Step 1: 写失败测试覆盖材料、互动、摘要和名称**

```python
def test_extract_materials_interactions_summary_and_name():
    result = extract_document_suggestions(
        DocumentExtractionInput(
            document_id="doc-mechanics",
            file_name="杠杆乐园方案说明.txt",
            file_type="txt",
            source_note=None,
            text=(
                "展项名称：杠杆乐园。"
                "本方案围绕力学主题，采用钢结构与亚克力组合。"
                "观众可通过机械互动和按钮互动理解杠杆原理。"
            ),
            chunks=[],
        )
    )

    assert result.exhibit_name == "杠杆乐园"
    assert result.theme == "力学"
    assert result.materials == ["钢结构", "亚克力"]
    assert result.interactions == ["机械互动", "按钮互动"]
    assert "杠杆乐园" in result.summary
    assert "materials" in result.field_sources
    assert "interactions" in result.field_sources
```

- [ ] **Step 2: 运行定向测试确认失败**

Run: `python -m pytest backend/tests/test_document_extraction.py::test_extract_materials_interactions_summary_and_name -q`

Expected: `AssertionError`

- [ ] **Step 3: 添加材料/互动词典和名称抽取**

```python
MATERIAL_KEYWORDS = ["钢结构", "亚克力", "木饰面", "铝板", "透明管道"]
INTERACTION_KEYWORDS = ["机械互动", "按钮互动", "触摸互动", "沉浸影像"]
NAME_PATTERNS = [
    re.compile(r"(?:展项名称|项目名称|方案名称)[:：]\s*(?P<name>[^。；\n]+)"),
]


def extract_name(text: str, file_name: str) -> str | None:
    for pattern in NAME_PATTERNS:
        match = pattern.search(text)
        if match:
            return match.group("name").strip()
    stem = Path(file_name).stem.strip()
    return stem or None


def collect_keywords(text: str, keywords: list[str]) -> list[str]:
    return [keyword for keyword in keywords if keyword in text]
```

- [ ] **Step 4: 生成短摘要**

```python
def build_summary(text: str, name: str | None, theme: str | None) -> str:
    sentences = [item.strip() for item in re.split(r"[。！？!?\n]", text) if item.strip()]
    if not sentences:
        return ""
    preferred = [
        sentence
        for sentence in sentences
        if any(token for token in [name, theme, "互动", "预算"] if token and token in sentence)
    ]
    return "。".join(preferred[:2] or sentences[:2])
```

- [ ] **Step 5: 运行测试文件确认通过**

Run: `python -m pytest backend/tests/test_document_extraction.py -q`

Expected: 现有测试全部通过

- [ ] **Step 6: 提交**

```bash
git add backend/app/ai/document_extraction.py backend/tests/test_document_extraction.py
git commit -m "feat: add document extraction keywords and summary"
```

## Task 4: 实现多 chunk 来源定位、供应商/业主/年份与 provider 回退

**Files:**
- Modify: `backend/tests/test_document_extraction.py`
- Modify: `backend/app/ai/document_extraction.py`

- [ ] **Step 1: 写失败测试覆盖多 chunk 来源定位**

```python
def test_field_sources_keep_chunk_locations():
    result = extract_document_suggestions(
        DocumentExtractionInput(
            document_id="doc-chunks",
            file_name="space-dome.txt",
            file_type="txt",
            source_note="球幕方案",
            text=None,
            chunks=[
                DocumentTextInput(chunk_id="c1", sequence=1, source_locator="P1", text="主题为宇宙探索，业主：江北科技馆。"),
                DocumentTextInput(chunk_id="c2", sequence=2, source_locator="P2", text="预算约 90 万到 160 万，采用钢结构，供应商：星图数字。"),
            ],
        )
    )

    assert result.theme == "宇宙探索"
    assert result.owner == "江北科技馆"
    assert result.supplier == "星图数字"
    assert result.budget_min == 900000
    assert result.budget_max == 1600000
    assert result.field_sources["theme"][0].chunk_id == "c1"
    assert result.field_sources["supplier"][0].chunk_id == "c2"
    assert result.field_sources["budget_min"][0].source_locator == "P2"
```

- [ ] **Step 2: 写失败测试覆盖 provider 回退**

```python
class EmptyProvider:
    def extract(self, payload):
        return None


def test_provider_none_result_falls_back_to_rules():
    result = extract_document_suggestions(
        DocumentExtractionInput(
            document_id="doc-provider",
            file_name="mechanics.txt",
            file_type="txt",
            source_note=None,
            text="力学展项采用机械互动，预算 20 万至 30 万。",
            chunks=[],
        ),
        provider=EmptyProvider(),
    )

    assert result.theme == "力学"
    assert result.interactions == ["机械互动"]
    assert result.budget_min == 200000
    assert result.budget_max == 300000
```

- [ ] **Step 3: 运行上述测试确认失败**

Run: `python -m pytest backend/tests/test_document_extraction.py -q`

Expected: 与 `field_sources`、`supplier`、`owner` 或 provider 回退相关的断言失败

- [ ] **Step 4: 实现 chunk 优先的来源装配和实体抽取**

```python
ORG_PATTERNS = {
    "supplier": re.compile(r"(?:供应商|承建单位|实施单位)[:：]\s*(?P<value>[^。；\n]+)"),
    "owner": re.compile(r"(?:业主|甲方|建设单位)[:：]\s*(?P<value>[^。；\n]+)"),
}


def iter_source_segments(payload: DocumentExtractionInput) -> list[DocumentTextInput]:
    if payload.chunks:
        return payload.chunks
    if payload.text:
        return [DocumentTextInput(chunk_id=None, text=payload.text, sequence=1, source_locator=None)]
    return []


def add_source(field_sources: dict[str, list[SuggestedFieldSource]], field_name: str, segment: DocumentTextInput, snippet: str, reason: str, document_id: str) -> None:
    field_sources.setdefault(field_name, []).append(
        SuggestedFieldSource(
            document_id=document_id,
            field_name=field_name,
            chunk_id=segment.chunk_id,
            source_locator=segment.source_locator,
            snippet=snippet,
            reason=reason,
        )
    )
```

- [ ] **Step 5: 在入口中加入 provider 优先、规则回退**

```python
if provider is not None:
    try:
        provider_result = provider.extract(payload)
    except Exception:
        provider_result = None
    if provider_result is not None and provider_result.confidence >= 0.6:
        return provider_result

return extract_by_rules(payload)
```

- [ ] **Step 6: 运行测试与回归**

Run: `python -m pytest backend/tests/test_document_extraction.py -q`

Expected: `8 passed` 或与测试数量一致的全绿结果

- [ ] **Step 7: 提交**

```bash
git add backend/app/ai/document_extraction.py backend/tests/test_document_extraction.py
git commit -m "feat: add document extraction field sources and provider fallback"
```

## Task 5: 编写契约文档与最终验证

**Files:**
- Create: `docs/document-extraction-contract.md`
- Modify: `backend/app/ai/__init__.py`
- Test: `backend/tests/test_document_extraction.py`

- [ ] **Step 1: 写契约文档**

```markdown
# 上传资料字段抽取建议契约

## 目标

`extract_document_suggestions()` 从文档文本或 chunk 中生成展项建档建议值。

本模块只输出“建议值”，不自动写入展项数据。

## 输入

- `document_id`
- `file_name`
- `file_type`
- `source_note`
- `text`
- `chunks`

## 输出

- `exhibit_name`
- `category`
- `theme`
- `venue_type`
- `budget_min`
- `budget_max`
- `materials`
- `interactions`
- `supplier`
- `owner`
- `project_year`
- `tags`
- `summary`
- `confidence`
- `field_sources`

## field_sources

每个来源项必须包含：

- `document_id`
- `field_name`
- `chunk_id`
- `source_locator`
- `snippet`
- `reason`

## 未来接入 upload_exhibit_asset 的建议

1. `upload_exhibit_asset` 正常保存 `DocumentAsset` 与 `chunks`
2. 上传完成后调用 `extract_document_suggestions()`
3. 结果保存为待确认建议，不直接更新展项字段
4. 在人工确认界面展示“现有值 vs 建议值 vs 来源片段”
5. 仅在人工确认后执行展项字段更新
```

- [ ] **Step 2: 运行新增测试**

Run: `python -m pytest backend/tests/test_document_extraction.py -q`

Expected: 全绿

- [ ] **Step 3: 运行后端全量测试**

Run: `python -m pytest backend/tests -q`

Expected: 现有测试与新增测试全部通过

- [ ] **Step 4: 查看诊断并修复易处理问题**

Run: `GetDiagnostics` on:

- `backend/app/ai/document_extraction.py`
- `backend/app/ai/__init__.py`
- `backend/tests/test_document_extraction.py`

Expected: 无新的 diagnostics；若有简单导入或类型错误，先修复再继续

- [ ] **Step 5: 提交**

```bash
git add backend/app/ai/__init__.py backend/app/ai/document_extraction.py backend/tests/test_document_extraction.py docs/document-extraction-contract.md
git commit -m "docs: add document extraction contract"
```

- [ ] **Step 6: 推送并核验分支状态**

Run:

```bash
git push -u origin trae/document-extraction
git status --short --branch
git log --oneline -n 5
```

Expected:

- 远端分支创建成功
- `git status --short --branch` 显示工作树干净
- 最近提交包含本模块的 4 次左右分阶段提交

## Self-Review Checklist

- Spec coverage:
  - 独立模块：Task 1-4
  - 规则/词典 fallback：Task 2-4
  - Provider 预留：Task 1、Task 4
  - 不接上传 API：所有任务均不修改 `backend/app/main.py`
  - `field_sources` 来源定位：Task 4
  - 预算/材料/互动/主题/摘要/多 chunk/空建议测试：Task 2-4
  - 接入 `upload_exhibit_asset` 后的人工确认说明：Task 5
- Placeholder scan:
  - 本计划未使用 `TBD`、`TODO`、`稍后实现`
- Type consistency:
  - 统一使用 `DocumentExtractionInput`、`DocumentTextInput`、`SuggestedFieldSource`、`DocumentExtractionResult`
