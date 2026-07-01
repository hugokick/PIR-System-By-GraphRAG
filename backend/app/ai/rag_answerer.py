"""带引用来源的 RAG 答案生成器。

本模块提供一组纯函数与一份数据契约，用于把 GraphRAG 检索结果（matched
exhibits + citations + 可选 reasoning signals）组装成中文答案文本。

设计目标：

- 默认实现为 deterministic fallback（不调用任何外部 LLM，可在 CI/测试中
  离线运行）。
- 通过 ``RagAnswerProvider`` Protocol 预留真实 LLM 接入点；上层在
  ``answer_rag`` 中按"先 provider，后 fallback"策略选择结果。
- 答案必须使用 ``[1] [2]`` 这类编号引用 citations；``used_citation_ids``
  以稳定顺序返回真正出现在答案中的来源键。
- 缺少可用依据时必须显式拒答（``refusal_reason`` + 低 confidence），禁止
  编造内容。
- 输入模型与主线 ``GraphRagSearchHit`` / ``GraphRagCitation`` 保持形状
  兼容，便于未来 ``services.graphrag._compose_grounded_answer`` 收敛到本
  模块（详见 ``docs/llm-rag-answer-contract.md``）。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Protocol, Sequence

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# 数据契约
# ---------------------------------------------------------------------------


class RagCitation(BaseModel):
    """单条引用来源，与主线 ``GraphRagCitation`` 字段保持一致。"""

    source_id: str
    source_type: str
    title: str
    snippet: str = ""

    @property
    def key(self) -> tuple[str, str]:
        """去重主键：(source_type, source_id)。"""
        return (self.source_type, self.source_id)


class RagMatchedExhibit(BaseModel):
    """一个被检索命中的展项候选。"""

    exhibit_id: str
    exhibit_name: str
    exhibit_description: str = ""
    reasons: list[str] = Field(default_factory=list)
    citations: list[RagCitation] = Field(default_factory=list)

    def citation_keys(self) -> list[tuple[str, str]]:
        return [citation.key for citation in self.citations]


class RagReasoningSignal(BaseModel):
    """细粒度推理信号；可选，用于提升 confidence 与回写答案说明。"""

    exhibit_id: str
    signal_type: str
    detail: str = ""
    score: float = 0.0


class RagAnswerInputs(BaseModel):
    """``answer_rag`` 的入参。"""

    query: str = Field(min_length=1)
    matched_exhibits: list[RagMatchedExhibit] = Field(default_factory=list)
    citations: list[RagCitation] = Field(default_factory=list)
    reasoning_signals: list[RagReasoningSignal] = Field(default_factory=list)


class RagAnswerResult(BaseModel):
    """``answer_rag`` 的输出契约。"""

    answer: str
    used_citation_keys: list[tuple[str, str]] = Field(default_factory=list)
    refusal_reason: str | None = None
    confidence: float = 0.0
    warnings: list[str] = Field(default_factory=list)

    @property
    def is_refusal(self) -> bool:
        return self.refusal_reason is not None


# ---------------------------------------------------------------------------
# Provider 协议
# ---------------------------------------------------------------------------


class RagAnswerProvider(Protocol):
    """未来真实 LLM 提供方应实现的最小协议。

    - 返回 ``None``：表示放弃，由 ``answer_rag`` 走 fallback。
    - 抛异常：同样视作放弃，由 ``answer_rag`` 兜底。
    - 返回 ``RagAnswerResult``：直接采用，不再走 fallback。
    """

    def answer(self, inputs: RagAnswerInputs) -> RagAnswerResult | None: ...


@dataclass
class _NullProvider:
    """默认占位 provider，始终拒绝并交给 fallback。"""

    name: str = "null"

    def answer(self, inputs: RagAnswerInputs) -> RagAnswerResult | None:  # noqa: ARG002
        return None


# ---------------------------------------------------------------------------
# 公共入口
# ---------------------------------------------------------------------------


ANSWER_HEADER = "根据库内资料，"
NO_CITATION_REFUSAL = "未找到引用来源"
NO_MATCH_REFUSAL = "未找到命中展项"
NO_DESCRIPTION_WARNING = "命中展项缺少说明文本"


def answer_rag(
    inputs: RagAnswerInputs,
    *,
    provider: RagAnswerProvider | None = None,
) -> RagAnswerResult:
    """根据检索结果组装中文答案。

    选择顺序：

    1. 若 ``provider`` 提供，返回有效结果则直接使用；
    2. 否则或返回空/抛异常时，回退到 deterministic fallback。
    """

    if provider is not None:
        try:
            provided = provider.answer(inputs)
        except Exception:  # noqa: BLE001 — fallback is the contract
            provided = None
        if provided is not None:
            return _normalize_result(provided)

    return _deterministic_answer(inputs)


# ---------------------------------------------------------------------------
# Fallback 实现
# ---------------------------------------------------------------------------


def _deterministic_answer(inputs: RagAnswerInputs) -> RagAnswerResult:
    citations = _dedupe_citations(inputs.citations)
    citations_by_key: dict[tuple[str, str], RagCitation] = {
        citation.key: citation for citation in citations
    }
    citation_order: list[tuple[str, str]] = list(citations_by_key.keys())
    citation_numbers: Mapping[tuple[str, str], int] = {
        key: index + 1 for index, key in enumerate(citation_order)
    }

    warnings: list[str] = []

    if not citation_order:
        if not inputs.matched_exhibits:
            return RagAnswerResult(
                answer=_refusal_message(inputs.query),
                used_citation_keys=[],
                refusal_reason=f"{NO_MATCH_REFUSAL} 且 {NO_CITATION_REFUSAL}",
                confidence=_confidence(empty_inputs=True),
                warnings=warnings,
            )
        return RagAnswerResult(
            answer=_refusal_message(inputs.query),
            used_citation_keys=[],
            refusal_reason=NO_CITATION_REFUSAL,
            confidence=_confidence(empty_inputs=False, has_citations=False),
            warnings=warnings,
        )

    if not inputs.matched_exhibits:
        return RagAnswerResult(
            answer=_refusal_message(inputs.query),
            used_citation_keys=[],
            refusal_reason=NO_MATCH_REFUSAL,
            confidence=_confidence(empty_inputs=False, has_citations=True),
            warnings=warnings,
        )

    used_keys: set[tuple[str, str]] = set()
    answer_lines: list[str] = [
        f"{ANSWER_HEADER}针对“{inputs.query}”找到 {len(inputs.matched_exhibits)} 个相关展项："
    ]

    for index, exhibit in enumerate(inputs.matched_exhibits, start=1):
        reference = _first_reference_marker(exhibit.citation_keys(), citation_numbers)
        reason = _compose_reasons(exhibit.reasons)
        description = exhibit.exhibit_description.strip() or "（暂无说明）"
        if not exhibit.exhibit_description.strip():
            warnings.append(f"{NO_DESCRIPTION_WARNING}：{exhibit.exhibit_name}")
        answer_lines.append(
            f"{index}. {exhibit.exhibit_name}（{exhibit.exhibit_id}）：{description}"
            f" 匹配依据：{reason}。{reference}"
        )
        used_keys.update(key for key in exhibit.citation_keys() if key in citation_numbers)

    used_ordered = [key for key in citation_order if key in used_keys]
    if used_ordered:
        summary = "；".join(
            _citation_source_summary(citation_numbers[key], citations_by_key[key])
            for key in used_ordered
        )
        answer_lines.append(f"来源：{summary}")

    confidence = _confidence(
        empty_inputs=False,
        has_citations=True,
        citation_count=len(citations),
        match_count=len(inputs.matched_exhibits),
        signal_count=len(inputs.reasoning_signals),
        used_citation_count=len(used_ordered),
    )

    return RagAnswerResult(
        answer="\n".join(answer_lines),
        used_citation_keys=used_ordered,
        refusal_reason=None,
        confidence=round(confidence, 3),
        warnings=warnings,
    )


# ---------------------------------------------------------------------------
# 内部辅助
# ---------------------------------------------------------------------------


def _dedupe_citations(citations: Sequence[RagCitation]) -> list[RagCitation]:
    seen: set[tuple[str, str]] = set()
    unique: list[RagCitation] = []
    for citation in citations:
        if citation.key in seen:
            continue
        seen.add(citation.key)
        unique.append(citation)
    return unique


def _compose_reasons(reasons: Sequence[str]) -> str:
    cleaned = [reason.strip() for reason in reasons if reason and reason.strip()]
    if not cleaned:
        return "与查询文本和图谱关系匹配"
    return "、".join(cleaned)


def _first_reference_marker(
    citation_keys: Sequence[tuple[str, str]],
    citation_numbers: Mapping[tuple[str, str], int],
) -> str:
    for key in citation_keys:
        number = citation_numbers.get(key)
        if number is not None:
            return f"依据 [{number}]。"
    return "暂无可编号来源。"


def _citation_source_summary(index: int, citation: RagCitation) -> str:
    snippet = citation.snippet.strip()
    if len(snippet) > 90:
        snippet = f"{snippet[:87]}..."
    return f"[{index}] {citation.title}：{snippet}" if snippet else f"[{index}] {citation.title}"


def _refusal_message(query: str) -> str:
    return (
        f"未找到依据：库内资料暂未命中“{query}”。"
        "请补充展项档案、上传资料，或调整筛选条件后重试。"
    )


def _confidence(
    *,
    empty_inputs: bool,
    has_citations: bool | None = None,
    citation_count: int = 0,
    match_count: int = 0,
    signal_count: int = 0,
    used_citation_count: int = 0,
) -> float:
    """轻量可解释置信度评分，0-1 之间。"""

    if empty_inputs:
        return 0.05
    if not has_citations:
        return 0.2
    # 有 citations 但完全没命中展项：证据没有可承载对象，仍偏低
    if match_count == 0:
        return 0.3
    base = 0.5
    base += min(citation_count, 5) * 0.05
    base += min(match_count, 5) * 0.04
    base += min(signal_count, 5) * 0.03
    coverage = used_citation_count / max(citation_count, 1)
    base += 0.1 * coverage
    return max(0.0, min(1.0, base))


def _normalize_result(result: RagAnswerResult) -> RagAnswerResult:
    """确保 provider 返回的 result 不暴露明显问题。"""

    confidence = result.confidence
    if result.refusal_reason and not result.answer.strip():
        return result
    if confidence < 0:
        confidence = 0.0
    if confidence > 1:
        confidence = 1.0
    return result.model_copy(update={"confidence": round(confidence, 3)})
