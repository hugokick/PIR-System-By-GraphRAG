from fastapi.testclient import TestClient
from zipfile import ZIP_DEFLATED, ZipFile
from io import BytesIO

from app.main import app


client = TestClient(app)

ADMIN_HEADERS = {"X-User-Role": "admin"}
EDITOR_HEADERS = {"X-User-Role": "editor"}


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


def test_only_admin_can_delete_uploaded_document_and_audit_it(monkeypatch, tmp_path):
    monkeypatch.setenv("FILE_STORAGE_ROOT", str(tmp_path))

    upload_response = client.post(
        "/api/exhibits/lever-play/assets",
        data={"asset_kind": "document", "note": "误传资料"},
        files={"file": ("delete-me.txt", b"temporary document", "text/plain")},
        headers=EDITOR_HEADERS,
    )
    assert upload_response.status_code == 201
    document = upload_response.json()["documents"][-1]

    editor_response = client.delete(
        f"/api/exhibits/lever-play/assets/{document['id']}",
        headers=EDITOR_HEADERS,
    )
    assert editor_response.status_code == 403

    admin_response = client.delete(
        f"/api/exhibits/lever-play/assets/{document['id']}",
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
        and entry["resource_id"] == "lever-play"
        and document["id"] in entry["summary"]
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
        and media["id"] in entry["summary"]
        for entry in audit_response.json()["items"]
    )
