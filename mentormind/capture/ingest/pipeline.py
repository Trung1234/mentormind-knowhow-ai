"""Ingest one file or a folder into chunk files (spec 02 FR-01, FR-06, FR-08)."""

from __future__ import annotations

import hashlib
import logging
import time
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import ValidationError

from mentormind.capture.ingest.chunker import chunk_document
from mentormind.capture.ingest.extractors.base import Extractor, ExtractorError
from mentormind.capture.ingest.jsonl import ChunkFileError, read_chunks, write_chunks_atomic
from mentormind.capture.ingest.quality import suspect_pages
from mentormind.capture.ingest.select import extract_with_fallback
from mentormind.capture.ingest.tokens import TokenCounter
from mentormind.core.config import Settings
from mentormind.core.guard.data_guard import DataGuard
from mentormind.core.schemas import DataClassification

logger = logging.getLogger(__name__)

SUPPORTED_SUFFIXES = frozenset({".pdf", ".docx", ".xlsx", ".pptx"})
_HASH_BLOCK = 1 << 20


class ClassificationMismatchError(ValueError):
    """The output already exists with another classification (never downgrade silently)."""


class _LocalProvider:
    """Extraction and embedding run on this machine, so nothing here is a cloud provider."""

    name = "local-ingest"
    is_cloud = False


@dataclass
class IngestResult:
    path: str
    doc_id: str | None = None
    extractor: str | None = None
    pages: int = 0
    chunks: int = 0
    seconds: float = 0.0
    skipped: bool = False
    error: str | None = None
    #: Why earlier extractors were passed over (FR-08 log).
    reasons: list[str] = field(default_factory=list)
    #: Pages whose text layer looks mis-encoded (FR-02b); chunked anyway, listed for a human to check.
    suspect_pages: list[int] = field(default_factory=list)


def doc_id_for(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(_HASH_BLOCK):
            digest.update(block)
    return "DOC-" + digest.hexdigest()[:12]


def ingest_file(
    path: Path,
    classification: DataClassification,
    out_dir: Path,
    *,
    extractors: Sequence[Extractor],
    counter: TokenCounter,
    settings: Settings,
    force: bool = False,
) -> IngestResult:
    """Extract, chunk and write ``<out_dir>/<doc_id>.jsonl``; failures are returned, not raised.

    Running again on the same bytes rewrites identical output (same ``doc_id``, ``chunk_id``, order).
    """
    result = IngestResult(path=str(path))
    if path.suffix.lower() not in SUPPORTED_SUFFIXES:
        result.skipped = True
        logger.info("skipped %s: định dạng %s không được hỗ trợ", path, path.suffix or "(không đuôi)")
        return result
    started = time.perf_counter()
    try:
        result.doc_id = doc_id_for(path)
        out = out_dir / f"{result.doc_id}.jsonl"
        if not force:
            _check_label_unchanged(out, classification)
        raw, result.reasons = extract_with_fallback(path, extractors)
        chunks = chunk_document(
            raw, doc_id=result.doc_id, classification=classification, counter=counter, settings=settings
        )
        result.suspect_pages = suspect_pages(raw, max_ratio=settings.text_quality_max_odd_ratio)
        if not chunks:
            raise ExtractorError(f"{path.name}: không sinh được chunk nào.")
        write_chunks_atomic(out, chunks)
        result.extractor, result.pages, result.chunks = raw.extractor, raw.num_pages, len(chunks)
    except (ExtractorError, ClassificationMismatchError, OSError) as exc:
        result.error = str(exc)
    except ValidationError as exc:  # an extractor handed over something that is not a valid chunk
        result.error = f"{path.name}: chunk không hợp lệ — {exc.errors()[0]['msg']}"
    result.seconds = time.perf_counter() - started
    return result


def ingest_path(
    input_: Path,
    classification: DataClassification,
    out_dir: Path,
    *,
    extractors: Sequence[Extractor],
    counter: TokenCounter,
    settings: Settings,
    force: bool = False,
) -> list[IngestResult]:
    """Ingest a file or every file under a folder (sorted, so runs are reproducible).

    Raises:
        FileNotFoundError: ``input_`` does not exist.
        ConfidentialDataError: DataGuard refuses ``classification`` for the local provider.
    """
    if not input_.exists():
        raise FileNotFoundError(f"Không thấy đường dẫn đầu vào: {input_}")
    DataGuard.check(classification, _LocalProvider())
    files = [input_] if input_.is_file() else sorted(p for p in input_.rglob("*") if p.is_file())
    return [
        ingest_file(f, classification, out_dir, extractors=extractors, counter=counter, settings=settings, force=force)
        for f in files
    ]


def _check_label_unchanged(out: Path, wanted: DataClassification) -> None:
    if not out.exists():
        return
    try:
        _, first = next(read_chunks(out))
    except (StopIteration, ChunkFileError):
        return  # unreadable or empty output carries no label to protect: rewrite it
    if first.data_classification is not wanted:
        raise ClassificationMismatchError(
            f"{out.name} đã có nhãn {first.data_classification.value}, không đổi sang {wanted.value} "
            "khi chưa có --force."
        )
