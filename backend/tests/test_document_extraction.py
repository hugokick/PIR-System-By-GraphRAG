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
