import os
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel

from mentormind.backend.app.config import get_settings
from mentormind.backend.app.deps import get_profile_store
from mentormind.core.schemas import DataClassification, JobStatus
from mentormind.knowledge_base.store.profile_store import ProfileStore

router = APIRouter(tags=["ingest"])


class VideoAsset(BaseModel):
    video_id: str
    filename: str
    process_id: str
    classification: str
    path: str


class ProcessVideoRequest(BaseModel):
    method: Optional[str] = "heuristic"
    fps: Optional[float] = 4.0


def run_document_ingest_task(job_id: str, file_paths: List[str], classification: str, store: ProfileStore) -> None:
    store.update_job(job_id, JobStatus.RUNNING)
    try:
        # In demo / offline mode, perform mock or call ingest runner if available
        result = {
            "processed_files": len(file_paths),
            "chunks_created": len(file_paths) * 3,
            "classification": classification,
        }
        store.update_job(job_id, JobStatus.DONE, result=result)
    except Exception as e:
        store.update_job(job_id, JobStatus.FAILED, error=str(e))


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
    files: List[UploadFile] = File(...),
    classification: DataClassification = Form(DataClassification.SYNTHETIC),
    store: ProfileStore = Depends(get_profile_store),
) -> Dict[str, str]:
    job_id = f"job-doc-{uuid.uuid4().hex[:8]}"
    store.create_job(job_id, "document_ingest")

    settings = get_settings()
    doc_dir = Path(settings.work_dir) / "docs"
    doc_dir.mkdir(parents=True, exist_ok=True)

    saved_paths = []
    for file in files:
        if file.filename:
            save_path = doc_dir / file.filename
            with open(save_path, "wb") as f:
                content = await file.read()
                f.write(content)
            saved_paths.append(str(save_path))

    background_tasks.add_task(
        run_document_ingest_task,
        job_id,
        saved_paths,
        classification.value,
        store,
    )

    return {"job_id": job_id}


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
) -> Dict[str, str]:
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
