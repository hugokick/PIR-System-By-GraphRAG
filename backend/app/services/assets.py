import os
import re
import shutil
from pathlib import Path
from typing import BinaryIO, Protocol
from uuid import uuid4

from fastapi import UploadFile


class FileStorageBackend(Protocol):
    def save(self, fileobj: BinaryIO, filename: str, content_type: str | None = None) -> tuple[str, str]:
        ...

    def path(self, file_id: str) -> Path | None:
        ...

    def delete(self, file_id: str) -> bool:
        ...


class LocalFileStorageBackend:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or storage_root()

    def save(self, fileobj: BinaryIO, filename: str, content_type: str | None = None) -> tuple[str, str]:
        file_id = uuid4().hex
        safe_name = safe_filename(filename or "upload.bin")
        target = self.root / file_id
        target.mkdir(parents=True, exist_ok=True)
        file_path = target / safe_name
        with file_path.open("wb") as output:
            shutil.copyfileobj(fileobj, output)
        return file_id, safe_name

    def path(self, file_id: str) -> Path | None:
        if not valid_file_id(file_id):
            return None
        directory = self.root / file_id
        if not directory.exists():
            return None
        files = [path for path in directory.iterdir() if path.is_file()]
        return files[0] if files else None

    def delete(self, file_id: str) -> bool:
        if not valid_file_id(file_id):
            return False
        directory = self.root / file_id
        if not directory.exists() or not directory.is_dir():
            return False
        shutil.rmtree(directory)
        return True


class S3ObjectStorageBackend:
    def __init__(
        self,
        *,
        bucket: str,
        prefix: str = "",
        cache_root: Path | None = None,
        client=None,
    ) -> None:
        self.bucket = bucket
        self.prefix = prefix.strip("/")
        self.cache_root = cache_root or Path(os.environ.get("S3_CACHE_ROOT", Path.cwd() / "backend" / "storage-cache"))
        self.client = client or _s3_client_from_env()

    def save(self, fileobj: BinaryIO, filename: str, content_type: str | None = None) -> tuple[str, str]:
        file_id = uuid4().hex
        safe_name = safe_filename(filename or "upload.bin")
        key = self._key(file_id, safe_name)
        extra_args = {"ContentType": content_type or "application/octet-stream"}
        self.client.upload_fileobj(fileobj, self.bucket, key, ExtraArgs=extra_args)
        return file_id, safe_name

    def path(self, file_id: str) -> Path | None:
        key = self._object_key_for_file_id(file_id)
        if key is None:
            return None
        filename = Path(key).name
        target_dir = self.cache_root / file_id
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / filename
        if not target.exists():
            self.client.download_file(self.bucket, key, str(target))
        return target

    def delete(self, file_id: str) -> bool:
        key = self._object_key_for_file_id(file_id)
        if key is None:
            return False
        self.client.delete_object(Bucket=self.bucket, Key=key)
        cache_dir = self.cache_root / file_id
        if cache_dir.exists():
            shutil.rmtree(cache_dir)
        return True

    def _object_key_for_file_id(self, file_id: str) -> str | None:
        if not valid_file_id(file_id):
            return None
        prefix = self._key_prefix(file_id)
        response = self.client.list_objects_v2(Bucket=self.bucket, Prefix=prefix)
        for item in response.get("Contents", []):
            key = item.get("Key")
            if key and not key.endswith("/"):
                return key
        return None

    def _key_prefix(self, file_id: str) -> str:
        return f"{self.prefix}/{file_id}/" if self.prefix else f"{file_id}/"

    def _key(self, file_id: str, filename: str) -> str:
        return f"{self._key_prefix(file_id)}{filename}"


def storage_root() -> Path:
    return Path(os.environ.get("FILE_STORAGE_ROOT", Path.cwd() / "backend" / "storage"))


def storage_backend_from_env(client=None) -> FileStorageBackend:
    backend = os.environ.get("FILE_STORAGE_BACKEND", "local").strip().lower()
    if backend in {"s3", "minio", "object-storage", "object_storage"}:
        bucket = os.environ.get("S3_BUCKET", "").strip()
        if not bucket:
            return LocalFileStorageBackend()
        return S3ObjectStorageBackend(
            bucket=bucket,
            prefix=os.environ.get("S3_PREFIX", "").strip(),
            cache_root=Path(os.environ.get("S3_CACHE_ROOT", Path.cwd() / "backend" / "storage-cache")),
            client=client,
        )
    return LocalFileStorageBackend()


def save_upload_file(file: UploadFile) -> tuple[str, str]:
    return storage_backend_from_env().save(file.file, file.filename or "upload.bin", file.content_type)


def file_path(file_id: str) -> Path | None:
    return storage_backend_from_env().path(file_id)


def delete_stored_file(file_id: str) -> bool:
    return storage_backend_from_env().delete(file_id)


def file_id_from_url(url: str) -> str | None:
    match = re.fullmatch(r"(?:/pir-system)?/api/files/([a-f0-9]{32})", url)
    if match is None:
        return None
    return match.group(1)


def safe_filename(filename: str) -> str:
    cleaned = Path(filename).name.strip() or "upload.bin"
    return re.sub(r"[^A-Za-z0-9._\-\u4e00-\u9fff]+", "_", cleaned)


def valid_file_id(file_id: str) -> bool:
    return bool(re.fullmatch(r"[a-f0-9]{32}", file_id))


def media_type_from_upload(file: UploadFile) -> str:
    content_type = file.content_type or ""
    suffix = Path(file.filename or "").suffix.lower()
    if content_type.startswith("image/"):
        return "image"
    if content_type.startswith("video/"):
        return "video"
    if suffix in {".dwg", ".dxf", ".skp"}:
        return "drawing"
    if suffix in {".xls", ".xlsx", ".csv"}:
        return "quote"
    return "document"


def file_extension(filename: str) -> str:
    return Path(filename).suffix.lower().lstrip(".") or "file"


def _s3_client_from_env():
    import boto3

    return boto3.client(
        "s3",
        endpoint_url=os.environ.get("S3_ENDPOINT_URL") or None,
        aws_access_key_id=os.environ.get("S3_ACCESS_KEY_ID") or None,
        aws_secret_access_key=os.environ.get("S3_SECRET_ACCESS_KEY") or None,
        region_name=os.environ.get("S3_REGION") or None,
    )
