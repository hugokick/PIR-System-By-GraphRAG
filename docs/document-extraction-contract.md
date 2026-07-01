# 上传资料字段抽取建议契约

## 配套文档

如果需要主线后端整合步骤、提交顺序和字段映射示例，请同时阅读 `docs/document-extraction-mainline-integration.md`。

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

## 主线 cherry-pick 顺序建议

建议主线按“先稳定契约骨架，再逐步增强抽取能力，最后接文档说明”的顺序挑选提交。

### 最小可用顺序

1. `3dbed6a` `test: add document extraction contract skeleton`
   - 引入 `backend/app/ai/__init__.py`
   - 引入 `backend/app/ai/document_extraction.py`
   - 引入 `backend/tests/test_document_extraction.py`
   - 作用：先把独立模块骨架、输入输出模型和空建议行为放进主线
2. `d4e0e87` `feat: extract document budget and theme suggestions`
   - 增加预算区间、主题、类别和基础 `field_sources`
   - 作用：先让主线拥有最核心、最稳定的建议能力
3. `2d618f2` `feat: add document extraction keywords and summary`
   - 增加展项名称、材料、互动方式和摘要建议
   - 作用：补齐上传资料人工审核时最常用的建议字段
4. `a75fff1` `feat: add document extraction field sources and provider fallback`
   - 增加多 chunk 来源定位
   - 增加供应商、业主、项目年份抽取
   - 增加 `DocumentExtractionProvider` 回退机制
   - 作用：把模块从“可用”提升到“可接 LLM / 可定位来源”的完整状态
5. `6ce857a` `docs: add document extraction contract`
   - 补充主线接入说明、`field_sources` 结构和人工确认流程建议
   - 作用：供主线对接和评审时参考

### 如果主线只想先接最小子集

推荐只先挑这两步：

1. `3dbed6a`
2. `d4e0e87`

这样主线可以先获得：

- 独立可调用的建议模块
- 空建议安全返回
- 预算区间建议
- 主题 / 类别建议

这套最小子集风险最低，也最适合先接到上传后异步分析或后台审核流程里。

### 不建议拆开的点

- `a75fff1` 最好整体引入，不建议只挑其中一部分
  - 因为该提交把 `field_sources` 的 chunk 级定位、组织字段抽取和 provider 回退一起收敛到了同一版结构
- `6ce857a` 虽然只是文档，但建议跟最终功能一起接
  - 否则主线同事拿不到完整的接入说明和人工确认流程约束

### 主线接入后的推荐动作

主线完成上述 cherry-pick 后，建议按下面顺序继续：

1. 在 `upload_exhibit_asset` 保存 `DocumentAsset` 与 `chunks` 后调用 `extract_document_suggestions()`
2. 先把结果存为“待确认建议”，不要直接改写展项字段
3. 在后台审核或管理界面增加“接受 / 忽略 / 编辑”流程
4. 等 provider 接口确定后，再接真实 LLM extraction provider
5. 保持当前规则 fallback 作为稳定保底链路

## 本阶段明确不做

- 不修改上传 API
- 不修改 `ExhibitResponse`
- 不修改 `DocumentAsset`
- 不修改前端
- 不做自动写库
- 不做建议值自动覆盖
