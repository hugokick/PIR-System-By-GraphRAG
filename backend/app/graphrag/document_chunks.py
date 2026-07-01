from pydantic import BaseModel, Field


class DocumentSource(BaseModel):
    exhibit_id: str
    document_id: str
    file_name: str
    file_type: str
    source_note: str | None = None


class DocumentTextBlock(BaseModel):
    text: str
    page_number: int | None = None
    paragraph_index: int | None = None
    section_title: str | None = None


class DocumentChunk(BaseModel):
    chunk_id: str
    exhibit_id: str
    document_id: str
    file_name: str
    file_type: str
    text: str
    page_number_start: int | None = None
    page_number_end: int | None = None
    paragraph_index_start: int | None = None
    paragraph_index_end: int | None = None
    section_title: str | None = None
    source_locator: str


class CitationSource(BaseModel):
    exhibit_id: str
    document_id: str
    file_name: str
    chunk_id: str
    page_number_start: int | None = None
    page_number_end: int | None = None
    paragraph_index_start: int | None = None
    paragraph_index_end: int | None = None
    snippet: str
    source_locator: str


class DocumentChunkResult(BaseModel):
    source: DocumentSource
    chunks: list[DocumentChunk] = Field(default_factory=list)
    citations: list[CitationSource] = Field(default_factory=list)


def chunk_document_source(
    source: DocumentSource,
    blocks: list[DocumentTextBlock],
    max_chars: int = 500,
    overlap_chars: int = 50,
) -> DocumentChunkResult:
    chunks: list[DocumentChunk] = []
    for block in blocks:
        text = block.text.strip()
        if not text:
            continue

        if len(text) <= max_chars:
            chunks.append(
                _make_chunk(
                    source=source,
                    text=text,
                    page_number_start=block.page_number,
                    page_number_end=block.page_number,
                    paragraph_index_start=block.paragraph_index,
                    paragraph_index_end=block.paragraph_index,
                    section_title=block.section_title,
                    chunk_index=len(chunks) + 1,
                )
            )
            continue

        start = 0
        step = max(1, max_chars - overlap_chars)
        while start < len(text):
            end = min(len(text), start + max_chars)
            chunks.append(
                _make_chunk(
                    source=source,
                    text=text[start:end],
                    page_number_start=block.page_number,
                    page_number_end=block.page_number,
                    paragraph_index_start=block.paragraph_index,
                    paragraph_index_end=block.paragraph_index,
                    section_title=block.section_title,
                    chunk_index=len(chunks) + 1,
                )
            )
            if end >= len(text):
                break
            start += step

    citations = [
        CitationSource(
            exhibit_id=chunk.exhibit_id,
            document_id=chunk.document_id,
            file_name=chunk.file_name,
            chunk_id=chunk.chunk_id,
            page_number_start=chunk.page_number_start,
            page_number_end=chunk.page_number_end,
            paragraph_index_start=chunk.paragraph_index_start,
            paragraph_index_end=chunk.paragraph_index_end,
            snippet=chunk.text[:120],
            source_locator=chunk.source_locator,
        )
        for chunk in chunks
    ]
    return DocumentChunkResult(source=source, chunks=chunks, citations=citations)


def chunk_document_sources(
    items: list[tuple[DocumentSource, list[DocumentTextBlock]]],
    max_chars: int = 500,
    overlap_chars: int = 50,
) -> list[DocumentChunkResult]:
    return [
        chunk_document_source(
            source=source,
            blocks=blocks,
            max_chars=max_chars,
            overlap_chars=overlap_chars,
        )
        for source, blocks in items
    ]


def _make_chunk(
    source: DocumentSource,
    text: str,
    page_number_start: int | None,
    page_number_end: int | None,
    paragraph_index_start: int | None,
    paragraph_index_end: int | None,
    section_title: str | None,
    chunk_index: int,
) -> DocumentChunk:
    locator_parts = [
        f"file={source.file_name}",
        f"page={page_number_start}" if page_number_start is not None else "page=unknown",
        f"paragraph={paragraph_index_start}" if paragraph_index_start is not None else "paragraph=unknown",
    ]
    return DocumentChunk(
        chunk_id=f"{source.document_id}:chunk-{chunk_index}",
        exhibit_id=source.exhibit_id,
        document_id=source.document_id,
        file_name=source.file_name,
        file_type=source.file_type,
        text=text,
        page_number_start=page_number_start,
        page_number_end=page_number_end,
        paragraph_index_start=paragraph_index_start,
        paragraph_index_end=paragraph_index_end,
        section_title=section_title,
        source_locator=", ".join(locator_parts),
    )
