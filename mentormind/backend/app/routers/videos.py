"""Video endpoints (spec 08 §2): upload, process (cut → describe → propose-reasons) and segments.

Spec 03 has no code yet, so processing cuts the video with spec 04's ``fixed_window`` fallback
(``processing.vlm.segments``). When spec 03 lands, only :func:`describe_video`'s cutting step changes.
"""

import re
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, Field

from mentormind.backend.app.deps import get_profile_store
from mentormind.backend.app.uploads import upload_name
from mentormind.core.config import Settings, get_settings
from mentormind.core.schemas import (
    DataClassification,
    JobStatus,
    Segment,
    VideoAsset,
    VideoProcessProgress,
    VideoProcessResult,
)
from mentormind.knowledge_base.store.profile_store import ProfileStore

if TYPE_CHECKING:
    from mentormind.core.providers.vlm import VLMProvider

router = APIRouter(prefix="/videos", tags=["videos"])

VIDEO_SUFFIXES = (".avi", ".m4v", ".mkv", ".mov", ".mp4", ".webm")
VIDEO_ID = re.compile(r"VID-[0-9a-f]{12}")
#: Cutting methods available today: only spec 03's fallback, until spec 03 lands (FR-03).
METHODS = ("fixed_window",)
WINDOW_S = 10.0
DEFAULT_PROCESS_ID = "PACK01"
_CHUNK = 1 << 20


class ProcessVideoRequest(BaseModel):
    method: str = "fixed_window"
    fps: float | None = Field(default=None, gt=0)


@router.post("", response_model=VideoAsset)
async def upload_video(
    file: UploadFile = File(...),
    process_id: str = Form(...),
    # Mandatory like for documents (spec 02 FR-01b): a factory video must never default to a weaker label.
    classification: DataClassification = Form(...),
) -> VideoAsset:
    from mentormind.processing.vlm.segments import probe_video
    from mentormind.processing.vlm.sweep.windows import video_id_for

    suffix = Path(upload_name(file.filename)).suffix.lower()
    if suffix not in VIDEO_SUFFIXES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Định dạng video không hỗ trợ: {suffix or '(không có đuôi)'}. Nhận: {' '.join(VIDEO_SUFFIXES)}.",
        )
    process_id = process_id.strip()
    if not process_id:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Thiếu mã công đoạn.")

    videos = get_settings().work_dir / "video"
    incoming = videos / "_incoming"
    incoming.mkdir(parents=True, exist_ok=True)
    part = incoming / f"{uuid.uuid4().hex}{suffix}"
    try:
        with part.open("wb") as out:
            while chunk := await file.read(_CHUNK):
                out.write(chunk)
        video_id = video_id_for(part)  # same id as `knowhow vlm describe` (spec 03 §3)
        folder = videos / video_id
        folder.mkdir(parents=True, exist_ok=True)
        source = folder / f"source{suffix}"
        part.replace(source)
    finally:
        part.unlink(missing_ok=True)
    try:
        asset = probe_video(source, process_id=process_id, classification=classification, video_id=video_id)
    except ValueError as exc:
        source.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=f"Không đọc được video: {exc}."
        ) from exc
    (folder / "video.json").write_text(asset.model_dump_json(indent=2), encoding="utf-8")
    return asset


@router.post("/{video_id}/process")
def process_video(
    video_id: str,
    req: ProcessVideoRequest,
    background_tasks: BackgroundTasks,
    store: ProfileStore = Depends(get_profile_store),
) -> dict[str, str]:
    if req.method not in METHODS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Chưa hỗ trợ cách cắt {req.method!r} (spec 03 chưa có); dùng: {', '.join(METHODS)}.",
        )
    settings = get_settings()
    asset = _uploaded(settings, video_id)
    job_id = f"job-vid-{uuid.uuid4().hex[:8]}"
    store.create_job(job_id, "video_process")
    background_tasks.add_task(run_video_process_task, job_id, asset, req.fps, settings, store)
    return {"job_id": job_id}


@router.get("/{video_id}/segments", response_model=list[Segment])
def get_segments(video_id: str) -> list[Segment]:
    from mentormind.processing.vlm.segments import read_segments, segments_path

    if not VIDEO_ID.fullmatch(video_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Không có video {video_id}.")
    try:
        return read_segments(segments_path(get_settings().work_dir, video_id))
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Video {video_id} chưa được cắt đoạn (chưa xử lý)."
        ) from exc


def run_video_process_task(
    job_id: str, asset: VideoAsset, fps: float | None, settings: Settings, store: ProfileStore
) -> None:
    """The background job of ``POST /videos/{id}/process``; any error ends it ``failed`` (AC-05)."""
    store.update_job(job_id, JobStatus.RUNNING)

    def report(progress: VideoProcessResult) -> None:
        store.update_job(job_id, JobStatus.RUNNING, result=progress.model_dump(mode="json"))

    try:
        result = describe_video(asset, fps=fps, settings=settings, report=report)
    except Exception as exc:
        store.update_job(job_id, JobStatus.FAILED, error=str(exc) or type(exc).__name__)
        return
    store.update_job(job_id, JobStatus.DONE, result=result.model_dump(mode="json"))


def describe_video(
    asset: VideoAsset,
    *,
    fps: float | None,
    settings: Settings,
    report: Callable[[VideoProcessResult], None],
) -> VideoProcessResult:
    """Cut, describe (passes A, B, C) and save draft profiles; propose reasons when a transcript exists.

    Same steps as ``knowhow vlm describe --video`` then ``propose-reasons`` (spec 04 FR-05).
    """
    from mentormind.core.guard import DataGuard
    from mentormind.core.providers.llm import get_llm_provider
    from mentormind.core.providers.vlm import get_vlm_provider
    from mentormind.processing.vlm.passes.reasons import propose_reasons
    from mentormind.processing.vlm.pipeline import DescribePipeline
    from mentormind.processing.vlm.profiles import FileProfileSink, get_profile_sink
    from mentormind.processing.vlm.segments import cut_fixed_windows
    from mentormind.processing.vlm.transcript import load_transcript

    work = settings.work_dir
    sink = get_profile_sink(settings, work_dir=work)
    vlm = get_vlm_provider(settings)
    llm = get_llm_provider(settings)
    # Before cutting or calling anything: this label may not reach a cloud provider (constitution art. 2).
    DataGuard.check(asset.data_classification, vlm)
    DataGuard.check(asset.data_classification, llm)

    process_id = asset.process_id or DEFAULT_PROCESS_ID
    segments = cut_fixed_windows(
        Path(asset.path), work_dir=work, classification=asset.data_classification, window_s=WINDOW_S
    )
    transcript = load_transcript(work, asset.video_id)
    result = VideoProcessResult(
        video_id=asset.video_id, process_id=process_id, segments=len(segments), transcript_lines=len(transcript)
    )
    total = 2 * len(segments)  # passes A and B: one VLM call per segment each

    def progress(done: int) -> None:
        result.progress = VideoProcessProgress(done=min(done, total), total=total)
        report(result)

    progress(0)
    _on_each_call(vlm, progress)
    pipeline = DescribePipeline(
        vlm, llm=llm, process_id=process_id, default_fps=fps or settings.vlm_fps, max_frames=settings.vlm_max_frames
    )
    described = pipeline.run(segments, work / "vlm" / asset.video_id / f"describe-{vlm.name}", transcript)
    stored = sink.save(asset.video_id, described.profiles)
    result.profiles = [p.profile_id for p in stored]
    result.failed_segments = described.failed_segments
    if any(p.evidence.transcript_excerpt and p.reason is None for p in stored):
        updated = propose_reasons(stored, llm)
        changed = [new for old, new in zip(stored, updated, strict=True) if old.reason != new.reason]
        if changed:
            # As `knowhow vlm propose-reasons`: the file sink rewrites the video, the store only what changed.
            sink.save(asset.video_id, updated if isinstance(sink, FileProfileSink) else changed)
        result.reasons_filled = len(changed)
    return result


def _uploaded(settings: Settings, video_id: str) -> VideoAsset:
    path = settings.work_dir / "video" / video_id / "video.json"
    if not VIDEO_ID.fullmatch(video_id) or not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Video {video_id} chưa được tải lên.")
    return VideoAsset.model_validate_json(path.read_text(encoding="utf-8"))


def _on_each_call(vlm: "VLMProvider", callback: Callable[[int], None]) -> None:
    """Call ``callback(n)`` after the n-th ``generate`` of this provider instance (job progress)."""
    generate = vlm.generate
    calls = 0

    def counted(*args: Any, **kwargs: Any) -> Any:
        nonlocal calls
        response = generate(*args, **kwargs)
        calls += 1
        callback(calls)
        return response

    setattr(vlm, "generate", counted)  # this instance only: get_vlm_provider builds a new one per call
