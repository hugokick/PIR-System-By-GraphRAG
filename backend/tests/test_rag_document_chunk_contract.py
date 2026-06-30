from app.graphrag.document_chunks import (
    CitationSource,
    DocumentSource,
    DocumentTextBlock,
    chunk_document_source,
    chunk_document_sources,
)


def test_chunk_document_source_preserves_traceability_fields():
    source = DocumentSource(
        exhibit_id="lever-play",
        document_id="lever-brief",
        file_name="杠杆乐园展项说明.pdf",
        file_type="pdf",
        source_note="样例文档",
    )
    blocks = [
        DocumentTextBlock(
            text="第一页介绍杠杆乐园的设计目标和低龄儿童学习场景。",
            page_number=1,
            paragraph_index=1,
            section_title="项目概述",
        ),
        DocumentTextBlock(
            text="第二页介绍展项的材料、机构和亲子互动方式。",
            page_number=2,
            paragraph_index=1,
            section_title="设计说明",
        ),
    ]

    result = chunk_document_source(source, blocks, max_chars=40, overlap_chars=0)

    assert result.source.exhibit_id == "lever-play"
    assert result.chunks
    first = result.chunks[0]
    assert first.exhibit_id == "lever-play"
    assert first.document_id == "lever-brief"
    assert first.file_name == "杠杆乐园展项说明.pdf"
    assert first.page_number_start is not None
    assert first.paragraph_index_start is not None


def test_chunk_document_source_splits_long_blocks_and_produces_citations():
    source = DocumentSource(
        exhibit_id="water-cycle",
        document_id="water-brief",
        file_name="城市水循环沙盘说明.docx",
        file_type="docx",
    )
    blocks = [
        DocumentTextBlock(
            text="城市水循环沙盘通过实体模型、灯光和投影叠加展示降雨、汇流、净化和再利用过程。"
            "观众可以通过按钮切换不同情境，观察城区排水与净水设施协同运作。",
            page_number=3,
            paragraph_index=2,
        )
    ]

    result = chunk_document_source(source, blocks, max_chars=35, overlap_chars=8)

    assert len(result.chunks) >= 2
    assert result.citations
    assert all(isinstance(item, CitationSource) for item in result.citations)
    assert all(chunk.text for chunk in result.chunks)


def test_chunk_document_sources_handles_multiple_documents_without_fastapi():
    first = DocumentSource(
        exhibit_id="lever-play",
        document_id="lever-brief",
        file_name="杠杆乐园展项说明.pdf",
        file_type="pdf",
    )
    second = DocumentSource(
        exhibit_id="pulley-wall",
        document_id="pulley-brief",
        file_name="滑轮挑战墙资料.txt",
        file_type="txt",
    )
    items = [
        (
            first,
            [DocumentTextBlock(text="杠杆原理说明。", page_number=1, paragraph_index=1)],
        ),
        (
            second,
            [DocumentTextBlock(text="滑轮组竞赛互动说明。", page_number=2, paragraph_index=3)],
        ),
    ]

    results = chunk_document_sources(items, max_chars=50, overlap_chars=0)

    assert len(results) == 2
    assert all(result.chunks for result in results)
    assert not hasattr(results[0], "status_code")
