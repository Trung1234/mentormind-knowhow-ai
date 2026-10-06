import uuid
from collections import Counter
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel

from mentormind.backend.app.deps import get_profile_store
from mentormind.capture.ingest import cli as ingest_cli
from mentormind.capture.ingest.index import index_files
from mentormind.capture.ingest.pipeline import IngestResult, ingest_path
from mentormind.core.config import Settings, get_settings
from mentormind.core.schemas import DataClassification, DocumentIngestFile, DocumentIngestResult, JobStatus
from mentormind.knowledge_base.store.profile_store import ProfileStore

router = APIRouter(tags=["ingest"])


class VideoAsset(BaseModel):
    video_id: str
    filename: str
    process_id: str
    classification: str
    path: str


class ProcessVideoRequest(BaseModel):
    method: str | None = "heuristic"
    fps: float | None = 4.0


def run_document_ingest_task(
    job_id: str,
    upload_dir: Path,
    classification: DataClassification,
    settings: Settings,
    store: ProfileStore,
) -> None:
    """Spec 02 ``ingest run`` on one upload, then ``ingest index`` of only the chunk files it wrote.

    Chunks go to ``<work_dir>/chunks`` like the CLI's, so ``knowhow ingest index`` sees them too.
    One bad file never stops the others; the job fails when no file gave chunks or indexing fails
    (AC-12), and an error never takes the server down.
    """
    store.update_job(job_id, JobStatus.RUNNING)
    result = DocumentIngestResult(classification=classification)
    try:
        vectors = ingest_cli.build_store(settings)  # before the slow extraction: fail fast if unreachable
        chunks_dir = settings.work_dir / "chunks"
        ingested = ingest_path(
            upload_dir,
            classification,
            chunks_dir,
            extractors=ingest_cli.build_extractors(settings),
            counter=ingest_cli.build_counter(settings),
            settings=settings,
        )
        result.files = [_file_result(r) for r in ingested]
        # A dict, not a list: identical files share one doc_id, hence one chunk file.
        written = dict.fromkeys(chunks_dir / f"{r.doc_id}.jsonl" for r in ingested if r.chunks)
        if not written:
            raise RuntimeError("Không tệp nào tách được chunk — " + "; ".join(map(_why_no_chunks, result.files)))
        indexed = index_files(written, vectors)
        result.chunks_indexed = indexed.upserted
        if indexed.files_failed:
            raise RuntimeError("Lỗi index: " + "; ".join(why for _, why in indexed.files_failed))
    except Exception as exc:
        store.update_job(
            job_id, JobStatus.FAILED, result=result.model_dump(mode="json"), error=str(exc) or type(exc).__name__
        )
        return
    store.update_job(job_id, JobStatus.DONE, result=result.model_dump(mode="json"))


def _file_result(r: IngestResult) -> DocumentIngestFile:
    return DocumentIngestFile(
        name=Path(r.path).name,
        doc_id=r.doc_id,
        extractor=r.extractor,
        pages=r.pages,
        chunks=r.chunks,
        skipped=r.skipped,
        error=r.error,
    )


def _why_no_chunks(f: DocumentIngestFile) -> str:
    if f.error is None:
        return f"{f.name}: định dạng không hỗ trợ"
    # Extractor errors already start with the file name.
    return f.error if f.error.startswith(f.name) else f"{f.name}: {f.error}"


def run_video_process_task(job_id: str, video_id: str, fps: float, store: ProfileStore) -> None:
    store.update_job(job_id, JobStatus.RUNNING)
    try:
        result = {
            "video_id": video_id,
            "segments_count": 4,
            "profiles_generated": 4,
        }
        store.update_job(job_id, JobStatus.DONE, result=result)
    except Exception as e:
        store.update_job(job_id, JobStatus.FAILED, error=str(e))


@router.post("/ingest/documents")
async def ingest_documents(
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(...),
    # Spec 02 FR-01b: the label is mandatory, never defaulted (AC-11).
    classification: DataClassification = Form(...),
    store: ProfileStore = Depends(get_profile_store),
) -> dict[str, str]:
    names = [_upload_name(file.filename) for file in files]
    duplicates = sorted(name for name, count in Counter(names).items() if count > 1)
    if duplicates:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Trùng tên tệp trong cùng một lần tải lên: {', '.join(duplicates)}.",
        )

    settings = get_settings()
    job_id = f"job-doc-{uuid.uuid4().hex[:8]}"
    upload_dir = settings.work_dir / "docs" / job_id
    upload_dir.mkdir(parents=True)
    for name, file in zip(names, files, strict=True):
        (upload_dir / name).write_bytes(await file.read())
    store.create_job(job_id, "document_ingest")

    background_tasks.add_task(run_document_ingest_task, job_id, upload_dir, classification, settings, store)

    return {"job_id": job_id}


def _upload_name(filename: str | None) -> str:
    """The base name of an uploaded file; directory parts (``../``, ``/``, ``\\``) are dropped (AC-10)."""
    name = Path((filename or "").replace("\\", "/")).name
    if name in ("", ".", ".."):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Tên tệp không hợp lệ: {filename!r}.",
        )
    return name


@router.post("/videos", response_model=VideoAsset)
async def upload_video(
    file: UploadFile = File(...),
    process_id: str = Form(...),
    classification: DataClassification = Form(DataClassification.SYNTHETIC),
) -> VideoAsset:
    video_id = f"VID-{process_id}-{uuid.uuid4().hex[:6].upper()}"
    settings = get_settings()
    video_dir = Path(settings.work_dir) / "video"
    video_dir.mkdir(parents=True, exist_ok=True)

    ext = Path(file.filename).suffix if file.filename else ".mp4"
    filename = f"{video_id}{ext}"
    dest_path = video_dir / filename

    with open(dest_path, "wb") as f:
        content = await file.read()
        f.write(content)

    return VideoAsset(
        video_id=video_id,
        filename=filename,
        process_id=process_id,
        classification=classification.value,
        path=f"data/work/video/{filename}",
    )


@router.post("/videos/{video_id}/process")
def process_video(
    video_id: str,
    req: ProcessVideoRequest,
    background_tasks: BackgroundTasks,
    store: ProfileStore = Depends(get_profile_store),
) -> dict[str, str]:
    job_id = f"job-vid-{uuid.uuid4().hex[:8]}"
    store.create_job(job_id, "video_process")

    background_tasks.add_task(
        run_video_process_task,
        job_id,
        video_id,
        req.fps or 4.0,
        store,
    )

    return {"job_id": job_id}
