from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from mentormind.backend.app.deps import get_knowledge_loader, get_profile_store
from mentormind.core.schemas import (
    ProfilePatchRequest,
    ReviewAction,
    ReviewRequest,
    WorkProfile,
)
from mentormind.knowledge_base.kg.loader import KnowledgeGraphLoader
from mentormind.knowledge_base.store.profile_store import ProfileStore

router = APIRouter(prefix="/profiles", tags=["profiles"])


@router.get("", response_model=list[WorkProfile])
def list_profiles(
    process_id: str | None = Query(default=None, description="Mã công đoạn"),
    status: str | None = Query(default=None, description="Trạng thái (draft, in_review, approved, rejected)"),
    store: ProfileStore = Depends(get_profile_store),
) -> list[WorkProfile]:
    return store.list_profiles(process_id=process_id, status=status)


@router.get("/{profile_id}")
def get_profile(
    profile_id: str,
    store: ProfileStore = Depends(get_profile_store),
) -> dict[str, Any]:
    res = store.get_profile_with_reviews(profile_id)
    if not res:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"WorkProfile {profile_id} không tồn tại",
        )
    return res


@router.patch("/{profile_id}", response_model=WorkProfile)
def patch_profile(
    profile_id: str,
    patch_req: ProfilePatchRequest,
    store: ProfileStore = Depends(get_profile_store),
) -> WorkProfile:
    try:
        return store.patch_profile(profile_id, patch_req)
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"WorkProfile {profile_id} không tồn tại",
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )


@router.post("/{profile_id}/review", response_model=WorkProfile)
def review_profile(
    profile_id: str,
    review_req: ReviewRequest,
    store: ProfileStore = Depends(get_profile_store),
    loader: KnowledgeGraphLoader = Depends(get_knowledge_loader),
) -> WorkProfile:
    existing = store.get_profile(profile_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"WorkProfile {profile_id} không tồn tại",
        )

    def publish(profile: WorkProfile) -> None:
        if review_req.action == ReviewAction.APPROVE:
            loader.load_profiles([profile])
        else:
            loader.unload_profile(profile.profile_id)

    def rollback_publish(profile: WorkProfile) -> None:
        if review_req.action == ReviewAction.APPROVE:
            loader.unload_profile(profile.profile_id)
        elif str(getattr(existing.status, "value", existing.status)) == "approved":
            loader.load_profiles([existing])

    try:
        updated = store.record_review(profile_id, review_req, before_save=publish,
                                      rollback_publish=rollback_publish)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )

    return updated
