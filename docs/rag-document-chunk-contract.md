# RAG 文档切片契约

## 1. 目标

本文件定义“文档资料进入 RAG 的解析/切片契约”。

当前阶段只处理：

- 文档元数据
- 上游已经抽取好的纯文本内容
- 纯函数切片
- 可追溯引用结构

当前阶段明确不处理：

- 文件上传
- 原始文件解析
- OCR
- Excel 导入
- 向量库写入
- FastAPI 路由接入

## 2. 模块位置

纯文本文档切片契约位于：

- `backend/app/graphrag/document_chunks.py`

主线后续如需接入文档切片，应优先调用该模块暴露的纯函数，而不是把切片逻辑写进上传接口或路由层。

## 3. 输入模型

### 3.1 DocumentSource

表示文档来源元数据，包含：

- `exhibit_id`
- `document_id`
- `file_name`
- `file_type`
- `source_note`

### 3.2 DocumentTextBlock

表示上游已经抽取好的文本块，包含：

- `text`
- `page_number`
- `paragraph_index`
- `section_title`

这里的 `page_number` 和 `paragraph_index` 都是可选的。

如果上游无法提供页码，也可以只传纯文本和段落序号。

## 4. 输出模型

### 4.1 DocumentChunk

表示可检索的切片，固定包含：

- `chunk_id`
- `exhibit_id`
- `document_id`
- `file_name`
- `file_type`
- `text`
- `page_number_start`
- `page_number_end`
- `paragraph_index_start`
- `paragraph_index_end`
- `section_title`
- `source_locator`

每个 chunk 都必须能追溯到：

- 展项
- 文档
- 文件名
- 页码或段落位置

### 4.2 CitationSource

表示 RAG 返回时可直接使用的引用来源，包含：

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

### 4.3 DocumentChunkResult

表示单文档切片结果，包含：

- `source`
- `chunks`
- `citations`

## 5. 纯函数入口

### 5.1 单文档切片

- `chunk_document_source(source, blocks, max_chars=500, overlap_chars=50)`

用于将单个文档的文本块切为可检索 chunks。

### 5.2 多文档切片

- `chunk_document_sources(items, max_chars=500, overlap_chars=50)`

用于批量处理多个文档。

其中 `items` 为：

- `(DocumentSource, list[DocumentTextBlock])`

## 6. 当前切片规则

当前切片规则如下：

1. 输入以 `DocumentTextBlock` 为基本单位
2. 如果单个文本块长度不超过 `max_chars`，直接生成一个 chunk
3. 如果单个文本块超过 `max_chars`，按字符窗口切开
4. 切开时支持 `overlap_chars` 重叠
5. 每个 chunk 保留所属文档与位置信息
6. 每个 chunk 自动派生一个 `CitationSource`

当前规则是“纯文本契约版”，目的是稳定输入输出，不追求最优检索效果。

## 7. 主线如何调用

主线后续接入时，推荐流程如下：

1. 文档资产链路负责把原始文件解析成纯文本块
2. 主线将文档元数据组装为 `DocumentSource`
3. 主线将文本块组装为 `DocumentTextBlock`
4. 主线调用 `chunk_document_source()` 或 `chunk_document_sources()`
5. 后续再决定是否写入向量库或接入 RAG 检索流程

示例：

```python
from app.graphrag.document_chunks import (
    DocumentSource,
    DocumentTextBlock,
    chunk_document_source,
)

source = DocumentSource(
    exhibit_id="lever-play",
    document_id="lever-brief",
    file_name="杠杆乐园展项说明.pdf",
    file_type="pdf",
)

blocks = [
    DocumentTextBlock(
        text="第一页介绍杠杆乐园的设计目标和低龄儿童学习场景。",
        page_number=1,
        paragraph_index=1,
        section_title="项目概述",
    )
]

result = chunk_document_source(source, blocks)
```

## 8. 当前为什么不接上传接口

当前不接上传接口，原因如下：

- 主线文档资产链路正在推进，当前不应重复设计文件接收和解析入口
- 文档上传、OCR、PDF/Word 解析属于上游职责，不应与切片契约混在同一层
- 先稳定纯文本输入契约，有利于后续不同解析器复用同一切片层
- 可以避免并行开发阶段出现两套文档解析语义

## 9. 当前为什么不接向量库

当前不接向量库，原因如下：

- 切片层的职责是“把文本变成可检索 chunk”，而不是决定具体检索后端
- pgvector、Embedding 和索引策略应在主线文档资产链路稳定后再确定
- 先稳定 `DocumentChunk` 和 `CitationSource`，后续无论接哪种向量库都更容易适配

## 10. 后续接入 RAG 的建议映射

主线后续若接入 RAG，可按以下顺序映射：

1. 原始文件 -> 文本抽取结果
2. 文本抽取结果 -> `DocumentTextBlock`
3. `DocumentTextBlock` -> `DocumentChunk`
4. `DocumentChunk` -> embedding / 向量索引
5. 检索命中 chunk -> `CitationSource`
6. `CitationSource` 与展项图谱上下文合并，供 GraphRAG 或 RAG 回答链路使用

## 11. 当前边界

本阶段明确不做：

- 上传接口
- 文件解析器
- PDF/Word 解析实现
- OCR
- Excel 导入
- 向量化
- `/api/graphrag/*` 路由
- `main.py` 修改

## 12. 验收标准

本契约完成后，应满足：

- 能把纯文本块切成可检索 chunks
- 每个 chunk 可追溯到 `exhibit_id`、`document_id`、`file_name`
- 每个 chunk 能携带页码或段落位置
- 能稳定生成 `CitationSource`
- 返回结构不依赖 FastAPI、上传接口或向量库
