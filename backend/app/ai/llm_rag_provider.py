"""Runtime RAG answer providers.

The default MVP path stays fully offline.  This module adds an optional
OpenAI-compatible chat-completions provider that can be enabled with
environment variables while keeping the existing GraphRAG API contract and
deterministic fallback behavior unchanged.
"""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from typing import Any

import httpx

from .rag_answerer import RagAnswerInputs, RagAnswerProvider, RagAnswerResult

PostJson = Callable[[str, dict[str, Any], dict[str, str], float], dict[str, Any]]


class OpenAICompatibleRagAnswerProvider:
    """RAG answer provider for chat-completions compatible HTTP APIs."""

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        timeout: float = 20.0,
        post_json: PostJson | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self._post_json = post_json or _post_json

    def answer(self, inputs: RagAnswerInputs) -> RagAnswerResult | None:
        payload = {
            "model": self.model,
            "temperature": 0.2,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "你是展陈行业资料库的检索问答助手。只允许依据用户提供的展项候选和引用来源回答，"
                        "不得编造来源。请返回 JSON，字段包括 answer、used_citation_keys、confidence、warnings。"
                    ),
                },
                {"role": "user", "content": _prompt_for_inputs(inputs)},
            ],
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        try:
            response = self._post_json(
                f"{self.base_url}/chat/completions",
                payload,
                headers,
                self.timeout,
            )
            content = response["choices"][0]["message"]["content"]
            return _result_from_content(content)
        except Exception:  # noqa: BLE001 - provider failures must fall back
            return None


def rag_answer_provider_from_env() -> RagAnswerProvider | None:
    provider_name = os.environ.get("RAG_LLM_PROVIDER", "").strip().lower()
    if provider_name not in {"openai-compatible", "openai_compatible"}:
        return None

    base_url = os.environ.get("RAG_LLM_BASE_URL", "").strip()
    api_key = os.environ.get("RAG_LLM_API_KEY", "").strip()
    model = os.environ.get("RAG_LLM_MODEL", "").strip()
    if not base_url or not api_key or not model:
        return None

    timeout = _float_env("RAG_LLM_TIMEOUT_SECONDS", 20.0)
    return OpenAICompatibleRagAnswerProvider(
        base_url=base_url,
        api_key=api_key,
        model=model,
        timeout=timeout,
    )


def _post_json(url: str, payload: dict[str, Any], headers: dict[str, str], timeout: float) -> dict[str, Any]:
    with httpx.Client(timeout=timeout) as client:
        response = client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()


def _prompt_for_inputs(inputs: RagAnswerInputs) -> str:
    exhibits = [
        {
            "id": exhibit.exhibit_id,
            "name": exhibit.exhibit_name,
            "description": exhibit.exhibit_description,
            "reasons": exhibit.reasons,
            "citation_keys": [list(key) for key in exhibit.citation_keys()],
        }
        for exhibit in inputs.matched_exhibits
    ]
    citations = [
        {
            "key": f"{citation.source_type}:{citation.source_id}",
            "source_type": citation.source_type,
            "source_id": citation.source_id,
            "title": citation.title,
            "snippet": citation.snippet,
        }
        for citation in inputs.citations
    ]
    return (
        f"用户问题：{inputs.query}\n"
        "展项候选：\n"
        f"{json.dumps(exhibits, ensure_ascii=False, indent=2)}\n"
        "引用来源：\n"
        f"{json.dumps(citations, ensure_ascii=False, indent=2)}\n"
        "回答要求：\n"
        "- 必须使用 [1]、[2] 形式标注引用。\n"
        "- used_citation_keys 必须是二维数组，例如 [[\"document\", \"doc-id\"]]。\n"
        "- 如果没有足够依据，answer 必须明确说明未找到依据。\n"
    )


def _result_from_content(content: str) -> RagAnswerResult | None:
    parsed = json.loads(content)
    if not isinstance(parsed, dict):
        return None
    answer = str(parsed.get("answer", "")).strip()
    if not answer:
        return None

    used_keys = [
        (str(item[0]), str(item[1]))
        for item in parsed.get("used_citation_keys", [])
        if isinstance(item, (list, tuple)) and len(item) == 2
    ]
    warnings = [
        str(warning)
        for warning in parsed.get("warnings", [])
        if str(warning).strip()
    ]
    confidence = parsed.get("confidence", 0.0)
    return RagAnswerResult(
        answer=answer,
        used_citation_keys=used_keys,
        refusal_reason=parsed.get("refusal_reason"),
        confidence=float(confidence),
        warnings=warnings,
    )


def _float_env(name: str, default: float) -> float:
    value = os.environ.get(name, "").strip()
    if not value:
        return default
    try:
        return float(value)
    except ValueError:
        return default
