# 上传资料字段抽取建议契约

## 目标

`extract_document_suggestions()` 从文档文本或 chunk 中生成展项建档建议值。

本模块只输出“建议值”，不自动写入展项数据，也不覆盖现有展项字段。

## 输入

- `document_id`
- `file_name`
- `file_type`
- `source_note`
- `text`
- `chunks`

其中 `chunks` 可提供更细粒度的来源定位信息，例如：

- `chunk_id`
- `sequence`
- `source_locator`
- `text`

## 输出

- `document_id`
- `file_name`
- `file_type`
- `source_note`
- `exhibit_name`
- `category`
- `theme`
- `venue_type`
- `budget_min`
- `budget_max`
- `materials`
- `interactions`
- `supplier`
- `owner`
- `project_year`
- `tags`
- `summary`
- `confidence`
- `field_sources`

## field_sources

`field_sources` 的 key 是建议字段名，value 是该字段的来源列表。

每个来源项必须包含：

- `document_id`
- `field_name`
- `chunk_id`
- `source_locator`
- `snippet`
- `reason`

用途如下：

- 给人工审核者说明“为什么推荐这个值”
- 在多 chunk 场景下定位具体来源片段
- 支持“接受 / 忽略 / 手动编辑”前的证据查看

## 规则 fallback

当前默认使用规则/词典 fallback，不依赖真实外部 LLM。

当前已覆盖：

- 预算区间
- 主题与类别
- 材料
- 互动方式
- 展项名称
- 供应商
- 业主
- 项目年份
- 摘要

## Provider 扩展点

模块预留 `DocumentExtractionProvider`。

未来如果接入真实 LLM，应保持以下行为：

1. provider 输出与当前结果结构一致
2. provider 返回空结果、异常或低置信时回退规则解析
3. 无论使用哪条路径，最终都返回同一份稳定契约

## 未来接入 upload_exhibit_asset 的建议

推荐接入顺序：

1. `upload_exhibit_asset` 正常保存 `DocumentAsset` 与 `chunks`
2. 上传完成后调用 `extract_document_suggestions()`
3. 生成的结果保存为待确认建议，而不是直接更新展项字段
4. 在人工确认界面展示“现有值 vs 建议值 vs 来源片段”
5. 仅在人工确认后执行展项字段更新

## 本阶段明确不做

- 不修改上传 API
- 不修改 `ExhibitResponse`
- 不修改 `DocumentAsset`
- 不修改前端
- 不做自动写库
- 不做建议值自动覆盖
