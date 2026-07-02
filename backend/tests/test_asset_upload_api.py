from fastapi.testclient import TestClient
import pytest
from zipfile import ZIP_DEFLATED, ZipFile
from io import BytesIO

from app.main import app, repository


client = TestClient(app)

ADMIN_HEADERS = {"X-User-Role": "admin"}
EDITOR_HEADERS = {"X-User-Role": "editor"}


@pytest.fixture(autouse=True)
def restore_seed_exhibits_after_asset_test():
    originals = {
        exhibit_id: (exhibit.model_copy(deep=True) if exhibit else None)
        for exhibit_id in ("lever-play", "pulley-wall")
        if (exhibit := repository.get_exhibit(exhibit_id)) is not None
    }
    yield
    for exhibit in originals.values():
        if exhibit is not None:
            repository.update_exhibit(exhibit.id, exhibit)


def minimal_pdf_bytes(text: str) -> bytes:
    escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    objects = [
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n",
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n",
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 144] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>\nendobj\n",
        b"4 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n",
    ]
    stream = f"BT /F1 12 Tf 24 100 Td ({escaped}) Tj ET".encode()
    objects.append(
        b"5 0 obj\n<< /Length "
        + str(len(stream)).encode()
        + b" >>\nstream\n"
        + stream
        + b"\nendstream\nendobj\n"
    )

    pdf = b"%PDF-1.4\n"
    offsets = [0]
    for item in objects:
        offsets.append(len(pdf))
        pdf += item
    xref_offset = len(pdf)
    xref_rows = [b"0000000000 65535 f \n"]
    xref_rows.extend(f"{offset:010d} 00000 n \n".encode() for offset in offsets[1:])
    pdf += b"xref\n0 6\n" + b"".join(xref_rows)
    pdf += b"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n"
    pdf += str(xref_offset).encode() + b"\n%%EOF\n"
    return pdf


def minimal_xlsx_bytes(rows: list[list[str]]) -> bytes:
    sheet_rows = []
    for row_index, row in enumerate(rows, start=1):
        cells = []
        for column_index, value in enumerate(row, start=1):
            column = chr(ord("A") + column_index - 1)
            escaped = (
                value.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;")
            )
            cells.append(f'<c r="{column}{row_index}" t="inlineStr"><is><t>{escaped}</t></is></c>')
        sheet_rows.append(f'<row r="{row_index}">{"".join(cells)}</row>')

    workbook = BytesIO()
    with ZipFile(workbook, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr(
            "[Content_Types].xml",
            """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
</Types>""",
        )
        archive.writestr(
            "_rels/.rels",
            """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>""",
        )
        archive.writestr(
            "xl/workbook.xml",
            """<?xml version="1.0" encoding="UTF-8"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
          xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets>
    <sheet name="Sheet1" sheetId="1" r:id="rId1"/>
  </sheets>
</workbook>""",
        )
        archive.writestr(
            "xl/_rels/workbook.xml.rels",
            """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
</Relationships>""",
        )
        archive.writestr(
            "xl/worksheets/sheet1.xml",
            f"""<?xml version="1.0" encoding="UTF-8"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <sheetData>{"".join(sheet_rows)}</sheetData>
</worksheet>""",
        )
    return workbook.getvalue()


def minimal_docx_bytes(paragraphs: list[str]) -> bytes:
    body = "".join(
        "<w:p><w:r><w:t>"
        + text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        + "</w:t></w:r></w:p>"
        for text in paragraphs
    )
    document_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>{body}</w:body>
</w:document>"""

    document = BytesIO()
    with ZipFile(document, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr(
            "[Content_Types].xml",
            """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>""",
        )
        archive.writestr(
            "_rels/.rels",
            """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>""",
        )
        archive.writestr("word/document.xml", document_xml)
    return document.getvalue()


def minimal_pptx_bytes(texts: list[str]) -> bytes:
    text_runs = "".join(
        "<a:p><a:r><a:t>"
        + text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        + "</a:t></a:r></a:p>"
        for text in texts
    )
    slide_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"
       xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
  <p:cSld>
    <p:spTree>
      <p:sp><p:txBody>{text_runs}</p:txBody></p:sp>
    </p:spTree>
  </p:cSld>
</p:sld>"""

    presentation = BytesIO()
    with ZipFile(presentation, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr(
            "[Content_Types].xml",
            """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>
  <Override PartName="/ppt/slides/slide1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>
</Types>""",
        )
        archive.writestr(
            "_rels/.rels",
            """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/>
</Relationships>""",
        )
        archive.writestr("ppt/presentation.xml", "<presentation />")
        archive.writestr("ppt/slides/slide1.xml", slide_xml)
    return presentation.getvalue()


def test_upload_image_asset_attaches_media_and_serves_file(monkeypatch, tmp_path):
    monkeypatch.setenv("FILE_STORAGE_ROOT", str(tmp_path))

    response = client.post(
        "/api/exhibits/lever-play/assets",
        data={"asset_kind": "media", "note": "现场照片"},
        files={"file": ("scene.png", b"fake image bytes", "image/png")},
        headers=EDITOR_HEADERS,
    )

    assert response.status_code == 201
    payload = response.json()
    media = payload["media_assets"][-1]
    assert media["name"] == "scene.png"
    assert media["type"] == "image"
    assert media["note"] == "现场照片"
    assert media["url"].startswith("/api/files/")

    file_response = client.get(media["url"])
    assert file_response.status_code == 200
    assert file_response.content == b"fake image bytes"

    download_response = client.get(f"{media['url']}?download=1")
    assert download_response.status_code == 200
    assert download_response.headers["content-disposition"].startswith("attachment;")
    assert "scene.png" in download_response.headers["content-disposition"]


def test_upload_document_asset_attaches_document_source(monkeypatch, tmp_path):
    monkeypatch.setenv("FILE_STORAGE_ROOT", str(tmp_path))

    response = client.post(
        "/api/exhibits/lever-play/assets",
        data={"asset_kind": "document", "note": "报价资料"},
        files={"file": ("quote.pdf", b"%PDF fake", "application/pdf")},
        headers=EDITOR_HEADERS,
    )

    assert response.status_code == 201
    payload = response.json()
    document = payload["documents"][-1]
    assert document["name"] == "quote.pdf"
    assert document["file_type"] == "pdf"
    assert document["source_note"] == "报价资料"
    assert document["url"].startswith("/api/files/")

    preview_response = client.get(document["url"])
    assert preview_response.status_code == 200
    assert preview_response.headers["content-disposition"].startswith("inline;")

    download_response = client.get(f"{document['url']}?download=1")
    assert download_response.status_code == 200
    assert download_response.headers["content-disposition"].startswith("attachment;")
    assert "quote.pdf" in download_response.headers["content-disposition"]


def test_editor_upload_to_approved_exhibit_moves_it_back_to_pending_review(monkeypatch, tmp_path):
    monkeypatch.setenv("FILE_STORAGE_ROOT", str(tmp_path))
    exhibit_id = "upload-review-reset-demo"
    payload = client.get("/api/exhibits/pulley-wall").json()
    payload["id"] = exhibit_id
    payload["name"] = "资料上传回审示例"
    payload["status"] = "制作中"
    payload["review_status"] = "已审核"
    create_response = client.post("/api/exhibits", json=payload, headers=ADMIN_HEADERS)
    assert create_response.status_code == 201
    assert create_response.json()["review_status"] == "已审核"

    try:
        upload_response = client.post(
            f"/api/exhibits/{exhibit_id}/assets",
            data={"asset_kind": "document", "note": "编辑补充资料"},
            files={"file": ("review-reset-note.txt", b"review reset evidence", "text/plain")},
            headers=EDITOR_HEADERS,
        )

        assert upload_response.status_code == 201
        assert upload_response.json()["review_status"] == "待审核"
        detail_response = client.get(f"/api/exhibits/{exhibit_id}")
        assert detail_response.json()["review_status"] == "待审核"

        audit_response = client.get("/api/admin/audit-logs", headers=ADMIN_HEADERS)
        assert any(
            entry["actor_role"] == "editor"
            and entry["action"] == "upload_document"
            and entry["resource_id"] == exhibit_id
            and "上传资料 review-reset-note.txt" in entry["summary"]
            and "审核状态已回到待审核" in entry["summary"]
            for entry in audit_response.json()["items"]
        )
    finally:
        cleanup_payload = client.get(f"/api/exhibits/{exhibit_id}").json()
        cleanup_payload["status"] = "制作中"
        cleanup_payload["review_status"] = "待审核"
        client.put(f"/api/exhibits/{exhibit_id}", json=cleanup_payload, headers=ADMIN_HEADERS)
        client.delete(f"/api/exhibits/{exhibit_id}", headers=ADMIN_HEADERS)


def test_uploaded_text_document_is_chunked_and_available_to_graphrag(monkeypatch, tmp_path):
    monkeypatch.setenv("FILE_STORAGE_ROOT", str(tmp_path))

    upload_response = client.post(
        "/api/exhibits/lever-play/assets",
        data={"asset_kind": "document", "note": "气流演示说明"},
        files={
            "file": (
                "airflow-note.txt",
                "伯努利气流环道用于解释低龄儿童可观察的气压差现象。".encode(),
                "text/plain",
            )
        },
        headers=EDITOR_HEADERS,
    )

    assert upload_response.status_code == 201
    document = upload_response.json()["documents"][-1]
    assert document["chunks"]
    assert document["chunks"][0]["text"].startswith("伯努利气流环道")

    search_response = client.post(
        "/api/graphrag/search",
        json={"query": "伯努利气流环道", "top_k": 1},
    )

    assert search_response.status_code == 200
    hit = search_response.json()["items"][0]
    assert hit["exhibit"]["id"] == "lever-play"
    assert any(
        citation["source_id"] == document["id"]
        and citation["source_type"] == "document"
        and "伯努利气流环道" in citation["snippet"]
        for citation in hit["citations"]
    )

    answer_response = client.post(
        "/api/graphrag/answer",
        json={"query": "伯努利气流环道", "top_k": 1},
    )

    assert answer_response.status_code == 200
    answer_payload = answer_response.json()
    assert any(citation["source_id"] == document["id"] for citation in answer_payload["citations"])
    assert "伯努利气流环道用于解释低龄儿童可观察的气压差现象" in answer_payload["answer"]


def test_editor_can_request_document_extraction_suggestions(monkeypatch, tmp_path):
    monkeypatch.setenv("FILE_STORAGE_ROOT", str(tmp_path))

    upload_response = client.post(
        "/api/exhibits/lever-play/assets",
        data={"asset_kind": "document", "note": "field suggestion smoke"},
        files={
            "file": (
                "suggested-exhibit.txt",
                (
                    "展项名称：儿童风洞实验台。"
                    "适用场馆：儿童科技馆。"
                    "标签：低龄儿童、亲子互动。"
                    "围绕力学主题，预算 20 万至 30 万。"
                ).encode(),
                "text/plain",
            )
        },
        headers=EDITOR_HEADERS,
    )
    assert upload_response.status_code == 201
    document = upload_response.json()["documents"][-1]

    response = client.get(
        f"/api/exhibits/lever-play/documents/{document['id']}/extraction-suggestions",
        headers=EDITOR_HEADERS,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["document_id"] == document["id"]
    assert payload["file_name"] == "suggested-exhibit.txt"
    assert payload["file_type"] == "txt"
    assert payload["source_note"] == "field suggestion smoke"
    assert payload["exhibit_name"] == "儿童风洞实验台"
    assert payload["theme"] == "力学"
    assert payload["venue_type"] == "儿童科技馆"
    assert payload["tags"] == ["低龄儿童", "亲子互动"]
    assert payload["field_sources"]["exhibit_name"][0]["chunk_id"] == document["chunks"][0]["id"]
    assert payload["field_sources"]["venue_type"][0]["chunk_id"] == document["chunks"][0]["id"]
    assert payload["field_sources"]["tags"][0]["chunk_id"] == document["chunks"][0]["id"]


def test_viewer_cannot_request_document_extraction_suggestions(monkeypatch, tmp_path):
    monkeypatch.setenv("FILE_STORAGE_ROOT", str(tmp_path))

    upload_response = client.post(
        "/api/exhibits/lever-play/assets",
        data={"asset_kind": "document", "note": "protected suggestions"},
        files={"file": ("viewer-denied.txt", b"viewer denied text", "text/plain")},
        headers=EDITOR_HEADERS,
    )
    assert upload_response.status_code == 201
    document = upload_response.json()["documents"][-1]

    response = client.get(
        f"/api/exhibits/lever-play/documents/{document['id']}/extraction-suggestions",
        headers={"X-User-Role": "viewer"},
    )

    assert response.status_code == 403


def test_uploaded_pdf_document_is_chunked_and_available_to_graphrag(monkeypatch, tmp_path):
    monkeypatch.setenv("FILE_STORAGE_ROOT", str(tmp_path))
    pdf_text = "pdf-smoke-token-ca68a67 explains pressure tunnel exhibit evidence"

    upload_response = client.post(
        "/api/exhibits/lever-play/assets",
        data={"asset_kind": "document", "note": "PDF 说明资料"},
        files={
            "file": (
                "pressure-tunnel.pdf",
                minimal_pdf_bytes(pdf_text),
                "application/pdf",
            )
        },
        headers=EDITOR_HEADERS,
    )

    assert upload_response.status_code == 201
    document = upload_response.json()["documents"][-1]
    assert document["file_type"] == "pdf"
    assert document["chunks"]
    assert pdf_text in document["chunks"][0]["text"]

    search_response = client.post(
        "/api/graphrag/search",
        json={"query": "pdf-smoke-token-ca68a67", "top_k": 1},
    )

    assert search_response.status_code == 200
    hit = search_response.json()["items"][0]
    assert hit["exhibit"]["id"] == "lever-play"
    assert any(
        citation["source_id"] == document["id"]
        and citation["source_type"] == "document"
        and "pdf-smoke-token-ca68a67" in citation["snippet"]
        for citation in hit["citations"]
    )


def test_uploaded_xlsx_document_is_chunked_and_available_to_graphrag(monkeypatch, tmp_path):
    monkeypatch.setenv("FILE_STORAGE_ROOT", str(tmp_path))
    xlsx_token = "xlsx-smoke-token-a51f3c"

    upload_response = client.post(
        "/api/exhibits/lever-play/assets",
        data={"asset_kind": "document", "note": "Excel 报价与配置清单"},
        files={
            "file": (
                "quote-matrix.xlsx",
                minimal_xlsx_bytes([
                    ["项目", "说明"],
                    ["滑轮挑战墙", f"{xlsx_token} 金属结构报价和互动配置依据"],
                ]),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
        headers=EDITOR_HEADERS,
    )

    assert upload_response.status_code == 201
    document = upload_response.json()["documents"][-1]
    assert document["file_type"] == "xlsx"
    assert document["chunks"]
    assert xlsx_token in document["chunks"][0]["text"]

    search_response = client.post(
        "/api/graphrag/search",
        json={"query": xlsx_token, "top_k": 1},
    )

    assert search_response.status_code == 200
    hit = search_response.json()["items"][0]
    assert hit["exhibit"]["id"] == "lever-play"
    assert any(
        citation["source_id"] == document["id"]
        and citation["source_type"] == "document"
        and xlsx_token in citation["snippet"]
        for citation in hit["citations"]
    )


def test_uploaded_docx_document_is_chunked_and_available_to_graphrag(monkeypatch, tmp_path):
    monkeypatch.setenv("FILE_STORAGE_ROOT", str(tmp_path))
    docx_token = "docx-smoke-token-f4b9e1"

    upload_response = client.post(
        "/api/exhibits/lever-play/assets",
        data={"asset_kind": "document", "note": "Word 方案说明"},
        files={
            "file": (
                "scheme-note.docx",
                minimal_docx_bytes([
                    "滑轮挑战墙深化设计说明",
                    f"{docx_token} 说明低龄儿童操作流程和安全维护要点",
                ]),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
        headers=EDITOR_HEADERS,
    )

    assert upload_response.status_code == 201
    document = upload_response.json()["documents"][-1]
    assert document["file_type"] == "docx"
    assert document["chunks"]
    assert docx_token in document["chunks"][0]["text"]

    search_response = client.post(
        "/api/graphrag/search",
        json={"query": docx_token, "top_k": 1},
    )

    assert search_response.status_code == 200
    hit = search_response.json()["items"][0]
    assert hit["exhibit"]["id"] == "lever-play"
    assert any(
        citation["source_id"] == document["id"]
        and citation["source_type"] == "document"
        and docx_token in citation["snippet"]
        for citation in hit["citations"]
    )


def test_uploaded_pptx_document_is_chunked_and_available_to_graphrag(monkeypatch, tmp_path):
    monkeypatch.setenv("FILE_STORAGE_ROOT", str(tmp_path))
    pptx_token = "pptx-smoke-token-91ec02"

    upload_response = client.post(
        "/api/exhibits/lever-play/assets",
        data={"asset_kind": "document", "note": "PPT 方案汇报"},
        files={
            "file": (
                "scheme-deck.pptx",
                minimal_pptx_bytes([
                    "滑轮挑战墙方案汇报",
                    f"{pptx_token} 说明展项互动形式和儿童安全边界",
                ]),
                "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            )
        },
        headers=EDITOR_HEADERS,
    )

    assert upload_response.status_code == 201
    document = upload_response.json()["documents"][-1]
    assert document["file_type"] == "pptx"
    assert document["chunks"]
    assert pptx_token in document["chunks"][0]["text"]

    search_response = client.post(
        "/api/graphrag/search",
        json={"query": pptx_token, "top_k": 1},
    )

    assert search_response.status_code == 200
    hit = search_response.json()["items"][0]
    assert hit["exhibit"]["id"] == "lever-play"
    assert any(
        citation["source_id"] == document["id"]
        and citation["source_type"] == "document"
        and pptx_token in citation["snippet"]
        for citation in hit["citations"]
    )


def test_upload_malformed_pdf_keeps_document_without_chunks(monkeypatch, tmp_path):
    monkeypatch.setenv("FILE_STORAGE_ROOT", str(tmp_path))

    response = client.post(
        "/api/exhibits/lever-play/assets",
        data={"asset_kind": "document", "note": "坏 PDF"},
        files={"file": ("broken.pdf", b"%PDF broken", "application/pdf")},
        headers=EDITOR_HEADERS,
    )

    assert response.status_code == 201
    document = response.json()["documents"][-1]
    assert document["name"] == "broken.pdf"
    assert document["chunks"] == []


def test_upload_asset_returns_404_for_unknown_exhibit(monkeypatch, tmp_path):
    monkeypatch.setenv("FILE_STORAGE_ROOT", str(tmp_path))

    response = client.post(
        "/api/exhibits/not-found/assets",
        data={"asset_kind": "media"},
        files={"file": ("scene.png", b"fake image bytes", "image/png")},
        headers=EDITOR_HEADERS,
    )

    assert response.status_code == 404


def test_upload_asset_rejects_unknown_asset_kind_before_storing_file(monkeypatch, tmp_path):
    monkeypatch.setenv("FILE_STORAGE_ROOT", str(tmp_path))

    response = client.post(
        "/api/exhibits/pulley-wall/assets",
        data={"asset_kind": "blueprint"},
        files={"file": ("wrong-kind.png", b"should not be stored", "image/png")},
        headers=EDITOR_HEADERS,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == {
        "error": "InvalidAssetKind",
        "message": "Asset kind must be media or document",
        "details": {
            "asset_kind": "blueprint",
            "valid_asset_kinds": ["media", "document"],
        },
    }
    assert list(tmp_path.iterdir()) == []


def test_only_admin_can_delete_uploaded_document_and_audit_it(monkeypatch, tmp_path):
    monkeypatch.setenv("FILE_STORAGE_ROOT", str(tmp_path))

    upload_response = client.post(
        "/api/exhibits/pulley-wall/assets",
        data={"asset_kind": "document", "note": "误传资料"},
        files={"file": ("delete-me.txt", b"temporary document", "text/plain")},
        headers=EDITOR_HEADERS,
    )
    assert upload_response.status_code == 201
    document = upload_response.json()["documents"][-1]

    editor_response = client.delete(
        f"/api/exhibits/pulley-wall/assets/{document['id']}",
        headers=EDITOR_HEADERS,
    )
    assert editor_response.status_code == 403

    admin_response = client.delete(
        f"/api/exhibits/pulley-wall/assets/{document['id']}",
        headers=ADMIN_HEADERS,
    )
    assert admin_response.status_code == 200
    payload = admin_response.json()
    assert all(item["id"] != document["id"] for item in payload["documents"])
    assert client.get(document["url"]).status_code == 404

    audit_response = client.get("/api/admin/audit-logs", headers=ADMIN_HEADERS)
    assert any(
        entry["actor_role"] == "admin"
        and entry["action"] == "delete_document"
        and entry["resource_id"] == "pulley-wall"
        and "删除资料" in entry["summary"]
        and document["id"] in entry["summary"]
        and "Deleted asset" not in entry["summary"]
        for entry in audit_response.json()["items"]
    )


def test_admin_can_delete_uploaded_media_asset(monkeypatch, tmp_path):
    monkeypatch.setenv("FILE_STORAGE_ROOT", str(tmp_path))

    upload_response = client.post(
        "/api/exhibits/pulley-wall/assets",
        data={"asset_kind": "media", "note": "误传照片"},
        files={"file": ("delete-media.png", b"temporary image", "image/png")},
        headers=EDITOR_HEADERS,
    )
    assert upload_response.status_code == 201
    media = upload_response.json()["media_assets"][-1]

    delete_response = client.delete(
        f"/api/exhibits/pulley-wall/assets/{media['id']}",
        headers=ADMIN_HEADERS,
    )

    assert delete_response.status_code == 200
    payload = delete_response.json()
    assert all(item["id"] != media["id"] for item in payload["media_assets"])
    assert client.get(media["url"]).status_code == 404

    audit_response = client.get("/api/admin/audit-logs", headers=ADMIN_HEADERS)
    assert any(
        entry["actor_role"] == "admin"
        and entry["action"] == "delete_media"
        and entry["resource_id"] == "pulley-wall"
        and "删除媒体" in entry["summary"]
        and media["id"] in entry["summary"]
        and "Deleted asset" not in entry["summary"]
        for entry in audit_response.json()["items"]
    )


def test_admin_cannot_delete_asset_from_approved_or_landed_exhibit(monkeypatch, tmp_path):
    monkeypatch.setenv("FILE_STORAGE_ROOT", str(tmp_path))

    upload_response = client.post(
        "/api/exhibits/lever-play/assets",
        data={"asset_kind": "document", "note": "受保护说明"},
        files={"file": ("protected-note.txt", b"protected note", "text/plain")},
        headers=EDITOR_HEADERS,
    )
    assert upload_response.status_code == 201
    document = upload_response.json()["documents"][-1]

    delete_response = client.delete(
        f"/api/exhibits/lever-play/assets/{document['id']}",
        headers=ADMIN_HEADERS,
    )

    assert delete_response.status_code == 409
    assert delete_response.json()["detail"]["error"] == "ProtectedExhibit"
    detail_response = client.get("/api/exhibits/lever-play")
    assert any(item["id"] == document["id"] for item in detail_response.json()["documents"])
    assert client.get(document["url"]).status_code == 200
