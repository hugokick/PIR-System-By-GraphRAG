"""``backend/app/ai/rag_answerer`` 的测试。

覆盖以下场景：

- 有来源时生成带 ``[N]`` 编号引用的答案
- 多个来源按输入顺序编号，跨展项去重
- 无来源或无命中展项时拒答
- 引用编号与 ``citations`` 顺序稳定一致
- provider 接入可生效，异常与 ``None`` 自动回退
- 答案中不会写入无依据内容
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.ai.rag_answerer import (  # noqa: E402
    NO_CITATION_REFUSAL,
    NO_DESCRIPTION_WARNING,
    NO_MATCH_REFUSAL,
    RagAnswerInputs,
    RagAnswerProvider,
    RagAnswerResult,
    RagCitation,
    RagMatchedExhibit,
    RagReasoningSignal,
    answer_rag,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _citation(source_id: str, source_type: str = "document", *, title: str | None = None, snippet: str = "") -> RagCitation:
    return RagCitation(
        source_id=source_id,
        source_type=source_type,
        title=title or f"{source_type}-{source_id}",
        snippet=snippet or f"片段 {source_id}",
    )


def _exhibit(
    exhibit_id: str,
    *,
    name: str | None = None,
    description: str = "适合低龄儿童的力学展品。",
    reasons: list[str] | None = None,
    citations: list[RagCitation] | None = None,
) -> RagMatchedExhibit:
    return RagMatchedExhibit(
        exhibit_id=exhibit_id,
        exhibit_name=name or f"展项-{exhibit_id}",
        exhibit_description=description,
        reasons=reasons or [f"识别展项 {exhibit_id}"],
        citations=citations or [_citation(f"doc-{exhibit_id}")],
    )


# ---------------------------------------------------------------------------
# 基础答案生成
# ---------------------------------------------------------------------------


def test_answer_with_citations_uses_numbered_references_in_order():
    inputs = RagAnswerInputs(
        query="适合低龄儿童的力学展项",
        matched_exhibits=[
            _exhibit("lever", citations=[_citation("guide-1")]),
            _exhibit("pulley", citations=[_citation("guide-2")]),
        ],
        citations=[
            _citation("guide-1", title="力学展项指南 A"),
            _citation("guide-2", title="力学展项指南 B"),
        ],
    )

    result = answer_rag(inputs)

    assert result.refusal_reason is None
    assert "[1]" in result.answer
    assert "[2]" in result.answer
    # 编号与 citations 顺序一致：guide-1 -> [1], guide-2 -> [2]
    assert "[1] 力学展项指南 A" in result.answer
    assert "[2] 力学展项指南 B" in result.answer
    assert result.used_citation_keys == [("document", "guide-1"), ("document", "guide-2")]
    assert "适合低龄儿童的力学展品" in result.answer


def test_answer_dedupes_citations_across_exhibits():
    shared = _citation("shared-doc")
    inputs = RagAnswerInputs(
        query="共享来源",
        matched_exhibits=[
            _exhibit("a", citations=[shared, _citation("only-a")]),
            _exhibit("b", citations=[shared]),
        ],
        citations=[shared, _citation("only-a")],
    )

    result = answer_rag(inputs)

    assert result.refusal_reason is None
    assert result.used_citation_keys == [("document", "shared-doc"), ("document", "only-a")]
    # shared-doc 只占 [1]，不会出现 [3] 或重复 [1]
    # [1] 出现在展项 a 行 + 展项 b 行 + 来源行 = 3 次
    assert result.answer.count("[1]") == 3
    assert "[2]" in result.answer
    assert "[3]" not in result.answer


def test_answer_orders_citation_numbers_by_input_order_even_when_duplicates_present():
    inputs = RagAnswerInputs(
        query="去重前顺序",
        citations=[
            _citation("b"),
            _citation("a"),
            _citation("c"),
            # 重复一份 a，应被去重而不影响编号
            _citation("a"),
        ],
        matched_exhibits=[
            _exhibit("ex-1", citations=[_citation("c"), _citation("a")]),
        ],
    )

    result = answer_rag(inputs)

    # 去重后：b -> [1], a -> [2], c -> [3]
    # 展项只挂 c 和 a，第一个匹配的是 c -> 行内显示 [3]
    assert "依据 [3]" in result.answer
    assert result.answer.count("[2]") == 1  # 来源行展示 [2]
    assert result.answer.count("[3]") == 2  # 行内 + 来源行
    # 没有任何命中引用到 [1]（b），但全局答案仍不应出现 [4] 等越界编号
    assert "[4]" not in result.answer
    assert result.used_citation_keys == [
        ("document", "a"),
        ("document", "c"),
    ]


def test_answer_orders_citation_numbers_by_input_order_when_exhibit_references_first():
    """当展项优先引用编号靠前的 citation 时，行内显示其编号。

    未被展项引用的 ``second-doc`` 不会出现在答案中，且也不会进入
    ``used_citation_keys``。
    """

    inputs = RagAnswerInputs(
        query="按引用顺序",
        citations=[
            _citation("first-doc"),
            _citation("second-doc"),
        ],
        matched_exhibits=[
            _exhibit("ex-1", citations=[_citation("first-doc")]),
        ],
    )

    result = answer_rag(inputs)
    assert "依据 [1]" in result.answer
    # only first-doc was actually used; second-doc stays out of the answer body
    assert "[2]" not in result.answer
    assert result.used_citation_keys == [("document", "first-doc")]  


def test_answer_includes_reasoning_signals_via_confidence_boost():
    inputs = RagAnswerInputs(
        query="力学",
        matched_exhibits=[_exhibit("lever")],
        citations=[_citation("guide-1")],
        reasoning_signals=[
            RagReasoningSignal(
                exhibit_id="lever",
                signal_type="graph_neighbor_match",
                detail="相邻节点匹配",
                score=0.8,
            )
        ],
    )

    result = answer_rag(inputs)
    assert result.refusal_reason is None
    assert result.confidence > 0.5
    assert result.warnings == []


def test_answer_warns_when_exhibit_has_no_description():
    inputs = RagAnswerInputs(
        query="缺说明",
        matched_exhibits=[
            _exhibit("blank", description="", citations=[_citation("guide-x")]),
        ],
        citations=[_citation("guide-x")],
    )

    result = answer_rag(inputs)
    assert result.refusal_reason is None
    assert any(NO_DESCRIPTION_WARNING in warning for warning in result.warnings)


# ---------------------------------------------------------------------------
# 拒答场景
# ---------------------------------------------------------------------------


def test_answer_refuses_when_no_citations_no_match():
    result = answer_rag(
        RagAnswerInputs(query="空查询", matched_exhibits=[], citations=[])
    )

    assert result.refusal_reason is not None
    assert NO_MATCH_REFUSAL in result.refusal_reason
    assert NO_CITATION_REFUSAL in result.refusal_reason
    assert result.used_citation_keys == []
    assert result.confidence <= 0.2
    assert "未找到依据" in result.answer


def test_answer_refuses_when_have_match_but_no_citations():
    result = answer_rag(
        RagAnswerInputs(
            query="仅有匹配",
            matched_exhibits=[_exhibit("lever")],
            citations=[],
        )
    )

    assert result.refusal_reason == NO_CITATION_REFUSAL
    assert result.used_citation_keys == []
    assert result.confidence <= 0.4
    assert "[1]" not in result.answer


def test_answer_refuses_when_have_citations_but_no_match():
    result = answer_rag(
        RagAnswerInputs(
            query="仅有来源",
            matched_exhibits=[],
            citations=[_citation("guide-1")],
        )
    )

    assert result.refusal_reason == NO_MATCH_REFUSAL
    assert result.used_citation_keys == []
    assert result.confidence <= 0.4


def test_refusal_answer_never_contains_numbered_invented_citations():
    """缺依据时答案不应出现幻觉引用编号。"""

    result = answer_rag(
        RagAnswerInputs(query="幻觉检查", matched_exhibits=[], citations=[])
    )

    for index in range(1, 6):
        assert f"[{index}]" not in result.answer


# ---------------------------------------------------------------------------
# Provider 接入
# ---------------------------------------------------------------------------


class _StubProvider:
    """测试用 provider，捕获 inputs 并返回预设结果。"""

    def __init__(self, payload: RagAnswerResult | None) -> None:
        self.payload = payload
        self.calls = 0

    def answer(self, inputs: RagAnswerInputs) -> RagAnswerResult | None:
        self.calls += 1
        return self.payload


class _RaisingProvider:
    def answer(self, inputs: RagAnswerInputs) -> RagAnswerResult | None:  # noqa: ARG002
        raise RuntimeError("simulated upstream failure")


def test_provider_returning_valid_result_is_used_directly():
    custom_answer = "自定义答案，引用 [1] 仅作示例。"
    provider = _StubProvider(
        RagAnswerResult(
            answer=custom_answer,
            used_citation_keys=[("document", "doc-x")],
            refusal_reason=None,
            confidence=0.91,
            warnings=["provider-mark"],
        )
    )

    result = answer_rag(
        RagAnswerInputs(
            query="provider 路径",
            matched_exhibits=[_exhibit("lever")],
            citations=[_citation("doc-x")],
        ),
        provider=provider,
    )

    assert provider.calls == 1
    assert result.answer == custom_answer
    assert result.confidence == 0.91
    assert result.warnings == ["provider-mark"]


def test_provider_returning_none_falls_back_to_deterministic():
    provider = _StubProvider(None)

    result = answer_rag(
        RagAnswerInputs(
            query="回退",
            matched_exhibits=[_exhibit("lever", citations=[_citation("guide-1")])],
            citations=[_citation("guide-1")],
        ),
        provider=provider,
    )

    assert provider.calls == 1
    # fallback 行为：包含 [1] 引用
    assert "[1]" in result.answer
    assert result.refusal_reason is None


def test_provider_raising_exception_falls_back_to_deterministic():
    provider = _RaisingProvider()

    result = answer_rag(
        RagAnswerInputs(
            query="provider 抛异常",
            matched_exhibits=[_exhibit("lever", citations=[_citation("guide-1")])],
            citations=[_citation("guide-1")],
        ),
        provider=provider,
    )

    # 不应把异常上抛；fallback 应该产出带 [1] 的答案
    assert "[1]" in result.answer
    assert result.refusal_reason is None


def test_provider_protocol_is_recognized():
    """``RagAnswerProvider`` 必须能被 stub 满足，避免后续重构破坏契约。"""

    class _Conforming:
        def answer(self, inputs: RagAnswerInputs) -> RagAnswerResult | None:  # noqa: ARG002
            return None

    provider: RagAnswerProvider = _Conforming()
    result = answer_rag(
        RagAnswerInputs(
            query="protocol",
            matched_exhibits=[_exhibit("lever", citations=[_citation("guide-1")])],
            citations=[_citation("guide-1")],
        ),
        provider=provider,
    )
    assert result.refusal_reason is None


# ---------------------------------------------------------------------------
# 边界与稳定性
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "query",
    ["", None],
)
def test_answer_rejects_empty_query_inputs(query):
    """``RagAnswerInputs`` 模型自身应在 query 为空时拒绝，避免外层被坑。"""

    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        RagAnswerInputs(
            query=query,  # type: ignore[arg-type]
            matched_exhibits=[],
            citations=[],
        )


def test_answer_keeps_used_citation_keys_only_for_in_answer_ones():
    inputs = RagAnswerInputs(
        query="部分引用",
        citations=[
            _citation("in"),
            _citation("orphan"),
        ],
        matched_exhibits=[
            _exhibit("lever", citations=[_citation("in")]),
        ],
    )

    result = answer_rag(inputs)

    # "orphan" 虽然在 citations 里，但没有挂在任何展项上，不应进入 used_citation_keys
    assert ("document", "orphan") not in result.used_citation_keys
    assert ("document", "in") in result.used_citation_keys


def test_answer_is_deterministic_for_same_inputs():
    inputs = RagAnswerInputs(
        query="稳定",
        matched_exhibits=[_exhibit("lever", citations=[_citation("guide-1")])],
        citations=[_citation("guide-1")],
    )

    first = answer_rag(inputs)
    second = answer_rag(inputs)
    third = answer_rag(inputs)

    assert first.answer == second.answer == third.answer
    assert first.used_citation_keys == second.used_citation_keys == third.used_citation_keys
    assert first.confidence == second.confidence == third.confidence
