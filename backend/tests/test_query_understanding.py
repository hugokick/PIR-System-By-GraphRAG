from app.ai.query_understanding import understand_query


def test_understand_query_extracts_low_age_children_low_budget_and_theme():
    result = understand_query("找几个适合低龄儿童、预算不高、互动性强的力学展项")

    assert result.original_query == "找几个适合低龄儿童、预算不高、互动性强的力学展项"
    assert result.normalized_query
    assert result.themes == ["力学"]
    assert result.audience == ["low_age_children"]
    assert result.budget_intent == "low"
    assert "互动性强" in result.tags
    assert result.confidence > 0.5


def test_understand_query_extracts_reference_case_and_exclusions():
    result = understand_query("找类似水循环沙盘但预算更低的方案，不考虑沉浸影像")

    assert result.project_case == "水循环沙盘"
    assert result.budget_intent == "lower_than_reference"
    assert result.exclusions == ["沉浸影像"]


def test_understand_query_extracts_explicit_budget_range():
    result = understand_query("找预算 30-50 万的力学展项")

    assert result.themes == ["力学"]
    assert result.budget_min == 300000
    assert result.budget_max == 500000
    assert any("预算区间" in reason for reason in result.reasoning)
