from app.graphrag.document_chunks import DocumentChunkResult
from app.services.documents import extract_document_chunk_result, extract_document_chunks


def test_extract_document_chunk_result_preserves_source_locator(tmp_path):
    document_path = tmp_path / "operation-note.txt"
    document_path.write_text(
        "pressure tunnel operation evidence " * 40,
        encoding="utf-8",
    )

    result = extract_document_chunk_result(
        exhibit_id="lever-play",
        document_id="document-demo",
        file_name="operation-note.txt",
        path=document_path,
        file_type="txt",
        source_note="operation note",
    )

    assert isinstance(result, DocumentChunkResult)
    assert result.source.exhibit_id == "lever-play"
    assert result.source.document_id == "document-demo"
    assert result.source.file_name == "operation-note.txt"
    assert result.chunks
    assert result.chunks[0].chunk_id == "document-demo:chunk-1"
    assert result.chunks[0].source_locator == "file=operation-note.txt, page=unknown, paragraph=1"
    assert result.citations[0].source_locator == result.chunks[0].source_locator


def test_extract_document_chunks_keeps_existing_api_shape(tmp_path):
    document_path = tmp_path / "operation-note.txt"
    document_path.write_text("pressure tunnel operation evidence", encoding="utf-8")

    chunks = extract_document_chunks("document-demo", document_path, "txt")

    assert chunks[0].id == "document-demo:chunk-1"
    assert chunks[0].sequence == 1
    assert chunks[0].text == "pressure tunnel operation evidence"
