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
