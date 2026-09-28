from fastapi import APIRouter, Depends, HTTPException, status

from mentormind.backend.app.deps import get_profile_store
from mentormind.core.schemas import JobResponse
from mentormind.knowledge_base.store.profile_store import ProfileStore

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/{job_id}", response_model=JobResponse)
def get_job(
    job_id: str,
    store: ProfileStore = Depends(get_profile_store),
) -> JobResponse:
    job = store.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} không tồn tại",
        )
    return job
