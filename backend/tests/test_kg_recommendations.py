"""``backend/app/kg/recommendations`` 的单元测试。"""

from __future__ import annotations

import pytest

from app.kg.builder import build_exhibit_kg_snapshot
from app.kg.recommendations import (
    DOC_CHUNK_PER_SHARED,
    INTERACTION_PER_SHARED,
    MATERIAL_PER_SHARED,
    MISSING_TARGET_WARNING,
    TAG_PER_SHARED,
    THEME_SHARED_WEIGHT,
    DocumentChunkRef,
    RecommendationInputs,
    RecommendationResult,
    RelationRecommendation,
    recommend_relations,
)
from app.schemas import (
    DocumentAsset,
    DocumentChunk,
    EntityRef,
    ExhibitResponse,
    MediaAsset,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _entity(entity_id: str, name: str | None = None) -> EntityRef:
    return EntityRef(id=entity_id, name=name or entity_id)


def _exhibit(
    exhibit_id: str,
    *,
    name: str | None = None,
    theme_id: str = "mechanics",
    material_ids: tuple[str, ...] = (),
    interaction_ids: tuple[str, ...] = (),
    tags: tuple[str, ...] = (),
    documents: tuple[DocumentAsset, ...] = (),
    related_exhibit_ids: tuple[str, ...] = (),
) -> ExhibitResponse:
    return ExhibitResponse(
        id=exhibit_id,
        name=name or f"展项-{exhibit_id}",
        category="interactive",
        theme=_entity(theme_id),
        venue_type="科技馆",
        budget_min=100000,
        budget_max=200000,
        materials=[_entity(mid) for mid in material_ids],
        dimensions="标准",
        interactions=[_entity(iid) for iid in interaction_ids],
        supplier=_entity("supplier-default"),
        project=_entity("project-default"),
        owner=_entity("owner-default"),
        project_year=2025,
        status="在库",
        review_status="已审核",
        description="示例展项",
        tags=list(tags),
        media_assets=[MediaAsset(id="m1", type="image", name="cover.png", url="/uploads/cover.png")],
        documents=list(documents),
        related_exhibit_ids=list(related_exhibit_ids),
    )


def _document(doc_id: str, chunks: tuple[tuple[int, str], ...]) -> DocumentAsset:
    return DocumentAsset(
        id=doc_id,
        name=f"document-{doc_id}",
        file_type="md",
        url=f"/uploads/{doc_id}.md",
        source_note="示例资料",
        chunks=[
            DocumentChunk(id=f"{doc_id}-chunk-{seq}", text=text, sequence=seq)
            for seq, text in chunks
        ],
    )


# ---------------------------------------------------------------------------
# similar_to 主动推荐
# ---------------------------------------------------------------------------


def test_recommends_similar_to_when_shared_theme():
    target = _exhibit("target", theme_id="mechanics")
    others = [
        _exhibit("other-a", theme_id="mechanics"),
        _exhibit("other-b", theme_id="astronomy"),
    ]

    result = recommend_relations(
        RecommendationInputs(target_exhibit=target, all_exhibits=[target, *others])
    )

    similar = [r for r in result.recommendations if r.relation_type == "similar_to"]
    by_target = {r.target_id: r for r in similar}

    assert "other-a" in by_target
    assert "other-b" not in by_target
    assert any("共同主题" in reason for reason in by_target["other-a"].reasons)
    assert "theme:mechanics" in by_target["other-a"].evidence_refs


def test_recommends_similar_to_when_shared_materials():
    target = _exhibit("target", theme_id="mechanics", material_ids=("metal", "wood"))
    others = [
        # 仅材料重叠：与 target 主题不同
        _exhibit("a", theme_id="astronomy", material_ids=("metal", "glass")),
        _exhibit("b", theme_id="biology", material_ids=("plastic",)),
    ]

    result = recommend_relations(
        RecommendationInputs(target_exhibit=target, all_exhibits=[target, *others])
    )

    similar = {r.target_id: r for r in result.recommendations if r.relation_type == "similar_to"}

    assert "a" in similar
    assert "b" not in similar
    assert similar["a"].confidence == pytest.approx(MATERIAL_PER_SHARED, rel=1e-3)
    assert "material:metal" in similar["a"].evidence_refs


def test_recommends_similar_to_when_shared_interactions():
    target = _exhibit("target", theme_id="mechanics", interaction_ids=("mechanical", "touch"))
    others = [
        # 仅互动重叠：与 target 主题不同
        _exhibit("a", theme_id="astronomy", interaction_ids=("touch", "voice")),
        _exhibit("b", theme_id="biology", interaction_ids=("rotation",)),
    ]

    result = recommend_relations(
        RecommendationInputs(target_exhibit=target, all_exhibits=[target, *others])
    )

    similar = {r.target_id: r for r in result.recommendations if r.relation_type == "similar_to"}

    assert "a" in similar
    assert "b" not in similar
    assert similar["a"].confidence == pytest.approx(INTERACTION_PER_SHARED, rel=1e-3)
    assert "interaction:touch" in similar["a"].evidence_refs


def test_recommends_similar_to_when_shared_tags():
    target = _exhibit("target", tags=("low_age", "physical"))
    other = _exhibit("other", tags=("low_age", "physical", "extra"))

    result = recommend_relations(
        RecommendationInputs(
            target_exhibit=target,
            all_exhibits=[target, other],
        )
    )

    similar = {r.target_id: r for r in result.recommendations if r.relation_type == "similar_to"}
    assert "other" in similar
    assert similar["other"].confidence >= TAG_PER_SHARED * 2 - 1e-9
    assert any("共同标签" in reason for reason in similar["other"].reasons)


def test_recommends_similar_to_when_shared_document_chunks():
    target = _exhibit(
        "target",
        documents=(
            _document("d1", ((1, "共享片段 A"), (2, "target 独有"))),
        ),
    )
    other = _exhibit(
        "other",
        documents=(
            _document("d1", ((1, "共享片段 A"), (3, "other 独有"))),
        ),
    )

    extra_input = DocumentChunkRef(
        exhibit_id="other",
        document_id="d1",
        chunk_id="d1-extra-shared",
        text="通过外部输入共享的片段",
    )

    target_extra = DocumentChunkRef(
        exhibit_id="target",
        document_id="d1",
        chunk_id="d1-extra-shared",
        text="通过外部输入共享的片段",
    )

    result = recommend_relations(
        RecommendationInputs(
            target_exhibit=target,
            all_exhibits=[target, other],
            document_chunks=[extra_input, target_extra],
        )
    )

    similar = {r.target_id: r for r in result.recommendations if r.relation_type == "similar_to"}
    assert "other" in similar
    assert similar["other"].confidence >= DOC_CHUNK_PER_SHARED * 2 - 1e-9
    assert "d1-extra-shared" in similar["other"].evidence_refs


def test_skips_self_reference_in_similar_to():
    target = _exhibit("target", theme_id="mechanics")

    result = recommend_relations(
        RecommendationInputs(target_exhibit=target, all_exhibits=[target])
    )

    similar = [r for r in result.recommendations if r.relation_type == "similar_to"]
    assert all(r.target_id != "target" for r in similar)


def test_no_similar_to_when_zero_overlap():
    target = _exhibit(
        "target",
        theme_id="mechanics",
        material_ids=("metal",),
        interaction_ids=("touch",),
        tags=("t1",),
    )
    other = _exhibit(
        "other",
        theme_id="astronomy",
        material_ids=("plastic",),
        interaction_ids=("voice",),
        tags=("t2",),
    )

    result = recommend_relations(
        RecommendationInputs(target_exhibit=target, all_exhibits=[target, other])
    )

    similar = [r for r in result.recommendations if r.relation_type == "similar_to"]
    assert similar == []


# ---------------------------------------------------------------------------
# already_exists 标记
# ---------------------------------------------------------------------------


def test_similar_to_marks_already_exists_when_relation_in_snapshot():
    target = _exhibit(
        "target",
        theme_id="mechanics",
        related_exhibit_ids=("other",),
    )
    other = _exhibit("other", theme_id="mechanics")

    result = recommend_relations(
        RecommendationInputs(target_exhibit=target, all_exhibits=[target, other])
    )

    similar = [r for r in result.recommendations if r.relation_type == "similar_to"]
    assert similar
    assert similar[0].target_id == "other"
    assert similar[0].already_exists is True


def test_similar_to_marks_already_exists_in_both_directions():
    """snapshot 中若 other->target 已存在，应同样标记 already_exists。"""

    target = _exhibit("target", theme_id="mechanics")
    other = _exhibit(
        "other",
        theme_id="mechanics",
        related_exhibit_ids=("target",),
    )

    result = recommend_relations(
        RecommendationInputs(target_exhibit=target, all_exhibits=[target, other])
    )

    similar = [r for r in result.recommendations if r.relation_type == "similar_to"]
    assert similar
    assert similar[0].already_exists is True


def test_typed_relations_appear_as_already_exists_with_full_evidence():
    target = _exhibit(
        "target",
        theme_id="mechanics",
        material_ids=("metal", "wood"),
        interaction_ids=("touch",),
    )
    other = _exhibit("other")

    snapshot = build_exhibit_kg_snapshot([target, other])
    result = recommend_relations(
        RecommendationInputs(
            target_exhibit=target,
            all_exhibits=[target, other],
            snapshot=snapshot,
        )
    )

    typed = [r for r in result.recommendations if r.relation_type != "similar_to"]
    relation_types = {r.relation_type for r in typed}
    assert {
        "has_theme",
        "uses_material",
        "has_interaction",
        "supplied_by",
        "owned_by",
        "belongs_to_project",
    } <= relation_types

    for record in typed:
        assert record.already_exists is True
        assert record.confidence == 1.0
        assert record.source_id == "target"
        # evidence_refs 应是完整的 KG 节点 id，type 前缀与 KG 边 target 一致
        evidence_id = record.evidence_refs[0]
        assert ":" in evidence_id
        # 例如 uses_material -> material:metal; has_theme -> theme:mechanics
        expected_prefix = {
            "has_theme": "theme:",
            "uses_material": "material:",
            "has_interaction": "interaction:",
            "supplied_by": "supplier:",
            "owned_by": "owner:",
            "belongs_to_project": "project:",
        }[record.relation_type]
        assert evidence_id.startswith(expected_prefix)
        assert record.target_label  # 应给出可读 label


def test_typed_relation_dedupes_when_snapshot_has_duplicate_edges():
    """snapshot 即使重复出现同一条 typed 边，推荐结果也应去重。"""

    from app.kg.models import KGEdge, KGNode, KGSnapshot

    target_node = KGNode(id="exhibit:target", type="exhibit", label="target")
    material_node = KGNode(id="material:metal", type="material", label="金属")
    edge = KGEdge(source="exhibit:target", target="material:metal", type="uses_material", label="使用材料")
    duplicate = edge.model_copy(deep=True)

    snapshot = KGSnapshot(
        nodes=[target_node, material_node],
        edges=[edge, duplicate],
        evidences=[],
        adjacency={"exhibit:target": ["material:metal"]},
        warnings=[],
    )

    target = _exhibit("target", material_ids=("metal",))

    result = recommend_relations(
        RecommendationInputs(
            target_exhibit=target,
            all_exhibits=[target],
            snapshot=snapshot,
        )
    )

    uses_material = [r for r in result.recommendations if r.relation_type == "uses_material"]
    assert len(uses_material) == 1


# ---------------------------------------------------------------------------
# 安全 / 边缘场景
# ---------------------------------------------------------------------------


def test_returns_empty_with_warning_when_target_exhibit_missing():
    result = recommend_relations(
        RecommendationInputs(target_exhibit=None, all_exhibits=[_exhibit("o")])
    )

    assert result.target_exhibit_id is None
    assert result.recommendations == []
    assert MISSING_TARGET_WARNING in result.warnings


def test_returns_empty_similar_when_no_overlap_and_keeps_typed_relations():
    target = _exhibit("target", theme_id="mechanics", material_ids=("metal",))
    other = _exhibit("other", theme_id="astronomy", material_ids=("plastic",))

    snapshot = build_exhibit_kg_snapshot([target, other])
    result = recommend_relations(
        RecommendationInputs(
            target_exhibit=target,
            all_exhibits=[target, other],
            snapshot=snapshot,
        )
    )

    similar = [r for r in result.recommendations if r.relation_type == "similar_to"]
    typed = [r for r in result.recommendations if r.relation_type != "similar_to"]
    assert similar == []
    assert typed  # typed 关系仍按 snapshot 镜像


def test_uses_passed_snapshot_without_rebuilding():
    """传入 snapshot 时不应再调用 builder；snapshot.warnings 应被透传。"""

    target = _exhibit("target", theme_id="mechanics")
    other = _exhibit("other", theme_id="mechanics")

    snapshot = build_exhibit_kg_snapshot([target, other])
    snapshot = snapshot.model_copy(update={"warnings": ["custom-warning-from-snapshot"]})

    result = recommend_relations(
        RecommendationInputs(
            target_exhibit=target,
            all_exhibits=[target, other],
            snapshot=snapshot,
        )
    )

    assert "custom-warning-from-snapshot" in result.warnings


def test_module_does_not_modify_inputs():
    """recommend_relations 必须是纯函数，不得修改输入。"""

    target = _exhibit(
        "target",
        theme_id="mechanics",
        material_ids=("metal",),
        related_exhibit_ids=("other",),
    )
    other = _exhibit("other", theme_id="mechanics")
    snapshot = build_exhibit_kg_snapshot([target, other])
    original_edges = list(snapshot.edges)
    original_nodes = list(snapshot.nodes)
    original_related = list(target.related_exhibit_ids)
    original_tags = list(target.tags)

    inputs = RecommendationInputs(
        target_exhibit=target,
        all_exhibits=[target, other],
        snapshot=snapshot,
    )
    recommend_relations(inputs)

    assert snapshot.edges == original_edges
    assert snapshot.nodes == original_nodes
    assert target.related_exhibit_ids == original_related
    assert target.tags == original_tags


# ---------------------------------------------------------------------------
# 排序稳定性
# ---------------------------------------------------------------------------


def test_recommendations_sorted_by_confidence_desc_then_stable_keys():
    target = _exhibit("target", theme_id="mechanics")
    # 制造有梯度得分差异的候选
    a = _exhibit("a", theme_id="mechanics", material_ids=("metal", "wood"))
    b = _exhibit("b", theme_id="mechanics", material_ids=("metal",))
    c = _exhibit("c", theme_id="mechanics")
    d = _exhibit("d", theme_id="astronomy")  # 零重叠，不应出现

    snapshot = build_exhibit_kg_snapshot([target, a, b, c, d])

    first = recommend_relations(
        RecommendationInputs(
            target_exhibit=target, all_exhibits=[target, a, b, c, d], snapshot=snapshot
        )
    )
    second = recommend_relations(
        RecommendationInputs(
            target_exhibit=target, all_exhibits=[target, a, b, c, d], snapshot=snapshot
        )
    )

    similar_first = [r.target_id for r in first.recommendations if r.relation_type == "similar_to"]
    similar_second = [r.target_id for r in second.recommendations if r.relation_type == "similar_to"]

    assert similar_first == similar_second
    assert "d" not in similar_first

    # a 应排第一：theme + material*2 = 0.4 + 0.3 = 0.7
    # b 应排第二：theme + material*1 = 0.4 + 0.15 = 0.55
    # c 应排第三：theme only = 0.4
    confidences = [
        r.confidence for r in first.recommendations
        if r.relation_type == "similar_to"
    ]
    assert confidences == sorted(confidences, reverse=True)
    assert similar_first[0] == "a"
    assert similar_first[1] == "b"
    assert similar_first[2] == "c"


def test_recommendations_with_tied_confidence_use_relation_type_then_target_id_as_tiebreaker():
    """同等 confidence 下，relation_type 与 target_id 应作为稳定破缺。

    通过让 other 展项与 target 主题不同，避免 similar_to 候选，
    所有 typed 边因此都是 confidence=1.0，便于构造纯平局排序。
    """

    target = _exhibit("target", theme_id="mechanics")
    other = _exhibit("other", theme_id="astronomy")

    snapshot = build_exhibit_kg_snapshot([target, other])

    result = recommend_relations(
        RecommendationInputs(
            target_exhibit=target,
            all_exhibits=[target, other],
            snapshot=snapshot,
        )
    )

    similar = [r for r in result.recommendations if r.relation_type == "similar_to"]
    assert similar == []

    confidences = [r.confidence for r in result.recommendations]
    assert all(c == 1.0 for c in confidences)

    keys = [(r.relation_type, r.target_id, r.source_id) for r in result.recommendations]
    assert keys == sorted(keys)


# ---------------------------------------------------------------------------
# 参数化校验
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("relation_type", [
    "has_theme",
    "uses_material",
    "has_interaction",
    "supplied_by",
    "owned_by",
    "belongs_to_project",
])
def test_each_typed_relation_can_appear_in_output(relation_type):
    """每种 typed 关系都应在 snapshot 中出现，并在结果中以 already_exists=True 输出。

    target 必须给出全部依赖字段，否则 builder 不会发出对应的边。
    """

    target = _exhibit(
        "target",
        theme_id="mechanics",
        material_ids=("metal",),
        interaction_ids=("touch",),
    )
    other = _exhibit(
        "other",
        theme_id="astronomy",
        material_ids=("plastic",),
        interaction_ids=("rotation",),
    )
    snapshot = build_exhibit_kg_snapshot([target, other])

    result = recommend_relations(
        RecommendationInputs(
            target_exhibit=target,
            all_exhibits=[target, other],
            snapshot=snapshot,
        )
    )

    relations = {r.relation_type: r for r in result.recommendations}
    assert relation_type in relations
    assert relations[relation_type].already_exists is True


def test_saturation_caps_confidence_at_one():
    """多个高权重信号叠加时，confidence 应被截断在 1.0。"""

    target = _exhibit(
        "target",
        theme_id="mechanics",
        material_ids=("m1", "m2", "m3"),
        interaction_ids=("i1", "i2", "i3"),
        tags=("t1", "t2", "t3"),
    )
    other = _exhibit(
        "other",
        theme_id="mechanics",
        material_ids=("m1", "m2", "m3"),
        interaction_ids=("i1", "i2", "i3"),
        tags=("t1", "t2", "t3"),
    )

    result = recommend_relations(
        RecommendationInputs(target_exhibit=target, all_exhibits=[target, other])
    )

    similar = [r for r in result.recommendations if r.relation_type == "similar_to"]
    assert similar
    assert similar[0].confidence == pytest.approx(min(
        (
            THEME_SHARED_WEIGHT
            + MATERIAL_PER_SHARED * 3
            + INTERACTION_PER_SHARED * 3
            + TAG_PER_SHARED * 3
        ),
        1.0,
    ), rel=1e-3)


# ---------------------------------------------------------------------------
# 契约层 sanity
# ---------------------------------------------------------------------------


def test_output_models_are_pydantic_and_serializable():
    target = _exhibit("target", theme_id="mechanics")
    other = _exhibit("other", theme_id="mechanics")

    result = recommend_relations(
        RecommendationInputs(target_exhibit=target, all_exhibits=[target, other])
    )

    assert isinstance(result, RecommendationResult)
    for record in result.recommendations:
        assert isinstance(record, RelationRecommendation)
        dumped = record.model_dump()
        assert "relation_type" in dumped
        assert "confidence" in dumped
        assert "already_exists" in dumped
