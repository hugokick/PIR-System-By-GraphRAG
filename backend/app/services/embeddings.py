import hashlib
import math
import os
import re
from collections.abc import Callable, Sequence
from typing import Any, Protocol

import httpx

from app.schemas import DocumentAsset, DocumentChunk, ExhibitResponse


EMBEDDING_DIMENSIONS = 1536
PostJson = Callable[[str, dict[str, Any], dict[str, str], float], dict[str, Any]]


class EmbeddingProvider(Protocol):
    def embed(self, text: str) -> list[float] | None: ...


class OpenAICompatibleEmbeddingProvider:
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        dimensions: int = EMBEDDING_DIMENSIONS,
        timeout: float = 20.0,
        post_json: PostJson | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.dimensions = dimensions
        self.timeout = timeout
        self._post_json = post_json or _post_json

    def embed(self, text: str) -> list[float] | None:
        try:
            response = self._post_json(
                f"{self.base_url}/embeddings",
                {"model": self.model, "input": text},
                {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                self.timeout,
            )
            values = response["data"][0]["embedding"]
            if not isinstance(values, list):
                return None
            vector = [float(value) for value in values]
            return vector if len(vector) == self.dimensions else None
        except Exception:  # noqa: BLE001 - embedding failures must fall back
            return None


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


def embedding_vector(
    text: str,
    *,
    dimensions: int = EMBEDDING_DIMENSIONS,
    provider: EmbeddingProvider | None = None,
) -> list[float]:
    if provider is not None:
        vector = provider.embed(text)
        if vector is not None and len(vector) == dimensions:
            return vector
    return stable_embedding(text, dimensions=dimensions)


def embedding_provider_from_env() -> EmbeddingProvider | None:
    provider_name = os.environ.get("EMBEDDING_PROVIDER", "").strip().lower()
    if provider_name not in {"openai-compatible", "openai_compatible"}:
        return None

    base_url = os.environ.get("EMBEDDING_BASE_URL", "").strip()
    api_key = os.environ.get("EMBEDDING_API_KEY", "").strip()
    model = os.environ.get("EMBEDDING_MODEL", "").strip()
    if not base_url or not api_key or not model:
        return None

    return OpenAICompatibleEmbeddingProvider(
        base_url=base_url,
        api_key=api_key,
        model=model,
        dimensions=_int_env("EMBEDDING_DIMENSIONS", EMBEDDING_DIMENSIONS),
        timeout=_float_env("EMBEDDING_TIMEOUT_SECONDS", 20.0),
    )


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


def _post_json(url: str, payload: dict[str, Any], headers: dict[str, str], timeout: float) -> dict[str, Any]:
    with httpx.Client(timeout=timeout) as client:
        response = client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()


def _int_env(name: str, default: int) -> int:
    value = os.environ.get(name, "").strip()
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _float_env(name: str, default: float) -> float:
    value = os.environ.get(name, "").strip()
    if not value:
        return default
    try:
        return float(value)
    except ValueError:
        return default
