"""知识图谱关系推荐模块。

只读分析现有展项档案、可选 KG snapshot 与可选 document chunks，输出潜在
图谱关系候选。**不修改任何 KG 写入路径**，调用方可决定是否写入。

设计要点：

- 主动推断 ``similar_to``：基于共同 theme / material / interaction / tag
  / document chunk 计算相似度得分，并附带 reasons 与 evidence_refs。
- 被动镜像其他 6 种关系类型（``has_theme``、``uses_material``、
  ``has_interaction``、``supplied_by``、``owned_by``、
  ``belongs_to_project``）从 snapshot 中读取当前已存在的图谱边，并标
  ``already_exists=True``，便于审计和解释当前图谱结构。
- 全部不主动"补写"已有关系的延伸建议，避免与 ``kg/builder``、
  ``kg/sync`` 的事实写入路径冲突。
- 排序键固定为 ``(-confidence, relation_type, target_id, source_id)``，
  保证稳定可重现。
"""

from __future__ import annotations

from typing import Iterable, Literal, Sequence

from pydantic import BaseModel, Field

from app.schemas import DocumentAsset, EntityRef, ExhibitResponse

from .builder import build_exhibit_kg_snapshot
from .models import KGSnapshot


# ---------------------------------------------------------------------------
# 推荐权重与上限
# ---------------------------------------------------------------------------

THEME_SHARED_WEIGHT = 0.4
MATERIAL_PER_SHARED = 0.15
INTERACTION_PER_SHARED = 0.15
TAG_PER_SHARED = 0.05
DOC_CHUNK_PER_SHARED = 0.1
CONFIDENCE_SATURATION = 1.0

EDGE_TYPE_TO_RELATION = {
    "has_theme": "has_theme",
    "uses_material": "uses_material",
    "has_interaction": "has_interaction",
    "supplied_by": "supplied_by",
    "owned_by": "owned_by",
    "belongs_to_project": "belongs_to_project",
}


RelationType = Literal[
    "similar_to",
    "has_theme",
    "uses_material",
    "has_interaction",
    "supplied_by",
    "owned_by",
    "belongs_to_project",
]


MISSING_TARGET_WARNING = "missing target_exhibit"


# ---------------------------------------------------------------------------
# 数据契约
# ---------------------------------------------------------------------------


class DocumentChunkRef(BaseModel):
    """外部输入的文档片段引用，独立于 ``ExhibitResponse.documents``。"""

    exhibit_id: str
    document_id: str
    chunk_id: str
    text: str = ""


class RelationRecommendation(BaseModel):
    """一条关系推荐记录。"""

    relation_type: RelationType
    source_id: str
    target_id: str
    target_label: str
    confidence: float
    reasons: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    already_exists: bool


class RecommendationInputs(BaseModel):
    """``recommend_relations`` 的输入参数。"""

    target_exhibit: ExhibitResponse | None = None
    all_exhibits: list[ExhibitResponse] = Field(default_factory=list)
    snapshot: KGSnapshot | None = None
    document_chunks: list[DocumentChunkRef] = Field(default_factory=list)


class RecommendationResult(BaseModel):
    """``recommend_relations`` 的输出。"""

    target_exhibit_id: str | None = None
    warnings: list[str] = Field(default_factory=list)
    recommendations: list[RelationRecommendation] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# 公共入口
# ---------------------------------------------------------------------------


def recommend_relations(inputs: RecommendationInputs) -> RecommendationResult:
    """根据输入返回关系推荐集合。

    安全语义：

    - ``target_exhibit is None`` → 返回空 ``recommendations`` 并写一条
      warning；不会抛错。
    - ``snapshot is None`` → 调用 ``build_exhibit_kg_snapshot`` 构造一次性
      内存快照作为只读索引；纯函数调用，不修改任何持久化状态。
    - 自身展项 (``target.id == other.id``) 自动跳过，不输出 ``similar_to``
      自引用。
    """

    if inputs.target_exhibit is None:
        return RecommendationResult(
            target_exhibit_id=None,
            warnings=[MISSING_TARGET_WARNING],
            recommendations=[],
        )

    target = inputs.target_exhibit
    snapshot = inputs.snapshot or build_exhibit_kg_snapshot(inputs.all_exhibits)

    existing_pairs = _existing_similar_pairs(snapshot)
    similar_recs = _recommend_similar_to(
        target=target,
        all_exhibits=inputs.all_exhibits,
        existing_pairs=existing_pairs,
        document_chunks=inputs.document_chunks,
    )
    typed_recs = _list_existing_typed_relations(target=target, snapshot=snapshot)

    recommendations = sorted(
        similar_recs + typed_recs,
        key=_sort_key,
    )

    return RecommendationResult(
        target_exhibit_id=target.id,
        warnings=list(snapshot.warnings),
        recommendations=recommendations,
    )


# ---------------------------------------------------------------------------
# similar_to 主动推荐
# ---------------------------------------------------------------------------


def _recommend_similar_to(
    *,
    target: ExhibitResponse,
    all_exhibits: Sequence[ExhibitResponse],
    existing_pairs: set[tuple[str, str]],
    document_chunks: Sequence[DocumentChunkRef],
) -> list[RelationRecommendation]:
    target_id = target.id
    target_node = f"exhibit:{target_id}"
    target_theme_id = target.theme.id
    target_materials = {m.id for m in target.materials}
    target_interactions = {i.id for i in target.interactions}
    target_tags = set(target.tags)
    target_chunk_ids = _chunk_ids_for(target.id, target.documents, document_chunks)

    recs: list[RelationRecommendation] = []
    for other in all_exhibits:
        if other.id == target_id:
            continue

        score = 0.0
        reasons: list[str] = []
        evidence: list[str] = []

        if other.theme.id == target_theme_id:
            score += THEME_SHARED_WEIGHT
            evidence.append(f"theme:{target_theme_id}")
            reasons.append(f"共同主题：{target.theme.name}")

        shared_materials = sorted(target_materials & {m.id for m in other.materials})
        if shared_materials:
            score += MATERIAL_PER_SHARED * len(shared_materials)
            evidence.extend(f"material:{mid}" for mid in shared_materials)
            names = _names_by_id(other.materials, shared_materials)
            reasons.append(f"共同材料（{len(shared_materials)}）：{'、'.join(names)}")

        shared_interactions = sorted(
            target_interactions & {i.id for i in other.interactions}
        )
        if shared_interactions:
            score += INTERACTION_PER_SHARED * len(shared_interactions)
            evidence.extend(f"interaction:{iid}" for iid in shared_interactions)
            names = _names_by_id(other.interactions, shared_interactions)
            reasons.append(f"共同互动（{len(shared_interactions)}）：{'、'.join(names)}")

        shared_tags = sorted(target_tags & set(other.tags))
        if shared_tags:
            score += TAG_PER_SHARED * len(shared_tags)
            reasons.append(f"共同标签（{len(shared_tags)}）：{'、'.join(shared_tags)}")

        other_chunk_ids = _chunk_ids_for(other.id, other.documents, document_chunks)
        shared_chunks = sorted(target_chunk_ids & other_chunk_ids)
        if shared_chunks:
            score += DOC_CHUNK_PER_SHARED * len(shared_chunks)
            evidence.extend(shared_chunks)
            reasons.append(f"共享文档片段（{len(shared_chunks)}）")

        if score <= 0:
            continue

        confidence = min(score / CONFIDENCE_SATURATION, CONFIDENCE_SATURATION)
        other_node = f"exhibit:{other.id}"
        already = (target_node, other_node) in existing_pairs or (
            other_node,
            target_node,
        ) in existing_pairs

        recs.append(
            RelationRecommendation(
                relation_type="similar_to",
                source_id=target_id,
                target_id=other.id,
                target_label=other.name,
                confidence=round(confidence, 3),
                reasons=reasons,
                evidence_refs=evidence,
                already_exists=already,
            )
        )

    return recs


# ---------------------------------------------------------------------------
# 已有 typed 关系镜像
# ---------------------------------------------------------------------------


def _list_existing_typed_relations(
    *,
    target: ExhibitResponse,
    snapshot: KGSnapshot,
) -> list[RelationRecommendation]:
    target_node = f"exhibit:{target.id}"
    nodes_by_id = {node.id: node for node in snapshot.nodes}

    recommendations: list[RelationRecommendation] = []
    seen: set[tuple[str, str]] = set()

    for edge in snapshot.edges:
        if edge.source != target_node:
            continue
        relation_type = EDGE_TYPE_TO_RELATION.get(edge.type)
        if relation_type is None:
            continue
        key = (relation_type, edge.target)
        if key in seen:
            continue
        seen.add(key)

        node = nodes_by_id.get(edge.target)
        label = node.label if node else edge.target
        target_raw_id = (
            edge.target.split(":", 1)[-1] if ":" in edge.target else edge.target
        )

        recommendations.append(
            RelationRecommendation(
                relation_type=relation_type,  # type: ignore[arg-type]
                source_id=target.id,
                target_id=target_raw_id,
                target_label=label,
                confidence=1.0,
                reasons=[f"已存在的图谱边：{edge.type}"],
                evidence_refs=[edge.target],
                already_exists=True,
            )
        )

    return recommendations


# ---------------------------------------------------------------------------
# 内部辅助
# ---------------------------------------------------------------------------


def _existing_similar_pairs(snapshot: KGSnapshot) -> set[tuple[str, str]]:
    pairs: set[tuple[str, str]] = set()
    for edge in snapshot.edges:
        if edge.type == "similar_to":
            pairs.add((edge.source, edge.target))
    return pairs


def _names_by_id(items: Iterable[EntityRef], ids: Iterable[str]) -> list[str]:
    by_id = {item.id: item.name for item in items}
    return [by_id[item_id] for item_id in ids if item_id in by_id]


def _chunk_ids_for(
    exhibit_id: str,
    documents: Sequence[DocumentAsset],
    extra: Sequence[DocumentChunkRef],
) -> set[str]:
    chunk_ids: set[str] = set()
    for document in documents:
        for chunk in document.chunks:
            if chunk.id:
                chunk_ids.add(chunk.id)
    for ref in extra:
        if ref.exhibit_id == exhibit_id and ref.chunk_id:
            chunk_ids.add(ref.chunk_id)
    return chunk_ids


def _sort_key(rec: RelationRecommendation) -> tuple[float, str, str, str]:
    return (-rec.confidence, rec.relation_type, rec.target_id, rec.source_id)
