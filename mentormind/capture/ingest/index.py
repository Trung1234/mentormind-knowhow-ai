"""Chunk files -> vector store (spec 02 FR-07, AC-14, AC-15)."""

from __future__ import annotations

import re
from collections.abc import Collection, Iterable
from dataclasses import dataclass, field
from itertools import islice
from pathlib import Path

from mentormind.capture.ingest.jsonl import ChunkFileError, read_chunks
from mentormind.core.schemas import DocumentChunk
from mentormind.core.schemas.vector import VectorChunk
from mentormind.knowledge_base.store.vector_store import VectorStore

DOC_ID = re.compile(r"^DOC-[0-9a-f]{12}$")


@dataclass
class IndexResult:
    upserted: int = 0
    files_ok: int = 0
    #: ``(file name, reason)`` for each file that was rejected whole.
    files_failed: list[tuple[str, str]] = field(default_factory=list)
    #: ``doc_id`` of every document whose file was indexed in this run.
    doc_ids: set[str] = field(default_factory=set)


def to_vector_chunk(chunk: DocumentChunk) -> VectorChunk:
    """Filterable columns stay columns; everything else lands in ``metadata``."""
    return VectorChunk(
        chunk_id=chunk.chunk_id,
        source_type=chunk.source_type,
        ref_id=chunk.doc_id,
        text=chunk.text,
        kind=chunk.kind.value,
        process_ids=chunk.process_ids,
        part_numbers=chunk.part_numbers,
        data_classification=chunk.data_classification,
        metadata={
            "page": chunk.page,
            "title": chunk.title,
            "source_path": chunk.source_path,
            "extractor": chunk.extractor,
            **chunk.metadata,
        },
    )


def index_chunks(chunks_dir: Path, store: VectorStore, *, batch_size: int = 32) -> IndexResult:
    """Upsert every ``*.jsonl`` in ``chunks_dir`` (sorted by name) into ``store``.

    A file is read and validated completely before anything of it is written, so a bad line
    rejects that file only (AC-14). Upserting is by ``chunk_id``: running twice adds nothing (AC-15).

    Raises:
        ValueError: ``batch_size`` is not positive.
        FileNotFoundError: ``chunks_dir`` does not exist.
    """
    if batch_size < 1:
        raise ValueError(f"batch_size phải >= 1, nhận {batch_size}.")
    if not chunks_dir.is_dir():
        raise FileNotFoundError(f"Không thấy thư mục chunk: {chunks_dir}")
    result = IndexResult()
    for path in sorted(chunks_dir.glob("*.jsonl")):
        try:
            chunks = [to_vector_chunk(c) for _, c in read_chunks(path)]
        except ChunkFileError as exc:
            result.files_failed.append((path.name, str(exc)))
            continue
        batches = iter(chunks)
        while batch := list(islice(batches, batch_size)):
            store.upsert(batch)
        result.upserted += len(chunks)
        result.files_ok += 1
        result.doc_ids.update(c.ref_id for c in chunks)
    return result


def replace_docs(store: VectorStore, old_doc_ids: Iterable[str], *, keep: Collection[str]) -> dict[str, int]:
    """Delete the chunks of superseded documents; returns ``{doc_id: chunks removed}``.

    A source file that changed gets a new ``doc_id`` (hash of its bytes), so its old chunks would
    stay searchable next to the new ones. Run this *after* the new chunks are indexed. A ``doc_id``
    in ``keep`` (indexed in the same run) is never deleted.
    """
    return {
        doc_id: 0 if doc_id in keep else store.delete_where({"source_type": "document", "doc_id": doc_id})
        for doc_id in old_doc_ids
    }
