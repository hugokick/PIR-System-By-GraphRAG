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


def test_understand_query_extracts_venue_type_interaction_and_tag():
    result = understand_query("有没有适合县级科技馆、维护成本低、机械互动的展品？")

    assert result.venue_types == ["县级科技馆"]
    assert result.interactions == ["机械互动"]
    assert "维护成本低" in result.tags


def test_understand_query_extracts_reference_case_and_lower_budget_intent():
    result = understand_query("找类似水循环沙盘但预算更低的方案")

    assert result.project_case == "水循环沙盘"
    assert result.budget_intent == "lower_than_reference"


def test_understand_query_extracts_exclusions():
    result = understand_query("找力学展项，但不要水景，也不考虑沉浸影像")

    assert result.themes == ["力学"]
    assert result.exclusions == ["水景", "沉浸影像"]


def test_understand_query_returns_low_confidence_for_empty_or_weak_query():
    result = understand_query("推荐一下")

    assert result.themes == []
    assert result.venue_types == []
    assert result.audience == []
    assert result.budget_intent == "unknown"
    assert result.confidence < 0.4
    assert any("未识别出有效检索槽位" in item for item in result.reasoning)


class NoneProvider:
    def understand(self, query: str):
        return None


def test_understand_query_falls_back_to_rules_when_provider_returns_none():
    result = understand_query("低龄儿童 力学", provider=NoneProvider())

    assert result.themes == ["力学"]
    assert result.audience == ["low_age_children"]
    assert result.budget_intent == "unknown"
