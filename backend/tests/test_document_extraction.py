from app.ai.document_extraction import (
    DocumentExtractionInput,
    DocumentTextInput,
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


def test_field_sources_keep_chunk_locations():
    result = extract_document_suggestions(
        DocumentExtractionInput(
            document_id="doc-chunks",
            file_name="space-dome.txt",
            file_type="txt",
            source_note="球幕方案",
            text=None,
            chunks=[
                DocumentTextInput(
                    chunk_id="c1",
                    sequence=1,
                    source_locator="P1",
                    text="主题为宇宙探索，业主：江北科技馆，项目年份：2023。",
                ),
                DocumentTextInput(
                    chunk_id="c2",
                    sequence=2,
                    source_locator="P2",
                    text="预算约 90 万到 160 万，采用钢结构，供应商：星图数字。",
                ),
            ],
        )
    )

    assert result.theme == "宇宙探索"
    assert result.owner == "江北科技馆"
    assert result.supplier == "星图数字"
    assert result.project_year == 2023
    assert result.budget_min == 900000
    assert result.budget_max == 1600000
    assert result.field_sources["theme"][0].chunk_id == "c1"
    assert result.field_sources["supplier"][0].chunk_id == "c2"
    assert result.field_sources["budget_min"][0].source_locator == "P2"


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
