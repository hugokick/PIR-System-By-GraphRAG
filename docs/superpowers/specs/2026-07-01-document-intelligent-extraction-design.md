# 上传资料字段抽取建议设计

## 1. 目标

本设计用于在项目内新增一个“上传资料字段抽取建议”模块，从文档全文或 chunk 中抽取展项建档建议值。

本阶段只交付独立模块，不接入上传 API，不改前端，不自动写入或覆盖任何现有展项字段。

典型输入包括：

- 文档基本信息：`document_id`、`file_name`、`file_type`、`source_note`
- 原始文本：`text`
- 或已切分文本块：`chunks`

典型输出包括以下建议字段：

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

所有输出都必须被明确标记为“建议值”，用于辅助人工确认，不具备自动落库语义。

## 2. 范围与边界

### 2.1 本次范围

- 新增 `backend/app/ai/__init__.py`
- 新增 `backend/app/ai/document_extraction.py`
- 新增 `backend/tests/test_document_extraction.py`
- 新增 `docs/document-extraction-contract.md`

### 2.2 明确不做

- 不修改 `upload_exhibit_asset`
- 不修改任何上传接口请求/响应结构
- 不修改 `ExhibitResponse`
- 不修改 `DocumentAsset`
- 不修改前端
- 不调用真实外部 LLM
- 不做自动写库
- 不做“建议值自动覆盖已有字段”

### 2.3 成功标准

- 新增模块可独立调用
- 新增测试通过
- 现有 `backend/tests` 不被破坏
- 契约文档清晰说明未来如何接入上传后的人工确认流程

## 3. 推荐方案

采用“单值建议 + 可追溯来源 + Provider 预留”的方案。

### 3.1 当前默认路径

默认使用规则/词典 fallback 完成字段抽取：

- 完全离线
- 可重复、可测试
- 不依赖真实 LLM
- 对外返回稳定结构

### 3.2 单值建议策略

每个字段只输出一个“当前最佳建议值”：

- `theme` 输出单个主题值，而非候选列表
- `supplier` 输出单个供应商名称
- `budget_min` / `budget_max` 输出单个区间

若原文出现多个候选值，内部可以进行竞争和排序，但对外只暴露最佳建议值。

### 3.3 未来扩展路径

预留 `DocumentExtractionProvider` 接口。

未来若接入真实 LLM，应遵循以下顺序：

1. 先由 provider 生成同结构建议结果
2. 若 provider 返回空结果、低置信结果或异常，则回退规则解析
3. 最终仍输出同一份稳定契约

## 4. 与现有项目的关系

### 4.1 当前已存在的文档链路

当前主线已经具备以下能力：

- `DocumentAsset` 可挂载 `source_note` 与 `chunks`
- `backend/app/services/documents.py` 能从文件中抽取文本并切分 chunk
- `upload_exhibit_asset` 在上传文档后会把 chunk 写入 `DocumentAsset.chunks`

这说明“上传后的文本与 chunk 已存在”，本模块不需要重复实现上传或切片。

### 4.2 本模块在架构中的位置

本模块放在 `backend/app/ai/` 下，定位为独立的“建议生成器”：

- 输入文档元信息与文本/chunks
- 输出结构化建议结果
- 不直接依赖 API 层
- 不直接依赖 repository 写操作

这能保证未来既可被上传链路调用，也可被离线批处理或后台审核任务调用。

## 5. 模块设计

### 5.1 文件职责

- `backend/app/ai/__init__.py`
  - 导出公共入口、数据模型与 provider 协议
- `backend/app/ai/document_extraction.py`
  - 定义输入输出模型、provider 接口、规则抽取器和字段来源定位逻辑
- `backend/tests/test_document_extraction.py`
  - 验证预算抽取、材料抽取、互动抽取、主题抽取、摘要生成、多 chunk 来源定位和空建议行为
- `docs/document-extraction-contract.md`
  - 说明输出契约、字段语义和未来接入人工确认流程的方式

### 5.2 入口函数

建议提供以下纯函数入口：

```python
def extract_document_suggestions(
    payload: DocumentExtractionInput,
    provider: DocumentExtractionProvider | None = None,
) -> DocumentExtractionResult:
    ...
```

该入口遵循：

- 保留原始文档信息
- 先统一文本输入
- 再执行字段级规则抽取
- 最终输出稳定的建议结果

## 6. 输入与输出契约

### 6.1 输入模型

建议定义 `DocumentExtractionInput`，字段包括：

- `document_id: str`
- `file_name: str`
- `file_type: str`
- `source_note: str | None`
- `text: str | None`
- `chunks: list[DocumentTextInput]`

其中 `DocumentTextInput` 建议至少包含：

- `chunk_id: str | None`
- `text: str`
- `sequence: int | None`
- `source_locator: str | None`

输入允许两种模式：

- 只有 `text`
- 只有 `chunks`

若同时存在，应优先使用 `chunks` 作为可追溯来源，并将 `text` 作为补充。

### 6.2 输出模型

建议定义 `DocumentExtractionResult`，字段如下：

- `document_id: str`
- `file_name: str`
- `file_type: str`
- `source_note: str | None`
- `exhibit_name: str | None`
- `category: str | None`
- `theme: str | None`
- `venue_type: str | None`
- `budget_min: int | None`
- `budget_max: int | None`
- `materials: list[str]`
- `interactions: list[str]`
- `supplier: str | None`
- `owner: str | None`
- `project_year: int | None`
- `tags: list[str]`
- `summary: str`
- `confidence: float`
- `field_sources: dict[str, list[SuggestedFieldSource]]`

### 6.3 来源模型

建议定义 `SuggestedFieldSource`，字段包括：

- `document_id: str`
- `field_name: str`
- `chunk_id: str | None`
- `source_locator: str | None`
- `snippet: str`
- `reason: str`

约束如下：

- `field_sources` 的 key 为建议字段名
- value 为支持该建议值的来源列表
- 即使字段只输出单个建议值，也可以保留多个支持来源
- 若字段没有建议值，则其 key 可缺省或对应空列表

## 7. 规则抽取策略

### 7.1 文本统一

进入规则匹配前先统一文本：

- 去除多余空白
- 统一全角/半角标点
- 保留中文原意
- 保留原始片段以便回填 `snippet`

### 7.2 字段抽取优先级

各字段建议遵循“强线索优先”的抽取顺序：

1. 带明显提示词的句子
2. 标题或首段高密度信息
3. 常规正文描述
4. `source_note`
5. 文件名

### 7.3 展项名称

`exhibit_name` 可从以下位置抽取：

- 文件名中的主标题
- 标题行或首句中的“展项名称 / 项目名称 / 方案名称”
- 带“乐园 / 沙盘 / 影院 / 装置 / 展项 / 展品”等展项后缀的短语

若同时出现多个候选，优先：

- 标题行
- 明确提示词后的值
- 与文档主题一致的名称

### 7.4 类别与主题

`category` 与 `theme` 使用业务词典匹配：

- `theme` 如 `力学`、`流体`、`水循环`、`天文`、`宇宙探索`
- `category` 可根据主题和关键词折叠，例如 `宇宙探索`、`基础科学`、`生态环保`

若主题命中但类别不明确，可由规则映射一个稳定类别；若映射不可靠，则只返回 `theme`。

### 7.5 场馆类型

`venue_type` 通过场馆词典和固定短语抽取，例如：

- `县级科技馆`
- `综合科技馆`
- `校园科技馆`
- `社区科普馆`

### 7.6 预算区间

`budget_min` / `budget_max` 使用正则识别下列表达：

- `20-30万`
- `20 万到 30 万`
- `80 万至 120 万`
- `预算约 50 万`
- `预算控制在 60 万以内`

规则如下：

- 明确区间则同时填 `budget_min` 与 `budget_max`
- 仅识别单值预算时，可将最小值与最大值都设为该值，或按文档约定仅填一侧，最终在契约中固定为同值
- 金额统一输出为整数元

### 7.7 材料与互动

`materials` 与 `interactions` 使用可扩展词典匹配：

- 材料示例：`钢结构`、`亚克力`、`木饰面`、`铝板`、`透明管道`
- 互动示例：`机械互动`、`按钮互动`、`触摸互动`、`沉浸影像`

结果去重并保留首次高质量来源。

### 7.8 供应商、业主与年份

- `supplier` 通过 `供应商`、`承建单位`、`实施单位` 等提示词抽取
- `owner` 通过 `业主`、`甲方`、`建设单位` 等提示词抽取
- `project_year` 抽取合理区间内的四位年份，例如 `2018-2035`

### 7.9 标签与摘要

`tags` 用于保留附加线索，例如：

- `低预算`
- `低维护`
- `适合低龄`
- `强互动`

`summary` 应生成 1 至 3 句短摘要，优先选择：

- 同时包含主题、互动或预算信息的句子
- 标题后的概述句
- 多 chunk 中信息密度最高的句子

若没有足够信息，则返回空字符串，而不是生成臆测摘要。

## 8. 多 chunk 来源定位

### 8.1 来源定位原则

`field_sources` 必须说明建议值来自哪一段文本：

- 有 chunk 时优先记录 `chunk_id`
- 能推断页码、段落或序号时，写入 `source_locator`
- `snippet` 保留短文本片段，便于人工审核

### 8.2 多来源合并

同一字段可由多个 chunk 支持：

- 对外仍只输出一个建议值
- 对内保留多个来源证据
- 预算区间、供应商、业主等字段优先保留带提示词的证据

### 8.3 无法定位时的降级

若只有全文 `text` 而没有 chunk：

- `chunk_id` 为空
- `source_locator` 可为空
- 仍需提供 `snippet`

## 9. 置信度与降级策略

### 9.1 置信度

`confidence` 在 0 到 1 之间，按以下信号综合计算：

- 命中的字段数量
- 是否命中强提示词
- 是否存在互相佐证的多 chunk 证据
- 是否抽取到预算、主题、互动等关键字段

### 9.2 空建议行为

当文档文本无法抽取任何稳定字段时：

- 返回空建议结构
- `summary` 为空字符串
- `materials`、`interactions`、`tags` 返回空列表
- `confidence` 为低值
- 不抛出异常

### 9.3 Provider 回退

若未来传入 provider：

- provider 成功且结果可信时可直接采用
- provider 结果为空、异常或低置信时回退规则解析
- 不允许 provider 改变输出结构

## 10. 测试策略

新增 `backend/tests/test_document_extraction.py`，至少覆盖以下场景：

- 从文本中抽取预算区间
- 抽取材料
- 抽取互动方式
- 抽取主题
- 生成摘要
- 多 chunk 来源定位
- 无法抽取时返回空建议而不是报错
- provider 回退到规则解析

同时运行现有 `backend/tests`，确保没有回归。

## 11. 未来接入方式

### 11.1 接入位置

未来建议在 `upload_exhibit_asset` 上传文档并生成 chunk 之后，再触发该模块。

接入顺序建议为：

1. 上传文档
2. 主线仍照常保存 `DocumentAsset` 与 `chunks`
3. 额外调用 `extract_document_suggestions(...)`
4. 将建议结果保存为待确认数据或临时审核结果
5. 由人工确认后再决定是否写入展项字段

### 11.2 人工确认流程

未来人工确认界面建议遵循：

- 左侧展示现有展项字段
- 右侧展示建议值
- 每个建议字段显示 `field_sources`
- 人工可执行“接受 / 忽略 / 手动编辑”

本阶段不实现该流程，只在契约文档中说明预期接入点。

## 12. 分阶段交付建议

最小交付顺序建议为：

1. `backend/app/ai/document_extraction.py`
2. `backend/tests/test_document_extraction.py`
3. `backend/app/ai/__init__.py`
4. `docs/document-extraction-contract.md`

这样主线可以先审规则抽取模块，再审文档说明。
