# 主线对接审查清单

## 1. 审查范围

当前 `hermes/graphrag-kg` 分支已形成 3 块可审查产物：

### 1.1 KG 构建与同步

- `backend/app/kg/__init__.py`
- `backend/app/kg/models.py`
- `backend/app/kg/extractors.py`
- `backend/app/kg/builder.py`
- `backend/app/kg/sync.py`

### 1.2 GraphRAG 查询契约

- `backend/app/graphrag/contract.py`
- `backend/app/graphrag/models.py`
- `backend/app/graphrag/search.py`
- `docs/kg-graphrag-contract.md`

### 1.3 文档切片与引用来源契约

- `backend/app/graphrag/document_chunks.py`
- `docs/rag-document-chunk-contract.md`

## 2. Cherry-pick 优先级

### 2.1 第一优先级：最小可接入子集

建议主线优先 cherry-pick 以下文件：

- `backend/app/graphrag/contract.py`
- `backend/app/kg/sync.py`
- `docs/kg-graphrag-contract.md`
- `backend/tests/test_kg_graphrag_contract.py`

原因：

- 这组文件最能直接支撑主线后续接入
- 不要求当前就接路由
- 不依赖文档上传链路或向量库
- 可先用来统一主线 GraphRAG 的服务层边界

### 2.2 第二优先级：KG 基础能力

如果主线需要真正运行 KG 快照构建，再补以下文件：

- `backend/app/kg/models.py`
- `backend/app/kg/extractors.py`
- `backend/app/kg/builder.py`
- `backend/app/kg/__init__.py`
- `backend/tests/test_kg_builder.py`
- `backend/tests/test_kg_sync.py`

原因：

- `contract.py` 最终依赖 KG 快照
- 如果主线只先审 GraphRAG 契约，可先不接全量 KG 文件
- 若要实际生成中心子图和邻域，则需要这组基础模块

### 2.3 第三优先级：文档切片契约

建议在主线 `documents / file upload / text extraction` 稳定后，再接以下文件：

- `backend/app/graphrag/document_chunks.py`
- `docs/rag-document-chunk-contract.md`
- `backend/tests/test_rag_document_chunk_contract.py`

原因：

- 当前切片层假设上游已经完成文本抽取
- 文档身份、文件存储和抽取结果格式应先由主线统一
- 过早接入容易与主线文档资产链路重复设计

### 2.4 暂缓直接合并

以下文件建议审查，但不一定要立即并入主线：

- `backend/app/graphrag/search.py`
- `backend/app/graphrag/models.py`
- `backend/tests/test_graphrag_search.py`

原因：

- 当前属于规则版、过渡版 GraphRAG 实现
- 主线如果已有自己的 `services/graphrag.py`，这部分更适合作为内部参考或被薄封装接入

## 3. 与主线现有 GraphRAG 的重叠点

如果主线已经存在 `backend/app/services/graphrag.py`，重叠点主要在以下方面：

- 查询职责重复：`contract.py` 与主线服务文件都可能承担“接收查询 -> 过滤 -> 检索 -> 拼装结果”职责
- 规则检索重叠：`search.py` 中的过滤、打分、邻域扩展可能与主线现有 GraphRAG 逻辑重复
- 返回结构重叠：主线现有 API 响应字段，可能与 `KGGraphRAGQueryResult` 不完全一致
- 引用结构重叠：主线若已有 citation 结构，可能需要与 `ContractCitation` 或 `CitationSource` 对齐

推荐处理方式：

- 保留主线现有 `backend/app/services/graphrag.py`
- 让主线服务文件逐步变成薄封装
- 内部优先委托 `backend/app/graphrag/contract.py`
- 不要长期维护两套并行 GraphRAG 核心逻辑

## 4. 文档切片接入路径

`document_chunks.py` 的职责应固定为：

- 接收文档元数据
- 接收已抽取好的纯文本块
- 生成可检索的 `DocumentChunk`
- 生成可追溯的 `CitationSource`

未来接入主线现有 `documents / file upload / RAG citation` 结构时，推荐映射如下：

### 4.1 documents

主线 `documents` 结构负责提供：

- `exhibit_id`
- `document_id`
- `file_name`
- `file_type`
- `source_note`

这些字段映射到：

- `DocumentSource`

### 4.2 file upload

主线文件上传与解析链路负责：

- 原始文件存储
- PDF/Word/TXT 文本抽取
- 页码、段落、章节等位置信息生成

这些抽取结果映射到：

- `DocumentTextBlock`

### 4.3 RAG citation

主线 RAG citation 层建议直接消费：

- `CitationSource`

如果主线已有自己的 citation 外层包装，可以保留主线包装，但尽量不要丢掉这些核心字段：

- `exhibit_id`
- `document_id`
- `file_name`
- `chunk_id`
- `page_number_start`
- `page_number_end`
- `paragraph_index_start`
- `paragraph_index_end`
- `snippet`
- `source_locator`

## 5. 最小接入建议

如果主线只想先接一个最小子集，推荐按以下顺序：

### 5.1 第一步

先接：

- `backend/app/graphrag/contract.py`
- `backend/app/kg/sync.py`
- `docs/kg-graphrag-contract.md`

这样可以先统一：

- GraphRAG 查询契约
- KG 同步入口语义
- 后续路由接入边界

### 5.2 第二步

再接：

- `backend/app/kg/models.py`
- `backend/app/kg/extractors.py`
- `backend/app/kg/builder.py`

这样主线就能实际构建 KG 快照并支撑中心子图查询。

### 5.3 第三步

等主线文档资产链路稳定后，再接：

- `backend/app/graphrag/document_chunks.py`
- `docs/rag-document-chunk-contract.md`

这样可以避免在上传、文档解析、Excel/import 尚未稳定时，把切片层提前耦合到不稳定接口上。

## 6. 当前不建议做的事

在主线文档资产链路、展项 CRUD、现有 GraphRAG API 未稳定前，当前不建议：

- 新增第二套路由语义
- 在主线中长期保留两套 GraphRAG 核心实现
- 把 `document_chunks.py` 直接耦合到上传接口
- 把文档切片层直接耦合到向量库写入
- 在当前阶段继续做结果质量增强

## 7. 推荐审查顺序

建议主线开发方按以下顺序审查：

1. `docs/kg-graphrag-contract.md`
2. `backend/app/graphrag/contract.py`
3. `backend/app/kg/sync.py`
4. `backend/app/kg/builder.py`
5. `docs/rag-document-chunk-contract.md`
6. `backend/app/graphrag/document_chunks.py`

这个顺序有利于先确认边界与契约，再确认实现细节。
