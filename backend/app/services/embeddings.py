import hashlib
import math
import re
from collections.abc import Sequence

from app.schemas import DocumentAsset, DocumentChunk, ExhibitResponse


EMBEDDING_DIMENSIONS = 1536


def stable_embedding(text: str, dimensions: int = EMBEDDING_DIMENSIONS) -> list[float]:
    tokens = _tokens(text)
    vector = [0.0] * dimensions
    if not tokens:
        return vector

    for token in tokens:
        digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
        index = int.from_bytes(digest[:4], "big") % dimensions
        sign = 1 if digest[4] % 2 == 0 else -1
        vector[index] += sign * (1.0 + min(len(token), 6) / 10)

    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [round(value / norm, 6) for value in vector]


def embedding_text_for_exhibit(exhibit: ExhibitResponse) -> str:
    return _join_text(
        [
            exhibit.id,
            exhibit.name,
            exhibit.category,
            exhibit.theme.name,
            exhibit.venue_type,
            exhibit.owner.name,
            exhibit.supplier.name,
            exhibit.project.name,
            exhibit.description,
            *[material.name for material in exhibit.materials],
            *[interaction.name for interaction in exhibit.interactions],
            *exhibit.tags,
        ]
    )


def embedding_text_for_document_chunk(
    exhibit: ExhibitResponse,
    document: DocumentAsset,
    chunk: DocumentChunk | None = None,
) -> str:
    return _join_text(
        [
            exhibit.id,
            exhibit.name,
            document.id,
            document.name,
            document.file_type,
            document.source_note or "",
            chunk.text if chunk else "",
        ]
    )


def vector_literal(values: Sequence[float]) -> str:
    return "[" + ",".join(f"{value:.6f}" for value in values) + "]"


def _join_text(values: Sequence[str]) -> str:
    return " ".join(value.strip() for value in values if value and value.strip())


def _tokens(text: str) -> list[str]:
    normalized = text.strip().lower()
    if not normalized:
        return []

    coarse_tokens = [
        token
        for token in re.split(r"[\s,，、。；;:：|/\\()（）\[\]{}<>《》\"']+", normalized)
        if token
    ]
    tokens: list[str] = []
    for token in coarse_tokens:
        tokens.append(token)
        if len(token) > 1:
            tokens.extend(token[index : index + 2] for index in range(len(token) - 1))
    return tokens
