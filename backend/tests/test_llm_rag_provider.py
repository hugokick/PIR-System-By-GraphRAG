import json

from app.ai.rag_answerer import RagAnswerInputs, RagCitation, RagMatchedExhibit


def test_openai_compatible_rag_provider_maps_json_answer_to_contract():
    from app.ai.llm_rag_provider import OpenAICompatibleRagAnswerProvider

    calls = []

    def post_json(url, payload, headers, timeout):
        calls.append((url, payload, headers, timeout))
        prompt = payload["messages"][-1]["content"]
        assert "低龄儿童力学展项" in prompt
        assert "杠杆乐园" in prompt
        assert "document:lever-brief" in prompt
        return {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "answer": "可推荐杠杆乐园，依据说明文档 [1]。",
                                "used_citation_keys": [["document", "lever-brief"]],
                                "confidence": 0.82,
                                "warnings": ["由外部 LLM 生成，请人工核验"],
                            },
                            ensure_ascii=False,
                        )
                    }
                }
            ]
        }

    provider = OpenAICompatibleRagAnswerProvider(
        base_url="https://llm.example.test/v1",
        api_key="secret-token",
        model="demo-chat",
        post_json=post_json,
        timeout=9.5,
    )

    result = provider.answer(
        RagAnswerInputs(
            query="低龄儿童力学展项",
            matched_exhibits=[
                RagMatchedExhibit(
                    exhibit_id="lever-play",
                    exhibit_name="杠杆乐园",
                    exhibit_description="通过杠杆机械结构解释省力原理。",
                    reasons=["匹配主题：力学"],
                    citations=[
                        RagCitation(
                            source_id="lever-brief",
                            source_type="document",
                            title="杠杆乐园展项说明",
                            snippet="适合低龄儿童的力学互动展项。",
                        )
                    ],
                )
            ],
            citations=[
                RagCitation(
                    source_id="lever-brief",
                    source_type="document",
                    title="杠杆乐园展项说明",
                    snippet="适合低龄儿童的力学互动展项。",
                )
            ],
        )
    )

    assert result is not None
    assert result.answer == "可推荐杠杆乐园，依据说明文档 [1]。"
    assert result.used_citation_keys == [("document", "lever-brief")]
    assert result.confidence == 0.82
    assert result.warnings == ["由外部 LLM 生成，请人工核验"]
    assert calls[0][0] == "https://llm.example.test/v1/chat/completions"
    assert calls[0][1]["model"] == "demo-chat"
    assert calls[0][2]["Authorization"] == "Bearer secret-token"
    assert calls[0][3] == 9.5


def test_rag_answer_provider_from_env_builds_only_when_configured(monkeypatch):
    from app.ai.llm_rag_provider import (
        OpenAICompatibleRagAnswerProvider,
        rag_answer_provider_from_env,
    )

    assert rag_answer_provider_from_env() is None

    monkeypatch.setenv("RAG_LLM_PROVIDER", "openai-compatible")
    monkeypatch.setenv("RAG_LLM_BASE_URL", "https://llm.example.test/v1/")
    monkeypatch.setenv("RAG_LLM_API_KEY", "secret-token")
    monkeypatch.setenv("RAG_LLM_MODEL", "demo-chat")

    provider = rag_answer_provider_from_env()

    assert isinstance(provider, OpenAICompatibleRagAnswerProvider)
