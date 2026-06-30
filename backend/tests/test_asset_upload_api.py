from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


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


def test_upload_image_asset_attaches_media_and_serves_file(monkeypatch, tmp_path):
    monkeypatch.setenv("FILE_STORAGE_ROOT", str(tmp_path))

    response = client.post(
        "/api/exhibits/lever-play/assets",
        data={"asset_kind": "media", "note": "现场照片"},
        files={"file": ("scene.png", b"fake image bytes", "image/png")},
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


def test_upload_document_asset_attaches_document_source(monkeypatch, tmp_path):
    monkeypatch.setenv("FILE_STORAGE_ROOT", str(tmp_path))

    response = client.post(
        "/api/exhibits/lever-play/assets",
        data={"asset_kind": "document", "note": "报价资料"},
        files={"file": ("quote.pdf", b"%PDF fake", "application/pdf")},
    )

    assert response.status_code == 201
    payload = response.json()
    document = payload["documents"][-1]
    assert document["name"] == "quote.pdf"
    assert document["file_type"] == "pdf"
    assert document["source_note"] == "报价资料"
    assert document["url"].startswith("/api/files/")


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


def test_upload_malformed_pdf_keeps_document_without_chunks(monkeypatch, tmp_path):
    monkeypatch.setenv("FILE_STORAGE_ROOT", str(tmp_path))

    response = client.post(
        "/api/exhibits/lever-play/assets",
        data={"asset_kind": "document", "note": "坏 PDF"},
        files={"file": ("broken.pdf", b"%PDF broken", "application/pdf")},
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
    )

    assert response.status_code == 404
