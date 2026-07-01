import os
import re
import shutil
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile


def storage_root() -> Path:
    return Path(os.environ.get("FILE_STORAGE_ROOT", Path.cwd() / "backend" / "storage"))


def save_upload_file(file: UploadFile) -> tuple[str, str]:
    file_id = uuid4().hex
    filename = safe_filename(file.filename or "upload.bin")
    target = storage_root() / file_id
    target.mkdir(parents=True, exist_ok=True)
    file_path = target / filename
    with file_path.open("wb") as output:
        shutil.copyfileobj(file.file, output)
    return file_id, filename


def file_path(file_id: str) -> Path | None:
    if not re.fullmatch(r"[a-f0-9]{32}", file_id):
        return None
    directory = storage_root() / file_id
    if not directory.exists():
        return None
    files = [path for path in directory.iterdir() if path.is_file()]
    return files[0] if files else None


def delete_stored_file(file_id: str) -> bool:
    if not re.fullmatch(r"[a-f0-9]{32}", file_id):
        return False
    directory = storage_root() / file_id
    if not directory.exists() or not directory.is_dir():
        return False
    shutil.rmtree(directory)
    return True


def file_id_from_url(url: str) -> str | None:
    match = re.fullmatch(r"(?:/pir-system)?/api/files/([a-f0-9]{32})", url)
    if match is None:
        return None
    return match.group(1)


def safe_filename(filename: str) -> str:
    cleaned = Path(filename).name.strip() or "upload.bin"
    return re.sub(r"[^A-Za-z0-9._\-\u4e00-\u9fff]+", "_", cleaned)


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
