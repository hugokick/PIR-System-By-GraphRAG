# RAG 答案生成器契约

> 状态：本契约由 `trae/llm-rag-answerer` 工作树引入，定位为"答案组织层"。
> 当前主线 `/api/graphrag/answer` 已经返回答案，本模块不替换主线实现，
> 只作为可被未来替换的可选答案生成器。

## 1. 目标

将 GraphRAG 检索阶段产出的内容（命中展项 + 引用来源 + 可选 reasoning
signals）组装成一段带编号引用、可解释、不编造的中文答案。本阶段只做
"答案组织层"，不接管"检索/召回/重排序"。

## 2. 模块位置

- `backend/app/ai/__init__.py` — 子包 docstring，不强制 re-export。
- `backend/app/ai/rag_answerer.py` — 数据契约 + provider 协议 +
  deterministic fallback。
- `backend/tests/test_rag_answerer.py` — 单元测试。
- `docs/llm-rag-answer-contract.md` — 本文档。

## 3. 公共入口

```python
from app.ai.rag_answerer import (
    RagAnswerInputs,
    RagAnswerProvider,
    RagAnswerResult,
    RagCitation,
    RagMatchedExhibit,
    RagReasoningSignal,
    answer_rag,
)

result: RagAnswerResult = answer_rag(
    RagAnswerInputs(
        query="适合低龄儿童的力学展项",
        matched_exhibits=[...],
        citations=[...],
        reasoning_signals=[...],
    ),
    # provider=None 走 deterministic fallback
)
```

## 4. 输入契约

`RagAnswerInputs` 字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `query` | `str`（必填，`min_length=1`） | 用户原始查询。空字符串在模型层就抛 `ValidationError`。 |
| `matched_exhibits` | `list[RagMatchedExhibit]` | 检索命中的展项候选。 |
| `citations` | `list[RagCitation]` | 全局引用来源集合（去重前的原始顺序）。 |
| `reasoning_signals` | `list[RagReasoningSignal]` | 可选的细粒度推理信号，仅用于 confidence 提升与未来回写说明。 |

`RagMatchedExhibit` 字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `exhibit_id` | `str` | 展项 ID。 |
| `exhibit_name` | `str` | 展项名称。 |
| `exhibit_description` | `str` | 展项说明；缺省视为无说明并产生 warning。 |
| `reasons` | `list[str]` | 命中原因，组合成 "匹配依据：…" 文案。 |
| `citations` | `list[RagCitation]` | 与本展项绑定的引用来源。 |

`RagCitation` 字段（与主线 `GraphRagCitation` 完全兼容）：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `source_id` | `str` | 引用来源 ID。 |
| `source_type` | `str` | `"exhibit"` / `"document"` 等。 |
| `title` | `str` | 在答案 "来源：[N] title：snippet" 中展示。 |
| `snippet` | `str` | 引用片段；过长会被截断到 90 字符以内（保留 `...`）。 |

`RagReasoningSignal` 字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `exhibit_id` | `str` | 关联展项。 |
| `signal_type` | `str` | 例如 `semantic_recall` / `graph_neighbor_match` 等。 |
| `detail` | `str` | 备注。 |
| `score` | `float` | 评分，当前只用作 confidence 统计。 |

## 5. 输出契约

`RagAnswerResult` 字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `answer` | `str` | 最终答案文本，使用 `\n` 拼接多行。 |
| `used_citation_keys` | `list[tuple[str, str]]` | 真正出现在答案里的 `(source_type, source_id)`，按全局编号顺序。 |
| `refusal_reason` | `str \| None` | 拒答原因；为 `None` 表示给出正式答案。 |
| `confidence` | `float` | 0-1 轻量可解释置信度（详见第 7 节）。 |
| `warnings` | `list[str]` | 答案生成期间的提示，例如"命中展项缺少说明文本"。 |

属性：

- `RagAnswerResult.is_refusal`：`bool`，即 `refusal_reason is not None`。

## 6. 行为约定

1. **拒答优先**：当缺少命中或缺少 citations 时，输出显式拒答文案，
   `answer` 形如
   `"未找到依据：库内资料暂未命中"…"请补充展项档案、上传资料，或调整筛选条件后重试。"`，
   且绝不出现 `[N]` 形式的虚构编号。
2. **编号稳定**：citations 按输入顺序生成 `[1] [2] …` 编号；
   `(source_type, source_id)` 重复时保留首次出现的编号。
3. **去重**：citations 主键为 `(source_type, source_id)`，跨展项共享同一
   来源时只占一个编号。
4. **used_citation_keys 严格收敛**：仅当 citation 至少被一个匹配展项引用
   时才进入 `used_citation_keys` 与末尾 "来源：" 行。
5. **deterministic fallback 默认开启**：传 `provider=None` 或 provider
   返回 `None` / 抛异常时，自动回退，且回退结果稳定可测试。
6. **reasoning signals 弱参与**：`confidence` 评分会随 `reasoning_signals`
   数量小幅提升，但不直接拼入答案文本。
7. **warning 不阻断**：warning 仅写入 `warnings` 字段，不影响拒答逻辑。

## 7. Confidence 评分（轻量可解释）

| 场景 | confidence |
| --- | --- |
| `matched_exhibits` 与 `citations` 均为空 | `0.05` |
| 有命中但完全没有 citations | `0.2` |
| 有 citations 但完全没有命中展项 | `0.3` |
| 两者都齐 | 基础 `0.5`，加上 citation 数（最多 `+0.25`）、命中数（最多 `+0.20`）、reasoning signal 数（最多 `+0.15`）和 used/citation 覆盖率（最多 `+0.10`），封顶 `1.0`。 |

该评分不引入统计模型，仅作为接入排序/兜底判断的轻量信号。

## 8. Provider 协议

```python
class RagAnswerProvider(Protocol):
    def answer(self, inputs: RagAnswerInputs) -> RagAnswerResult | None: ...
```

接入 LLM 时应满足：

- 返回 `None` 表示放弃，落回 fallback。
- 抛异常同样视为放弃，由 `answer_rag` 兜底。
- 返回的 `RagAnswerResult`：
  - `confidence` 由 provider 自己估算；
  - `refusal_reason` 为 `None` 时表示给出答案；
  - `used_citation_keys` 必须与 `answer` 中实际出现的 `[N]` 编号一一对应。

## 9. 与 GraphRAG 主线的集成建议

短期（不建议变更主线）：

- 保持 `backend/app/services/graphrag.py` 的 `_compose_grounded_answer`
  不变；本模块仅作为"可被未来替换"的可选答案生成器。
- 新接口或新调用点若需要"答案组织层"，直接调用
  `answer_rag(RagAnswerInputs(...))`，不依赖 FastAPI 路由。

中期（参考 cherry-pick 顺序）：

1. 在 `backend/app/services/graphrag.py` 增加一个内部适配函数
   `_to_rag_answer_inputs(items, citations) -> RagAnswerInputs`，
   把 `GraphRagSearchHit`/`GraphRagCitation` 映射为本模块模型。
2. 在 `answer_from_graphrag_context` 中以 **特性开关或参数** 形式接入
   `answer_rag`，由显式注入的 provider 提供答案；fallback 保持旧模板。
3. 上线稳定后，再把"`answer = answer_rag(...).answer`"作为单一路径，
   删除 `_compose_grounded_answer`，并把其模板与本模块的 deterministic
   fallback 做等价性回归测试（`tests/test_graphrag_eval_samples.py` 已具备
   类似机制）。

## 10. 测试覆盖

`backend/tests/test_rag_answerer.py` 已覆盖：

- 有来源时生成带编号引用的答案；
- 多个来源按输入顺序编号，跨展项去重；
- 重复 citation 与去重后的稳定编号；
- 无来源或无命中时显式拒答；
- `refusal_reason` 与 `confidence` 边界；
- 拒答答案绝不出现 ` [1]` 这类虚构编号；
- `RagAnswerProvider` 协议可被实现，返回 `None` / 抛异常均回退到 fallback；
- `RagAnswerInputs.query` 空值在模型层拒绝；
- `used_citation_keys` 严格收敛到"真正出现在答案里"的子集；
- deterministic fallback 对相同输入稳定可重现。

测试运行命令：

```bash
cd backend && python -m pytest tests/test_rag_answerer.py -v
```

## 11. 验收标准

- 新增测试全部通过（18 项）。
- 现有 `backend/tests` 在本模块新增代码下不被破坏。
- 输入/输出契约与主线 `GraphRagCitation`、`GraphRagSearchHit` 字段完全
  兼容，可以被未来 `services/graphrag.py` 适配函数零摩擦接入。
- 模块默认零外部依赖，可离线运行。
