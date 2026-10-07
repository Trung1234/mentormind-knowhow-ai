"""Deleting steps from the UI (spec 08 §2 "Xoá dữ liệu", AC-19..AC-22).

A step that reached the knowledge graph is unloaded first (spec 05 FR-04: its ``Step`` and its
pgvector chunk) and only then removed from the profile store, so the store never forgets a step
the graph still serves. A step that never reached the graph is only removed from the store:
Neo4j and pgvector are not even opened, so deleting drafts works while they are down.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from contextlib import AbstractContextManager
from typing import Protocol

from mentormind.core.schemas import DeleteFailure, ProfileDeleteResult, WorkProfile
from mentormind.knowledge_base.store.profile_store import ProfileStore


class Unloader(Protocol):
    """The part of ``KnowledgeGraphLoader`` deletion needs."""

    def unload_profile(self, profile_id: str) -> None: ...


UnloaderOpener = Callable[[], AbstractContextManager[Unloader]]


def is_published(store: ProfileStore, profile: WorkProfile) -> bool:
    """In the graph: approved, or approved then edited (``in_review`` keeps the old version, AC-01)."""
    return profile.status == "approved" or store.last_review_action(profile.profile_id) == "approve"


def delete_profiles(
    store: ProfileStore, profiles: Sequence[WorkProfile], open_loader: UnloaderOpener
) -> ProfileDeleteResult:
    """Delete ``profiles``; a published one whose unloading fails is kept and listed in ``failed``."""
    published = [p.profile_id for p in profiles if is_published(store, p)]
    unloaded, failed = _unload(published, open_loader) if published else ([], [])
    kept = {f.profile_id for f in failed}
    removable = [p.profile_id for p in profiles if p.profile_id not in kept]
    store.delete_profiles(removable)
    return ProfileDeleteResult(deleted=removable, unpublished=unloaded, failed=failed)


def _unload(profile_ids: list[str], open_loader: UnloaderOpener) -> tuple[list[str], list[DeleteFailure]]:
    done: list[str] = []
    errors: dict[str, str] = {}
    try:
        with open_loader() as loader:
            for profile_id in profile_ids:
                try:
                    loader.unload_profile(profile_id)
                except Exception as exc:  # the loader restores what it had touched (spec 05 FR-04)
                    errors[profile_id] = _why(exc)
                else:
                    done.append(profile_id)
    except Exception as exc:  # Neo4j or pgvector unreachable: whatever was not unloaded stays
        for profile_id in profile_ids:
            if profile_id not in done:
                errors.setdefault(profile_id, _why(exc))
    return done, [DeleteFailure(profile_id=p, error=errors[p]) for p in profile_ids if p in errors]


def _why(exc: Exception) -> str:
    return f"chưa gỡ được khỏi đồ thị tri thức / kho vector ({str(exc) or type(exc).__name__})"
