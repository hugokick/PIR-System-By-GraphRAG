from pathlib import Path
from xml.etree import ElementTree
from zipfile import ZipFile

from app.schemas import DocumentChunk


TEXT_FILE_TYPES = {"txt", "md", "markdown", "csv", "tsv", "json", "log"}
PDF_FILE_TYPES = {"pdf"}
XLSX_FILE_TYPES = {"xlsx"}
MAX_TEXT_CHARS = 20000
CHUNK_SIZE = 500
CHUNK_OVERLAP = 80
SPREADSHEET_NAMESPACE = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def extract_document_chunks(document_id: str, path: Path, file_type: str) -> list[DocumentChunk]:
    text = extract_document_text(path, file_type)
    if not text:
        return []
    return [
        DocumentChunk(id=f"{document_id}:chunk-{index + 1}", text=chunk, sequence=index + 1)
        for index, chunk in enumerate(split_text(text))
    ]


def extract_document_text(path: Path, file_type: str) -> str:
    normalized_type = file_type.lower()
    if normalized_type in PDF_FILE_TYPES:
        return extract_pdf_text(path)
    if normalized_type in XLSX_FILE_TYPES:
        return extract_xlsx_text(path)
    if normalized_type not in TEXT_FILE_TYPES:
        return ""
    raw = path.read_bytes()[:MAX_TEXT_CHARS]
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return normalize_text(raw.decode(encoding))
        except UnicodeDecodeError:
            continue
    return normalize_text(raw.decode("utf-8", errors="ignore"))


def extract_pdf_text(path: Path) -> str:
    from pypdf import PdfReader

    try:
        reader = PdfReader(str(path))
    except Exception:
        return ""
    parts: list[str] = []
    try:
        for page in reader.pages:
            text = page.extract_text() or ""
            if text:
                parts.append(text)
            if sum(len(part) for part in parts) >= MAX_TEXT_CHARS:
                break
    except Exception:
        return ""
    return normalize_text(" ".join(parts))[:MAX_TEXT_CHARS]


def extract_xlsx_text(path: Path) -> str:
    try:
        with ZipFile(path) as archive:
            shared_strings = read_xlsx_shared_strings(archive)
            parts: list[str] = []
            for sheet_name in sorted(
                name for name in archive.namelist() if name.startswith("xl/worksheets/") and name.endswith(".xml")
            ):
                root = ElementTree.fromstring(archive.read(sheet_name))
                for row in root.findall(".//s:sheetData/s:row", SPREADSHEET_NAMESPACE):
                    values = [
                        xlsx_cell_value(cell, shared_strings)
                        for cell in row.findall("s:c", SPREADSHEET_NAMESPACE)
                    ]
                    row_text = " ".join(value for value in values if value)
                    if row_text:
                        parts.append(row_text)
                    if sum(len(part) for part in parts) >= MAX_TEXT_CHARS:
                        return normalize_text(" ".join(parts))[:MAX_TEXT_CHARS]
    except Exception:
        return ""
    return normalize_text(" ".join(parts))[:MAX_TEXT_CHARS]


def read_xlsx_shared_strings(archive: ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []
    root = ElementTree.fromstring(archive.read("xl/sharedStrings.xml"))
    values: list[str] = []
    for item in root.findall("s:si", SPREADSHEET_NAMESPACE):
        values.append("".join(node.text or "" for node in item.findall(".//s:t", SPREADSHEET_NAMESPACE)))
    return values


def xlsx_cell_value(cell: ElementTree.Element, shared_strings: list[str]) -> str:
    cell_type = cell.attrib.get("t")
    if cell_type == "s":
        value_node = cell.find("s:v", SPREADSHEET_NAMESPACE)
        if value_node is None or value_node.text is None:
            return ""
        try:
            return shared_strings[int(value_node.text)]
        except (ValueError, IndexError):
            return ""
    if cell_type == "inlineStr":
        return "".join(node.text or "" for node in cell.findall(".//s:t", SPREADSHEET_NAMESPACE))
    value_node = cell.find("s:v", SPREADSHEET_NAMESPACE)
    return value_node.text or "" if value_node is not None else ""


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
