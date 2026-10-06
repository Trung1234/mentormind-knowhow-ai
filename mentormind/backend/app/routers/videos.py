"""Video endpoints (spec 08 §2): upload, process (cut → describe → propose-reasons) and segments.

Cutting, keyframes, clips and the transcript are spec 03's ``VideoCapturePipeline``.
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
from mentormind.capture.video.segmenters import METHODS, Method
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
    from mentormind.capture.video import VideoCapturePipeline
    from mentormind.core.providers.vlm import VLMProvider
    from mentormind.core.schemas.api import VideoStage

router = APIRouter(prefix="/videos", tags=["videos"])

VIDEO_SUFFIXES = (".avi", ".m4v", ".mkv", ".mov", ".mp4", ".webm")
VIDEO_ID = re.compile(r"VID-[0-9a-f]{12}")
WINDOW_S = 10.0
DEFAULT_PROCESS_ID = "PACK01"
_CHUNK = 1 << 20


class ProcessVideoRequest(BaseModel):
    #: Spec 03 FR-03: hand_activity | scene | fixed_window; a missing library falls back down the chain.
    method: str = "hand_activity"
    fps: float | None = Field(default=None, gt=0)


@router.post("", response_model=VideoAsset)
async def upload_video(
    file: UploadFile = File(...),
    process_id: str = Form(...),
    # Mandatory like for documents (spec 02 FR-01b): a factory video must never default to a weaker label.
    classification: DataClassification = Form(...),
) -> VideoAsset:
    from mentormind.capture.video.probe import probe_video, video_id_for

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
            detail=f"Không có cách cắt {req.method!r}; chọn một trong: {', '.join(METHODS)}.",
        )
    settings = get_settings()
    asset = _uploaded(settings, video_id)
    job_id = f"job-vid-{uuid.uuid4().hex[:8]}"
    store.create_job(job_id, "video_process")
    background_tasks.add_task(run_video_process_task, job_id, asset, req.method, req.fps, settings, store)
    return {"job_id": job_id}


@router.get("/{video_id}/segments", response_model=list[Segment])
def get_segments(video_id: str) -> list[Segment]:
    from mentormind.capture.video.store import read_segments, segments_path

    if not VIDEO_ID.fullmatch(video_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Không có video {video_id}.")
    try:
        return read_segments(segments_path(get_settings().work_dir, video_id))
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Video {video_id} chưa được cắt đoạn (chưa xử lý)."
        ) from exc


def run_video_process_task(
    job_id: str, asset: VideoAsset, method: Method, fps: float | None, settings: Settings, store: ProfileStore
) -> None:
    """The background job of ``POST /videos/{id}/process``; any error ends it ``failed`` (AC-05)."""
    store.update_job(job_id, JobStatus.RUNNING)

    def report(progress: VideoProcessResult) -> None:
        store.update_job(job_id, JobStatus.RUNNING, result=progress.model_dump(mode="json"))

    try:
        result = describe_video(asset, method=method, fps=fps, settings=settings, report=report)
    except Exception as exc:
        store.update_job(job_id, JobStatus.FAILED, error=str(exc) or type(exc).__name__)
        return
    store.update_job(job_id, JobStatus.DONE, result=result.model_dump(mode="json"))


def capture_pipeline(settings: Settings) -> "VideoCapturePipeline":
    """Spec 03's pipeline as the API runs it (tests put fake detectors and a fake ASR here)."""
    from mentormind.capture.video import VideoCapturePipeline

    return VideoCapturePipeline(settings, window_s=WINDOW_S)


def describe_video(
    asset: VideoAsset,
    *,
    method: Method,
    fps: float | None,
    settings: Settings,
    report: Callable[[VideoProcessResult], None],
) -> VideoProcessResult:
    """Cut and transcribe (spec 03), describe (spec 04 passes A, B, C), save drafts, propose reasons.

    Same steps as ``knowhow video segment`` + ``transcribe``, then ``knowhow vlm describe`` and
    ``propose-reasons``; ``report`` gets the result so far with the stage it is in (spec 08 §2).
    """
    from mentormind.core.guard import DataGuard
    from mentormind.core.providers.llm import get_llm_provider
    from mentormind.core.providers.vlm import get_vlm_provider
    from mentormind.processing.vlm.passes.reasons import propose_reasons
    from mentormind.processing.vlm.pipeline import DescribePipeline
    from mentormind.processing.vlm.profiles import FileProfileSink, get_profile_sink

    work = settings.work_dir
    sink = get_profile_sink(settings, work_dir=work)
    vlm = get_vlm_provider(settings)
    llm = get_llm_provider(settings)
    # Before cutting or calling anything: this label may not reach a cloud provider (constitution art. 2).
    DataGuard.check(asset.data_classification, vlm)
    DataGuard.check(asset.data_classification, llm)

    process_id = asset.process_id or DEFAULT_PROCESS_ID
    result = VideoProcessResult(video_id=asset.video_id, process_id=process_id, method=method)

    def stage(name: "VideoStage", done: float, total: float) -> None:
        result.progress = VideoProcessProgress(stage=name, done=round(min(done, total), 1), total=round(total, 1))
        report(result)

    captured = capture_pipeline(settings).run(
        Path(asset.path),
        work_dir=work,
        process_id=process_id,
        classification=asset.data_classification,
        method=method,
        transcribe=True,
        video_id=asset.video_id,
        progress=stage,
    )
    result.method_used = captured.method_used
    result.segments = len(captured.segments)
    result.transcript_lines = len(captured.transcript)

    calls = 2 * len(captured.segments)  # passes A and B: one VLM call per segment each

    def described(done: int) -> None:
        stage("describe", done, calls)
        if done >= calls:
            stage("merge", 0, 1)  # pass C, one LLM call, comes next

    stage("describe", 0, calls)
    _on_each_call(vlm, described)
    pipeline = DescribePipeline(
        vlm,
        llm=llm,
        process_id=process_id,
        default_fps=fps or settings.vlm_fps,
        max_frames=settings.vlm_max_frames,
        transcript_lead_s=settings.transcript_lead_s,
        transcript_lag_s=settings.transcript_lag_s,
    )
    work_dir = work / "vlm" / asset.video_id / f"describe-{vlm.name}"
    drafts = pipeline.run(captured.segments, work_dir, captured.transcript)
    stored = sink.save(asset.video_id, drafts.profiles)
    result.profiles = [p.profile_id for p in stored]
    result.failed_segments = drafts.failed_segments

    quoting = [p for p in stored if p.evidence.transcript_excerpt]
    result.steps_with_excerpt = len(quoting)
    waiting = [p for p in quoting if p.reason is None]
    proposed = {}
    for done, profile in enumerate(waiting):
        stage("reasons", done, len(waiting))
        [after] = propose_reasons([profile], llm)
        if after.reason != profile.reason:
            proposed[after.profile_id] = after
    if proposed:
        # As `knowhow vlm propose-reasons`: the file sink rewrites the video, the store only what changed.
        everything = [proposed.get(p.profile_id, p) for p in stored]
        sink.save(asset.video_id, everything if isinstance(sink, FileProfileSink) else list(proposed.values()))
    if waiting:
        stage("reasons", len(waiting), len(waiting))
    result.reasons_filled = len(proposed)
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
