from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from mentormind.backend.app.deps import get_profile_store
from mentormind.core.schemas import (
    ProfilePatchRequest,
    ReviewAction,
    ReviewRequest,
    WorkProfile,
)
from mentormind.knowledge_base.store.profile_store import ProfileStore

router = APIRouter(prefix="/profiles", tags=["profiles"])


def hook_on_profile_approved(profile: WorkProfile) -> None:
    """Hook to notify Knowledge Graph when a profile is approved (Spec 08 §2)."""
    try:
        # If knowledge_base.kg exists, import and load
        from mentormind.knowledge_base import kg  # type: ignore

        if hasattr(kg, "load_profiles"):
            kg.load_profiles([profile])
    except ImportError:
        pass


def hook_on_profile_unloaded(profile: WorkProfile) -> None:
    """Hook to notify Knowledge Graph when an approved profile is rejected (Spec 08 §2)."""
    try:
        from mentormind.knowledge_base import kg  # type: ignore

        if hasattr(kg, "unload_profile"):
            kg.unload_profile(profile.profile_id)
    except ImportError:
        pass


@router.get("", response_model=List[WorkProfile])
def list_profiles(
    process_id: Optional[str] = Query(default=None, description="Mã công đoạn"),
    status: Optional[str] = Query(default=None, description="Trạng thái (draft, in_review, approved, rejected)"),
    store: ProfileStore = Depends(get_profile_store),
) -> List[WorkProfile]:
    return store.list_profiles(process_id=process_id, status=status)


@router.get("/{profile_id}")
def get_profile(
    profile_id: str,
    store: ProfileStore = Depends(get_profile_store),
) -> Dict[str, Any]:
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
) -> WorkProfile:
    existing = store.get_profile(profile_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"WorkProfile {profile_id} không tồn tại",
        )

    was_approved = existing.status.value == "approved"

    try:
        updated = store.record_review(profile_id, review_req)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )

    if review_req.action == ReviewAction.APPROVE:
        hook_on_profile_approved(updated)
    elif review_req.action == ReviewAction.REJECT and was_approved:
        hook_on_profile_unloaded(updated)

    return updated
