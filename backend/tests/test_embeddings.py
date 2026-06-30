from app.repository import seed_exhibits
from app.services.embeddings import (
    EMBEDDING_DIMENSIONS,
    embedding_text_for_document_chunk,
    embedding_text_for_exhibit,
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
