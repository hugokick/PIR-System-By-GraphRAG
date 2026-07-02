# 上传资料字段抽取建议主线整合说明

## 适用范围

本文面向主线后端开发同事，目标是帮助主线以最小风险合入 `trae/document-extraction` 分支中的“上传资料字段抽取建议”模块。

本文只覆盖以下内容：

- 推荐 cherry-pick 顺序
- 可直接执行的 cherry-pick 命令
- 主线代码中的自然接入点
- `DocumentAsset` / `DocumentChunk` 到抽取模块输入的字段映射
- 回归验证清单
- 当前实现边界与风险提示

本文不覆盖以下内容：

- 前端审核界面
- 建议值持久化表结构
- 自动写回展项字段
- 真实 LLM provider 接入
- 上线部署流程

## 分支与 worktree

- 分支名：`trae/document-extraction`
- worktree 路径：`.worktrees/trae-document-extraction`
- 当前状态：本地与 `origin/trae/document-extraction` 对齐

## 相对 `main` 的变更文件清单

相对 `main` 的完整增量文件如下：

- `backend/app/ai/__init__.py`
- `backend/app/ai/document_extraction.py`
- `backend/tests/test_document_extraction.py`
- `docs/document-extraction-contract.md`
- `docs/document-extraction-mainline-integration.md`
- `docs/superpowers/plans/2026-07-01-document-intelligent-extraction.md`
- `docs/superpowers/specs/2026-07-01-document-intelligent-extraction-design.md`

如果主线只做运行与集成，核心文件可收敛为：

- `backend/app/ai/__init__.py`
- `backend/app/ai/document_extraction.py`
- `backend/tests/test_document_extraction.py`
- `docs/document-extraction-contract.md`

## 当前分支交付物

主线真正需要关注的文件只有以下几类：

- `backend/app/ai/__init__.py`
- `backend/app/ai/document_extraction.py`
- `backend/tests/test_document_extraction.py`
- `docs/document-extraction-contract.md`

其中：

- `backend/app/ai/document_extraction.py` 提供稳定纯函数入口 `extract_document_suggestions()`
- `backend/tests/test_document_extraction.py` 锁定规则 fallback、空建议、多 chunk 来源定位等可承诺行为
- `docs/document-extraction-contract.md` 说明输入输出契约和人工确认约束

## 已核验测试命令与结果

本次已重新执行以下定向测试：

```bash
python -m pytest backend/tests/test_document_extraction.py -q
```

实际结果：

- `5 passed in 0.09s`

测试覆盖的核心行为包括：

- 空文本返回空建议
- 预算区间与主题抽取
- 材料、互动、摘要与展项名称抽取
- 多 chunk 来源定位
- provider 返回空结果时回退规则解析

## 推荐 cherry-pick 顺序

建议主线按“先代码骨架，再核心能力，再增强能力，最后文档说明”的顺序挑选提交。

### 最小可用顺序

适合主线先拿到可调用模块和最稳定字段：

1. `3dbed6a` `test: add document extraction contract skeleton`
2. `d4e0e87` `feat: extract document budget and theme suggestions`

合入后可立即获得：

- 独立可调用的建议模块
- 空建议安全返回
- `theme` / `category` 建议
- `budget_min` / `budget_max` 建议

### 完整推荐顺序

适合主线一次性拿到当前分支的完整后端能力：

1. `3dbed6a` `test: add document extraction contract skeleton`
2. `d4e0e87` `feat: extract document budget and theme suggestions`
3. `2d618f2` `feat: add document extraction keywords and summary`
4. `a75fff1` `feat: add document extraction field sources and provider fallback`
5. `6ce857a` `docs: add document extraction contract`
6. `b3a76fb` `docs: add mainline cherry-pick order`

合入后可获得：

- 展项名称建议
- 材料建议
- 互动方式建议
- 摘要建议
- `supplier` / `owner` / `project_year` 建议
- `field_sources` 多 chunk 来源追溯
- `DocumentExtractionProvider` 预留扩展点

### 不建议拆开的提交

- `a75fff1` 不建议拆开
- 该提交同时收敛了 `field_sources`、组织字段抽取和 provider 回退逻辑，拆开后容易出现契约半成品

## 潜在冲突文件

### 当前 cherry-pick 阶段

最可能产生冲突的是：

- `backend/app/ai/__init__.py`

原因：

- 它与 `query_understanding`、`llm-rag-answerer` 等 AI 子模块共享同一导出入口
- 主线若已扩展 `app.ai`，最容易在导出列表或包注释上冲突

中风险文件：

- `docs/document-extraction-contract.md`

低风险文件：

- `backend/app/ai/document_extraction.py`
- `backend/tests/test_document_extraction.py`

### 后续真正接入上传后建议链路时

若主线准备把本模块接入上传完成后的审核流程，后续冲突热点会转移到：

- `backend/app/main.py`
- `backend/app/services/documents.py`
- `backend/app/schemas.py`

本分支当前没有直接改动这些文件来接入主线。

## 可直接执行的 cherry-pick 命令

### 方案 1：主线先接最小子集

```bash
git cherry-pick 3dbed6a d4e0e87
```

### 方案 2：主线一次性接完整能力

```bash
git cherry-pick 3dbed6a d4e0e87 2d618f2 a75fff1 6ce857a b3a76fb
```

### 方案 3：如果主线已手工实现部分规则，只补剩余增强

仅在主线已经自行接入骨架与预算/主题能力时使用：

```bash
git cherry-pick 2d618f2 a75fff1 6ce857a b3a76fb
```

执行建议：

1. 先在独立整合分支执行 cherry-pick，不要直接在主线保护分支操作
2. 若有冲突，优先保留主线已有上传链路，不要为了接本模块去改动上传 API 契约
3. 文档提交可放在代码提交之后解决

## 主线自然接入点

当前主线已有文档上传链路如下：

1. `upload_exhibit_asset`
2. `extract_document_chunks`
3. 生成 `DocumentAsset`
4. `repository.update_exhibit(...)`

对应现有文件：

- `backend/app/main.py`
- `backend/app/services/documents.py`
- `backend/app/schemas.py`

主线后续如果要真正挂接建议抽取，推荐只在 `upload_exhibit_asset` 的文档分支里追加一段“上传后建议生成”流程，而不要改变现有请求/响应结构。

推荐挂接时机：

1. 文件已经保存
2. `DocumentAsset` 已经构造完成
3. `chunks` 已经由 `extract_document_chunks()` 生成
4. 展项更新已经成功写入 repository
5. 再触发 `extract_document_suggestions()` 生成待确认建议

这样做的原因是：

- 不影响现有上传成功语义
- 不阻塞文档上传主流程
- 即使抽取失败，也不会影响 `DocumentAsset` 落库
- 后续更容易改造成异步任务或后台审核任务

## 字段映射方式

主线已有结构与新模块输入并不完全同名，需要做一次轻量映射。

### 主线已有字段

`DocumentAsset` 当前可提供：

- `id`
- `name`
- `file_type`
- `source_note`
- `chunks`

`DocumentChunk` 当前可提供：

- `id`
- `text`
- `sequence`

### 抽取模块所需字段

`DocumentExtractionInput` 需要：

- `document_id`
- `file_name`
- `file_type`
- `source_note`
- `text`
- `chunks`

`DocumentTextInput` 需要：

- `chunk_id`
- `text`
- `sequence`
- `source_locator`

### 推荐映射规则

- `document.id -> document_id`
- `document.name -> file_name`
- `document.file_type -> file_type`
- `document.source_note -> source_note`
- `document.chunks[].id -> chunk_id`
- `document.chunks[].text -> text`
- `document.chunks[].sequence -> sequence`
- `source_locator -> None`

注意：

- 当前主线 `DocumentChunk` 没有 `source_locator`
- 因此主线在不改 schema 的前提下，`field_sources` 仍可稳定返回 `chunk_id`，但页码级定位会为空
- 这不影响当前模块接入，只是证据粒度稍弱

## 推荐接入示例

以下示例只展示主线后端如何组装输入，不要求当前阶段立即改动 API。

```python
from app.ai import (
    DocumentExtractionInput,
    DocumentTextInput,
    extract_document_suggestions,
)


def build_document_extraction_input(document: DocumentAsset) -> DocumentExtractionInput:
    return DocumentExtractionInput(
        document_id=document.id,
        file_name=document.name,
        file_type=document.file_type,
        source_note=document.source_note,
        text=None,
        chunks=[
            DocumentTextInput(
                chunk_id=chunk.id,
                text=chunk.text,
                sequence=chunk.sequence,
                source_locator=None,
            )
            for chunk in document.chunks
        ],
    )


def generate_document_suggestions(document: DocumentAsset):
    payload = build_document_extraction_input(document)
    return extract_document_suggestions(payload)
```

如果主线暂时不想在上传接口里调用，也可以先用于：

- 后台管理命令
- 离线修复脚本
- 审核任务 worker
- 管理端人工复核接口

## 建议的主线接入步骤

若主线准备正式挂接，可按下面顺序推进：

1. 先完成 cherry-pick 并保证 `backend/tests/test_document_extraction.py` 全绿
2. 在主线新增一个内部组装函数，把 `DocumentAsset` 映射为 `DocumentExtractionInput`
3. 先在非 API 主路径调用，例如后台任务、审核命令或 admin-only 逻辑
4. 将结果保存为“待确认建议”，不要直接更新展项字段
5. 等后台审核流程稳定后，再考虑在上传后自动触发

推荐原因：

- 先验证抽取质量，再讨论数据落库位置
- 先保持人工确认，再决定是否自动化
- 先把建议链路跑通，再接真实 provider

## 回归验证清单

主线合入后，建议至少执行以下验证：

### 定向测试

```bash
python -m pytest backend/tests/test_document_extraction.py -q
```

预期：

- 预算区间抽取通过
- 主题与类别抽取通过
- 材料与互动建议通过
- 摘要生成通过
- 多 chunk 来源定位通过
- provider 空结果回退通过

### 后端回归

```bash
python -m pytest backend/tests -q
```

预期：

- 现有上传、展项、GraphRAG 等测试不出现回归

### 手工 smoke check

建议额外用一个现有 `DocumentAsset` 样本做一次本地调用，重点确认：

- `document_id`、`file_name`、`file_type` 原样保留
- `field_sources` 至少带出 `chunk_id`
- 空文本或弱文本不会抛异常
- 抽取失败只返回空建议，不影响上传主链路

## 风险与注意事项

### 1. 当前结果是建议值，不是事实值

- 不要把 `DocumentExtractionResult` 直接映射回 `ExhibitResponse`
- 不要在没有人工确认的前提下覆盖展项现有字段

### 2. 当前主线没有建议值持久化结构

- 本分支没有引入新的 repository schema
- 主线如果要保存建议值，需要后续自行决定存储位置

### 3. `source_locator` 目前可能为空

- 因为主线 `DocumentChunk` 只保留 `id`、`text`、`sequence`
- 若未来需要页码级证据，可在不破坏现有契约的前提下另做增强

### 4. `venue_type` 与 `tags` 已保留字段，但当前规则覆盖较少

- 主线接入时不要把这两个字段视为稳定高召回能力
- 目前更稳定的是预算、主题、材料、互动、组织字段和摘要

### 5. provider 只是扩展点

- 当前分支默认仍是规则/词典 fallback
- 合入主线时不需要任何外部模型配置

## 后续推荐动作

如果主线希望继续往“可审核、可落库”推进，推荐下一阶段只做以下一项：

1. 新增“待确认建议”存储结构
2. 增加 admin 审核接口或后台审核任务
3. 前端再接“接受 / 忽略 / 编辑”界面

建议不要把这三件事和本次 cherry-pick 绑在同一个提交里，以免扩大整合风险。
