from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


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


def test_upload_asset_returns_404_for_unknown_exhibit(monkeypatch, tmp_path):
    monkeypatch.setenv("FILE_STORAGE_ROOT", str(tmp_path))

    response = client.post(
        "/api/exhibits/not-found/assets",
        data={"asset_kind": "media"},
        files={"file": ("scene.png", b"fake image bytes", "image/png")},
    )

    assert response.status_code == 404
