from io import BytesIO

from app.services.assets import (
    LocalFileStorageBackend,
    S3ObjectStorageBackend,
    storage_backend_from_env,
)


class FakeS3Client:
    def __init__(self):
        self.objects = {}
        self.uploads = []
        self.deleted = []

    def upload_fileobj(self, fileobj, bucket, key, ExtraArgs=None):
        self.objects[(bucket, key)] = fileobj.read()
        self.uploads.append((bucket, key, ExtraArgs))

    def list_objects_v2(self, Bucket, Prefix):
        contents = [
            {"Key": key}
            for bucket, key in self.objects
            if bucket == Bucket and key.startswith(Prefix)
        ]
        return {"Contents": contents}

    def download_file(self, bucket, key, filename):
        with open(filename, "wb") as output:
            output.write(self.objects[(bucket, key)])

    def delete_object(self, Bucket, Key):
        self.deleted.append((Bucket, Key))
        self.objects.pop((Bucket, Key), None)


def test_local_storage_backend_preserves_existing_file_lifecycle(tmp_path):
    backend = LocalFileStorageBackend(root=tmp_path)

    file_id, filename = backend.save(BytesIO(b"local bytes"), "现场 照片.png", "image/png")
    path = backend.path(file_id)

    assert filename == "现场_照片.png"
    assert path is not None
    assert path.read_bytes() == b"local bytes"
    assert backend.delete(file_id) is True
    assert backend.path(file_id) is None


def test_s3_storage_backend_uploads_downloads_and_deletes_with_local_cache(tmp_path):
    client = FakeS3Client()
    backend = S3ObjectStorageBackend(
        bucket="exhibit-assets",
        prefix="pir-system",
        cache_root=tmp_path,
        client=client,
    )

    file_id, filename = backend.save(BytesIO(b"remote bytes"), "报价.pdf", "application/pdf")
    cached_path = backend.path(file_id)

    assert filename == "报价.pdf"
    assert client.uploads[0][0] == "exhibit-assets"
    assert client.uploads[0][1] == f"pir-system/{file_id}/报价.pdf"
    assert client.uploads[0][2]["ContentType"] == "application/pdf"
    assert cached_path is not None
    assert cached_path.read_bytes() == b"remote bytes"

    assert backend.delete(file_id) is True
    assert client.deleted == [("exhibit-assets", f"pir-system/{file_id}/报价.pdf")]
    assert backend.path(file_id) is None


def test_storage_backend_from_env_defaults_local_and_can_build_s3(monkeypatch, tmp_path):
    monkeypatch.setenv("FILE_STORAGE_ROOT", str(tmp_path / "local"))
    assert isinstance(storage_backend_from_env(), LocalFileStorageBackend)

    monkeypatch.setenv("FILE_STORAGE_BACKEND", "s3")
    monkeypatch.setenv("S3_BUCKET", "exhibit-assets")
    monkeypatch.setenv("S3_ENDPOINT_URL", "http://minio:9000")
    monkeypatch.setenv("S3_ACCESS_KEY_ID", "minio")
    monkeypatch.setenv("S3_SECRET_ACCESS_KEY", "minio-secret")
    monkeypatch.setenv("S3_CACHE_ROOT", str(tmp_path / "cache"))

    backend = storage_backend_from_env(client=FakeS3Client())

    assert isinstance(backend, S3ObjectStorageBackend)
