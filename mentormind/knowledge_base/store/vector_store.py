"""``VectorStore`` — the vector table behind an interface (spec 01 FR-05c, constitution art. 5).

Backends, chosen by ``KNOWHOW_VECTOR_BACKEND``:

* ``memory`` — in-process: dense cosine over the store's embedder plus BM25 over accent-folded
  tokens, fused by Reciprocal Rank Fusion (k=60, the fusion of spec 05). For unit tests / CI
  without Docker (AC-08).
* ``pgvector`` — ``public.knowhow_chunks`` of ``infra/postgres/init.sql``; lands with spec 02
  T02-6 (it needs a Postgres driver and the bge-m3 embedder).

Filters are exact matches on ``source_type``, ``kind``, ``ref_id`` and ``data_classification``;
``process_id`` / ``part_number`` match when the chunk lists that value.
"""

from __future__ import annotations

import hashlib
import math
import re
import unicodedata
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from typing import Any, Protocol

from mentormind.core.config import Settings, get_settings
from mentormind.core.schemas.vector import VectorChunk, VectorHit

RRF_K = 60
_BM25_K1 = 1.5
_BM25_B = 0.75
_TOKEN = re.compile(r"\w+")
_EXACT_FILTERS = ("source_type", "kind", "ref_id", "data_classification")
_LIST_FILTERS = {"process_id": "process_ids", "part_number": "part_numbers"}


class VectorStoreError(RuntimeError):
    """The configured vector backend cannot be used."""


class Embedder(Protocol):
    """Text -> dense vector. The real one (bge-m3, 1024 dims) arrives with spec 02."""

    @property
    def dim(self) -> int: ...

    def embed(self, texts: Sequence[str]) -> list[list[float]]: ...


class VectorStore(Protocol):
    """The surface every backend offers (spec 01 FR-05c)."""

    def upsert(self, chunks: Iterable[VectorChunk]) -> int:
        """Insert or replace by ``chunk_id``; returns how many chunks were written."""
        ...

    def search(self, query: str, k: int = 8, filters: Mapping[str, Any] | None = None) -> list[VectorHit]:
        """Top ``k`` chunks for ``query`` that pass ``filters``, best first."""
        ...

    def delete(self, ids: Iterable[str]) -> int:
        """Remove chunks by ``chunk_id``; returns how many existed."""
        ...


def tokens(text: str) -> list[str]:
    """Lower-case, accent-folded word tokens ("Tránh trầy" -> ["tranh", "tray"])."""
    decomposed = unicodedata.normalize("NFD", text.replace("đ", "d").replace("Đ", "D"))
    folded = "".join(c for c in decomposed if not unicodedata.combining(c)).lower()
    return _TOKEN.findall(folded)


class HashingEmbedder:
    """Deterministic bag-of-words embedder (feature hashing): no model, no network.

    Good enough for tests and the offline demo; semantic search needs the real embedder.
    """

    def __init__(self, dim: int = 256) -> None:
        if dim <= 0:
            raise ValueError("dim must be positive")
        self._dim = dim

    @property
    def dim(self) -> int:
        return self._dim

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        return [self._one(text) for text in texts]

    def _one(self, text: str) -> list[float]:
        vector = [0.0] * self._dim
        for token in tokens(text):
            digest = int.from_bytes(hashlib.blake2b(token.encode(), digest_size=8).digest(), "big")
            vector[digest % self._dim] += 1.0 if digest >> 63 else -1.0
        norm = math.sqrt(sum(v * v for v in vector))
        return [v / norm for v in vector] if norm else vector


class MemoryVectorStore:
    """In-process :class:`VectorStore`: cosine + BM25, fused by RRF."""

    def __init__(self, embedder: Embedder | None = None) -> None:
        self._embedder = embedder or HashingEmbedder()
        self._chunks: dict[str, VectorChunk] = {}

    def upsert(self, chunks: Iterable[VectorChunk]) -> int:
        batch = list(chunks)
        missing = [c for c in batch if c.embedding is None]
        vectors = iter(self._embedder.embed([c.text for c in missing]))
        for chunk in batch:
            if chunk.embedding is None:
                chunk = chunk.model_copy(update={"embedding": next(vectors)})
            elif len(chunk.embedding) != self._embedder.dim:
                raise VectorStoreError(
                    f"Chunk {chunk.chunk_id}: embedding có {len(chunk.embedding)} chiều, "
                    f"store cần {self._embedder.dim}."
                )
            self._chunks[chunk.chunk_id] = chunk
        return len(batch)

    def search(self, query: str, k: int = 8, filters: Mapping[str, Any] | None = None) -> list[VectorHit]:
        candidates = [c for c in self._chunks.values() if _passes(c, filters or {})]
        if not candidates or k <= 0:
            return []
        query_vector = self._embedder.embed([query])[0]
        dense = sorted(candidates, key=lambda c: _cosine(query_vector, c.embedding or []), reverse=True)
        lexical_scores = _bm25(tokens(query), candidates)
        lexical = sorted(
            (c for c in candidates if lexical_scores[c.chunk_id] > 0),
            key=lambda c: lexical_scores[c.chunk_id],
            reverse=True,
        )
        fused: dict[str, float] = {}
        for ranking in (dense, lexical):
            for rank, chunk in enumerate(ranking, start=1):
                fused[chunk.chunk_id] = fused.get(chunk.chunk_id, 0.0) + 1.0 / (RRF_K + rank)
        best = sorted(fused.items(), key=lambda item: item[1], reverse=True)[:k]
        return [VectorHit(chunk=self._chunks[cid], score=round(score, 6)) for cid, score in best]

    def delete(self, ids: Iterable[str]) -> int:
        return sum(self._chunks.pop(i, None) is not None for i in ids)


def get_vector_store(settings: Settings | None = None, *, embedder: Embedder | None = None) -> VectorStore:
    """The backend selected by ``KNOWHOW_VECTOR_BACKEND`` (only config changes, art. 5).

    Raises:
        VectorStoreError: ``pgvector`` is selected but its backend has not landed yet.
    """
    settings = settings or get_settings()
    if settings.vector_backend == "memory":
        return MemoryVectorStore(embedder)
    raise VectorStoreError(
        "Backend pgvector chưa có (spec 02 T02-6). Đặt KNOWHOW_VECTOR_BACKEND=memory để chạy không cần Docker."
    )


def _passes(chunk: VectorChunk, filters: Mapping[str, Any]) -> bool:
    for key, wanted in filters.items():
        if key in _EXACT_FILTERS:
            if getattr(chunk, key) != wanted:
                return False
        elif key in _LIST_FILTERS:
            if wanted not in getattr(chunk, _LIST_FILTERS[key]):
                return False
        else:
            raise ValueError(f"Filter không hỗ trợ: {key!r}")
    return True


def _cosine(a: Sequence[float], b: Sequence[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    norm = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return dot / norm if norm else 0.0


def _bm25(query: list[str], chunks: Sequence[VectorChunk]) -> dict[str, float]:
    docs = {c.chunk_id: Counter(tokens(c.text)) for c in chunks}
    lengths = {cid: sum(tf.values()) for cid, tf in docs.items()}
    average = sum(lengths.values()) / len(docs) or 1.0
    scores = dict.fromkeys(docs, 0.0)
    for term in set(query):
        having = sum(1 for tf in docs.values() if term in tf)
        if not having:
            continue
        idf = math.log(1 + (len(docs) - having + 0.5) / (having + 0.5))
        for cid, tf in docs.items():
            f = tf.get(term, 0)
            if f:
                norm = 1 - _BM25_B + _BM25_B * lengths[cid] / average
                scores[cid] += idf * f * (_BM25_K1 + 1) / (f + _BM25_K1 * norm)
    return scores
