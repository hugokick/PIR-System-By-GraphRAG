from pathlib import Path

from app.schemas import DocumentChunk


TEXT_FILE_TYPES = {"txt", "md", "markdown", "csv", "tsv", "json", "log"}
MAX_TEXT_CHARS = 20000
CHUNK_SIZE = 500
CHUNK_OVERLAP = 80


def extract_document_chunks(document_id: str, path: Path, file_type: str) -> list[DocumentChunk]:
    text = extract_document_text(path, file_type)
    if not text:
        return []
    return [
        DocumentChunk(id=f"{document_id}:chunk-{index + 1}", text=chunk, sequence=index + 1)
        for index, chunk in enumerate(split_text(text))
    ]


def extract_document_text(path: Path, file_type: str) -> str:
    if file_type.lower() not in TEXT_FILE_TYPES:
        return ""
    raw = path.read_bytes()[:MAX_TEXT_CHARS]
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return normalize_text(raw.decode(encoding))
        except UnicodeDecodeError:
            continue
    return normalize_text(raw.decode("utf-8", errors="ignore"))


def split_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    normalized = normalize_text(text)
    if not normalized:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(normalized):
        end = min(start + chunk_size, len(normalized))
        chunk = normalized[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end == len(normalized):
            break
        start = max(end - overlap, start + 1)
    return chunks


def normalize_text(text: str) -> str:
    return " ".join(text.replace("\x00", " ").split())
