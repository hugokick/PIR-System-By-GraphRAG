from app.graphrag.document_chunks import DocumentChunkResult
from app.services.documents import extract_document_chunk_result, extract_document_chunks, extract_document_text


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


def test_extract_legacy_office_text_from_utf16_payload(tmp_path):
    legacy_path = tmp_path / "legacy-scheme.doc"
    legacy_text = "旧版 Word 方案包含低龄儿童力学互动证据 legacy-office-token"
    legacy_path.write_bytes(b"\xd0\xcf\x11\xe0" + legacy_text.encode("utf-16le") + b"\x00\x01")

    extracted = extract_document_text(legacy_path, "doc")

    assert "legacy-office-token" in extracted
    assert "低龄儿童力学互动证据" in extracted


def test_extract_legacy_spreadsheet_and_presentation_text(tmp_path):
    xls_path = tmp_path / "quote.xls"
    ppt_path = tmp_path / "deck.ppt"
    xls_path.write_bytes("旧版 Excel 报价 token-xls-legacy".encode("gb18030"))
    ppt_path.write_bytes("旧版 PPT 汇报 token-ppt-legacy".encode("utf-16le"))

    assert "token-xls-legacy" in extract_document_text(xls_path, "xls")
    assert "token-ppt-legacy" in extract_document_text(ppt_path, "ppt")
