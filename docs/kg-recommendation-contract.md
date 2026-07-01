# KG 关系推荐契约

> 状态：由 `trae/kg-recommendations` 工作树引入。模块仅做"建议/镜像"，
> 不写入图谱；接入人工确认后再写入关系是未来独立任务。

## 1. 目标

在已有展项档案、可选 KG 快照、可选文档片段的输入下，输出潜在的可写入
图谱关系候选。模块严格只读：**不**修改 ``kg_nodes``/``kg_edges``，不调用
``kg/sync.py``，不做 Neo4j 双写。

## 2. 模块位置

- ``backend/app/kg/recommendations.py`` — 数据契约 + 公共入口 + 权重常量
- ``backend/tests/test_kg_recommendations.py`` — 25 个单元测试
- ``docs/kg-recommendation-contract.md`` — 本文档

## 3. 公共入口

```python
from app.kg.recommendations import (
    RecommendationInputs,
    RecommendationResult,
    RelationRecommendation,
    DocumentChunkRef,
    recommend_relations,
)

result: RecommendationResult = recommend_relations(
    RecommendationInputs(
        target_exhibit=target,
        all_exhibits=repository.list_exhibits(),
        snapshot=kg_snapshot,           # 可选
        document_chunks=extra_chunks,   # 可选
    )
)
```

## 4. 输入契约

### ``RecommendationInputs``

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| ``target_exhibit`` | ``ExhibitResponse \| None`` | 推荐中心。``None`` 时安全返回空结果 + warning。 |
| ``all_exhibits`` | ``list[ExhibitResponse]`` | 候选展项池；``target_exhibit`` 在其中会被自动跳过自引用。 |
| ``snapshot`` | ``KGSnapshot \| None`` | 当前内存快照；缺省时调用 ``build_exhibit_kg_snapshot`` 构造一次性只读快照。 |
| ``document_chunks`` | ``list[DocumentChunkRef]`` | 外部文档片段引用，独立于 ``ExhibitResponse.documents``。 |

### ``DocumentChunkRef``

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| ``exhibit_id`` | ``str`` | 关联展项 ID。 |
| ``document_id`` | ``str`` | 关联文档 ID。 |
| ``chunk_id`` | ``str`` | 片段 ID（用于 evidence_refs 去重）。 |
| ``text`` | ``str`` | 片段文本，仅用于将来可选语义匹配。 |

## 5. 输出契约

### ``RecommendationResult``

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| ``target_exhibit_id`` | ``str \| None`` | 实际处理的目标展项 ID；安全场景下为 ``None``。 |
| ``warnings`` | ``list[str]`` | 含 ``missing target_exhibit`` 与 ``snapshot.warnings`` 透传。 |
| ``recommendations`` | ``list[RelationRecommendation]`` | 排序后的推荐记录。 |

### ``RelationRecommendation``

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| ``relation_type`` | 7 种受控枚举 | ``similar_to`` / ``has_theme`` / ``uses_material`` / ``has_interaction`` / ``supplied_by`` / ``owned_by`` / ``belongs_to_project`` |
| ``source_id`` | ``str`` | 始终等于 ``target_exhibit.id``（裸展项 ID）。 |
| ``target_id`` | ``str`` | 目标裸 ID（展项 / theme / material / interaction / supplier / owner / project 的原始 ID）。 |
| ``target_label`` | ``str`` | 目标展示名，取自 snapshot 节点 label。 |
| ``confidence`` | ``float`` | 0-1；typed 关系恒为 1.0；``similar_to`` 见第 6 节。 |
| ``reasons`` | ``list[str]`` | 中文可读解释，例如 "共同主题：力学"、"已存在的图谱边：uses_material"。 |
| ``evidence_refs`` | ``list[str]`` | 完整 KG 节点 ID（如 ``theme:mechanics``、``material:metal``）或 chunk ID；用于交叉校验。 |
| ``already_exists`` | ``bool`` | 是否已在 snapshot 中存在。 |

## 6. ``similar_to`` 推理权重

| 信号 | 权重 |
| --- | --- |
| 主题相同 | +0.4 |
| 每个共同材料 | +0.15 |
| 每个共同互动方式 | +0.15 |
| 每个共同标签 | +0.05 |
| 每个共享文档片段 | +0.10 |

得分被 ``min(score / 1.0, 1.0)`` 截断，保留 3 位小数。

``already_exists`` 检测 ``similar_to`` 边时同时检查 ``(target -> other)`` 和
``(other -> target)`` 两种方向，避免手动维护的同向无关边绕过提示。

## 7. typed 关系镜像策略

对 ``has_theme``、``uses_material``、``has_interaction``、``supplied_by``、
``owned_by``、``belongs_to_project`` 这 6 种类型：

- **不主动推断**：模块不会基于"相似展项都有 X"再给目标补一条 ``has_X`` 边，
  避免重复或与 ``kg/builder`` 之外的事实写入路径冲突。
- **镜像已有边**：从 snapshot 中读取 ``source = exhibit:target.id`` 的全部
  上述类型边，转写为 ``RelationRecommendation``，``confidence=1.0``、
  ``already_exists=True``。
- **去重**：同一 ``(relation_type, target_id)`` 仅输出一条。
- **目标边缺失的场景**：当前由 ``kg/builder`` 保证 6 种类型都会写出；
  若调用方传入的目标在 snapshot 中没有相关边，结果列表里也不会出现，
  视为"无相关推荐"。

## 8. 排序与稳定性

排序键固定为 ``(-confidence, relation_type, target_id, source_id)``：

- 同 confidence 时按 relation_type 字典序破缺；
- 再按 target_id 字典序破缺；
- 再按 source_id（恒为目标展项 ID，作为最终稳定手段）。

输入顺序不会影响输出顺序。

## 9. 安全与不变性

- ``recommend_relations`` 是**纯函数**：不修改输入 ``RecommendationInputs``、
  ``snapshot``、``target_exhibit``、``all_exhibits``。
- 当 ``target_exhibit is None`` 时，返回
  ``RecommendationResult(target_exhibit_id=None, warnings=[missing_target_exhibit], recommendations=[])``；
  不会抛错。
- 当没有传入 ``snapshot`` 时，模块会调用 ``build_exhibit_kg_snapshot`` 构造
  一次内存中快照；该调用同样是纯函数（builder 自行测试保证）。
- 当 ``target.id`` 与 ``all_exhibits`` 中某项相等时，**自动跳过**，不会输出
  自引用 ``similar_to``。

## 10. 与现有 KG 模块的关系

| 模块 | 角色 | 本模块是否调用 |
| --- | --- | --- |
| ``kg.builder.build_exhibit_kg_snapshot`` | 一次性快照构建 | 是（仅 snapshot 缺省时调用，纯函数） |
| ``kg.sync.sync_snapshot_after_upsert`` | 写入后重建 snapshot | 否 |
| ``kg.sync.sync_snapshot_after_delete`` | 删除后重建 snapshot | 否 |
| ``kg_nodes`` / ``kg_edges`` 投影表 | 持久化 | **否** |
| Neo4j Demo Graph | 旁路演示 | **否** |
| ``services.graphrag`` | GraphRAG 检索 | 否 |

## 11. 未来接入人工确认后写入关系

**写入路径必须在人工逐条确认后单独设计**。本模块的设计目标是让上层流程
可以按以下步骤使用：

1. 服务端在用户编辑某个展项时，调用
   ``recommend_relations(RecommendationInputs(target_exhibit=...))``。
2. 前端展示：仅 ``similar_to`` 且 ``already_exists=False`` 的条目作为"建议"。
   ``already_exists=True`` 的 typed 关系用于"已有关系解释"，不展示为建议。
3. 用户勾选若干条后，前端发送 ``POST /api/exhibits/{id}/related-exhibits``
   提交；现有主线接口在收到 ``related_exhibit_ids`` 时会校验展项存在性与自引用，
   并经由 ``kg/sync`` 重建 snapshot，从而把 recommended 关系落到 ``kg_nodes``
   / ``kg_edges`` 投影。
4. 写库仍走主线，不直接调用 KG 模块，避免两套写入路径分叉。

下列写入辅助函数本模块**不提供**：

- 不提供 ``apply_recommendation`` / ``commit_recommendation``。
- 不在内部修改 ``ExhibitResponse.related_exhibit_ids`` 或 snapshot。

## 12. 测试覆盖

``backend/tests/test_kg_recommendations.py`` 25 项测试覆盖：

- 共同主题 / 材料 / 互动 / 标签 / 文档片段 五种信号下产生 ``similar_to``；
- 自引用跳过；
- 零重叠无 ``similar_to``；
- snapshot 中已存在的 ``similar_to`` 双向均标 ``already_exists=True``；
- 六种 typed 关系均以 ``already_exists=True`` 出现，且具备完整 KG 节点前缀；
- snapshot 中重复 typed 边会被去重；
- 安全语义：target 缺失返回空结果 + warning；snapshot.warnings 透传；输入不被修改；
- 排序稳定性：confidence 降序 + 平局键排序；多次运行结果一致；
- 饱和：叠加大量信号时 confidence 上限 1.0；
- 输出模型可序列化。

测试命令：

```bash
cd backend && python -m pytest tests/test_kg_recommendations.py -v
```

## 13. 验收标准

- 所有 25 项新测试通过。
- 现有 ``backend/tests`` 在本模块新增代码下不被破坏（已验证 162 + 25 = 187
  全绿）。
- ``kg/builder.py``、``kg/sync.py``、``kg_nodes``/``kg_edges`` 写入路径零改动。
- 模块默认零外部依赖，可离线运行。
