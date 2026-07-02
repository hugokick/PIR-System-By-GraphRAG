from app.repository import seed_exhibits
from app.services.embeddings import (
    EMBEDDING_DIMENSIONS,
    OpenAICompatibleEmbeddingProvider,
    embedding_text_for_document_chunk,
    embedding_text_for_exhibit,
    embedding_vector,
    embedding_provider_from_env,
    stable_embedding,
    vector_literal,
)


def test_stable_embedding_is_deterministic_and_has_expected_dimensions():
    first = stable_embedding("低龄儿童 力学 机械互动")
    second = stable_embedding("低龄儿童 力学 机械互动")

    assert first == second
    assert len(first) == EMBEDDING_DIMENSIONS == 1536
    assert any(value != 0 for value in first)


def test_embedding_text_for_exhibit_includes_searchable_business_fields():
    text = embedding_text_for_exhibit(seed_exhibits[0])

    assert "lever-play" in text
    assert "杠杆乐园" in text
    assert "力学" in text
    assert "儿童科技馆" in text
    assert "机械互动" in text
    assert "低龄儿童" in text


def test_embedding_text_for_document_chunk_keeps_source_identity_and_content():
    document = seed_exhibits[0].documents[0]
    chunk = document.chunks[0] if document.chunks else None

    text = embedding_text_for_document_chunk(seed_exhibits[0], document, chunk)

    assert "lever-play" in text
    assert "杠杆乐园" in text
    assert "杠杆乐园展项说明" in text
    assert document.source_note in text


def test_vector_literal_serializes_embedding_for_pgvector_parameter_cast():
    literal = vector_literal([0.1, -0.25, 0.0])

    assert literal == "[0.100000,-0.250000,0.000000]"


def test_openai_compatible_embedding_provider_maps_response_vector():
    calls = []

    def post_json(url, payload, headers, timeout):
        calls.append((url, payload, headers, timeout))
        assert payload == {"model": "demo-embedding", "input": "低龄儿童 力学"}
        return {"data": [{"embedding": [0.1, -0.2, 0.3]}]}

    provider = OpenAICompatibleEmbeddingProvider(
        base_url="https://embedding.example.test/v1/",
        api_key="secret-token",
        model="demo-embedding",
        dimensions=3,
        post_json=post_json,
        timeout=8.5,
    )

    assert provider.embed("低龄儿童 力学") == [0.1, -0.2, 0.3]
    assert calls[0][0] == "https://embedding.example.test/v1/embeddings"
    assert calls[0][2]["Authorization"] == "Bearer secret-token"
    assert calls[0][3] == 8.5


def test_embedding_vector_uses_provider_and_falls_back_on_invalid_output():
    stable = stable_embedding("低龄儿童 力学", dimensions=3)

    class GoodProvider:
        def embed(self, text):
            assert text == "低龄儿童 力学"
            return [0.2, 0.3, 0.4]

    class BadProvider:
        def embed(self, text):
            return [0.1]

    assert embedding_vector("低龄儿童 力学", dimensions=3, provider=GoodProvider()) == [0.2, 0.3, 0.4]
    assert embedding_vector("低龄儿童 力学", dimensions=3, provider=BadProvider()) == stable
    assert embedding_vector("低龄儿童 力学", dimensions=3, provider=None) == stable


def test_embedding_provider_from_env_builds_only_when_configured(monkeypatch):
    assert embedding_provider_from_env() is None

    monkeypatch.setenv("EMBEDDING_PROVIDER", "openai-compatible")
    monkeypatch.setenv("EMBEDDING_BASE_URL", "https://embedding.example.test/v1")
    monkeypatch.setenv("EMBEDDING_API_KEY", "secret-token")
    monkeypatch.setenv("EMBEDDING_MODEL", "demo-embedding")
    monkeypatch.setenv("EMBEDDING_DIMENSIONS", "3")

    provider = embedding_provider_from_env()

    assert isinstance(provider, OpenAICompatibleEmbeddingProvider)
