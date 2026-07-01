from app.graphrag.document_chunks import (
    DocumentSource,
    DocumentTextBlock,
    chunk_document_source,
)


def test_chunk_document_source_returns_chunks_and_citation_sources():
    source = DocumentSource(
        exhibit_id="lever-play",
        document_id="document-demo",
        file_name="lever-guide.pdf",
        file_type="pdf",
        source_note="说明资料",
    )
    blocks = [
        DocumentTextBlock(
            text="低龄儿童可以通过杠杆装置观察力矩变化，并记录不同支点位置下的互动结果。",
            page_number=3,
            paragraph_index=2,
            section_title="互动说明",
        )
    ]

    result = chunk_document_source(source, blocks, max_chars=18, overlap_chars=4)

    assert result.source == source
    assert len(result.chunks) > 1
    assert result.chunks[0].chunk_id == "document-demo:chunk-1"
    assert result.chunks[0].source_locator == "file=lever-guide.pdf, page=3, paragraph=2"
    assert result.chunks[0].section_title == "互动说明"
    assert result.chunks[1].text.startswith(result.chunks[0].text[-4:])
    assert result.citations[0].chunk_id == result.chunks[0].chunk_id
    assert result.citations[0].source_locator == result.chunks[0].source_locator
