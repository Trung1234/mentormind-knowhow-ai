"""Profile Store implementation using SQLite.

Spec: docs/08-api-and-ui.md Section 1
Tables:
- profiles (profile_id, process_id, status, version, data_json, updated_at)
- review_events (id, profile_id, action, reviewer, comment, error_tags, created_at)
- jobs (job_id, kind, status, result_json, error, created_at, finished_at)
"""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import jsonschema

from mentormind.core.schemas import (
    ErrorTag,
    JobResponse,
    JobStatus,
    ProfilePatchRequest,
    ProfileStatus,
    ReviewAction,
    ReviewRequest,
    WorkProfile,
)

SCHEMA_FILE = Path(__file__).resolve().parents[3] / "docs" / "contracts" / "work_profile.schema.json"


def get_contract_schema() -> dict | None:
    if SCHEMA_FILE.exists():
        try:
            with open(SCHEMA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None
    return None


CONTRACT_SCHEMA = get_contract_schema()


def validate_against_contract(data: dict) -> None:
    """Validate raw dict against JSON Schema contract if available."""
    if CONTRACT_SCHEMA:
        jsonschema.validate(instance=data, schema=CONTRACT_SCHEMA)


class ProfileStore:
    def __init__(self, db_path: str = "data/work/profiles.sqlite"):
        self.db_path = db_path
        self._ensure_dir()
        self.init_db()

    def _ensure_dir(self) -> None:
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS profiles (
                    profile_id TEXT PRIMARY KEY,
                    process_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    data_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS review_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    profile_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    reviewer TEXT NOT NULL,
                    comment TEXT,
                    error_tags TEXT,
                    created_at TEXT NOT NULL
                );
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    job_id TEXT PRIMARY KEY,
                    kind TEXT NOT NULL,
                    status TEXT NOT NULL,
                    result_json TEXT,
                    error TEXT,
                    created_at TEXT,
                    finished_at TEXT
                );
                """
            )
            conn.commit()

    def save_profile(self, profile: WorkProfile) -> WorkProfile:
        data_dict = profile.model_dump(mode="json")
        validate_against_contract(data_dict)

        updated_at = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO profiles (profile_id, process_id, status, version, data_json, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(profile_id) DO UPDATE SET
                    process_id=excluded.process_id,
                    status=excluded.status,
                    version=excluded.version,
                    data_json=excluded.data_json,
                    updated_at=excluded.updated_at;
                """,
                (
                    profile.profile_id,
                    profile.process_id,
                    profile.status.value if isinstance(profile.status, ProfileStatus) else profile.status,
                    profile.version,
                    json.dumps(data_dict, ensure_ascii=False),
                    updated_at,
                ),
            )
            conn.commit()
        return profile

    def get_profile(self, profile_id: str) -> WorkProfile | None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT data_json FROM profiles WHERE profile_id = ?", (profile_id,))
            row = cursor.fetchone()
            if not row:
                return None
            data = json.loads(row["data_json"])
            return WorkProfile.model_validate(data)

    def get_profile_with_reviews(self, profile_id: str) -> dict[str, Any] | None:
        profile = self.get_profile(profile_id)
        if not profile:
            return None

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, profile_id, action, reviewer, comment, error_tags, created_at
                FROM review_events
                WHERE profile_id = ?
                ORDER BY id ASC;
                """,
                (profile_id,),
            )
            rows = cursor.fetchall()
            reviews = []
            for r in rows:
                reviews.append(
                    {
                        "id": r["id"],
                        "profile_id": r["profile_id"],
                        "action": r["action"],
                        "reviewer": r["reviewer"],
                        "comment": r["comment"],
                        "error_tags": json.loads(r["error_tags"]) if r["error_tags"] else [],
                        "created_at": r["created_at"],
                    }
                )

        return {
            "profile": profile,
            "reviews": reviews,
        }

    def list_profiles(
        self, process_id: str | None = None, status: str | None = None
    ) -> list[WorkProfile]:
        query = "SELECT data_json FROM profiles WHERE 1=1"
        params: list[Any] = []

        if process_id:
            query += " AND process_id = ?"
            params.append(process_id)
        if status:
            query += " AND status = ?"
            params.append(status)

        query += " ORDER BY process_id, profile_id"

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [WorkProfile.model_validate(json.loads(r["data_json"])) for r in rows]

    def patch_profile(self, profile_id: str, patch_data: ProfilePatchRequest) -> WorkProfile:
        existing = self.get_profile(profile_id)
        if not existing:
            raise KeyError(f"Profile {profile_id} not found")

        # Disallow editing profile_id, generated_by, created_at
        current_dict = existing.model_dump(mode="json")
        patch_dict = patch_data.model_dump(exclude_unset=True, mode="json")

        for key, val in patch_dict.items():
            if val is not None:
                current_dict[key] = val

        # Spec 08 §1: Sửa nội dung profile -> version += 1, status = "in_review"
        current_dict["version"] = existing.version + 1
        current_dict["status"] = ProfileStatus.IN_REVIEW.value

        updated_profile = WorkProfile.model_validate(current_dict)
        return self.save_profile(updated_profile)

    def record_review(
        self,
        profile_id: str,
        review_req: ReviewRequest,
    ) -> WorkProfile:
        existing = self.get_profile(profile_id)
        if not existing:
            raise KeyError(f"Profile {profile_id} not found")

        now_str = datetime.now(timezone.utc).isoformat()
        current_dict = existing.model_dump(mode="json")

        if review_req.action == ReviewAction.REJECT:
            if not (review_req.comment and review_req.comment.strip()):
                raise ValueError("Từ chối (reject) bắt buộc phải nhập lý do.")
            current_dict["status"] = ProfileStatus.REJECTED.value
        elif review_req.action == ReviewAction.APPROVE:
            current_dict["status"] = ProfileStatus.APPROVED.value

        current_dict["review"] = {
            "reviewer": review_req.reviewer,
            "reviewed_at": now_str,
            "comment": review_req.comment,
            "error_tags": [t.value if isinstance(t, ErrorTag) else t for t in review_req.error_tags],
        }

        updated_profile = WorkProfile.model_validate(current_dict)
        self.save_profile(updated_profile)

        # Record review event
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO review_events (profile_id, action, reviewer, comment, error_tags, created_at)
                VALUES (?, ?, ?, ?, ?, ?);
                """,
                (
                    profile_id,
                    review_req.action.value if isinstance(review_req.action, ReviewAction) else review_req.action,
                    review_req.reviewer,
                    review_req.comment,
                    json.dumps([t.value if isinstance(t, ErrorTag) else t for t in review_req.error_tags]),
                    now_str,
                ),
            )
            conn.commit()

        return updated_profile

    # ==========================
    # Job tracking methods
    # ==========================
    def create_job(self, job_id: str, kind: str) -> JobResponse:
        now_str = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO jobs (job_id, kind, status, created_at)
                VALUES (?, ?, ?, ?);
                """,
                (job_id, kind, JobStatus.QUEUED.value, now_str),
            )
            conn.commit()
        return JobResponse(
            job_id=job_id,
            kind=kind,
            status=JobStatus.QUEUED,
            created_at=now_str,
        )

    def update_job(
        self,
        job_id: str,
        status: JobStatus,
        result: Any | None = None,
        error: str | None = None,
    ) -> JobResponse | None:
        finished_at = (
            datetime.now(timezone.utc).isoformat()
            if status in (JobStatus.DONE, JobStatus.FAILED)
            else None
        )
        result_json = json.dumps(result, ensure_ascii=False) if result is not None else None

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE jobs
                SET status = ?, result_json = ?, error = ?, finished_at = coalesce(?, finished_at)
                WHERE job_id = ?;
                """,
                (
                    status.value if isinstance(status, JobStatus) else status,
                    result_json,
                    error,
                    finished_at,
                    job_id,
                ),
            )
            conn.commit()

        return self.get_job(job_id)

    def get_job(self, job_id: str) -> JobResponse | None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT job_id, kind, status, result_json, error, created_at, finished_at FROM jobs WHERE job_id = ?",
                (job_id,),
            )
            row = cursor.fetchone()
            if not row:
                return None
            result = json.loads(row["result_json"]) if row["result_json"] else None
            return JobResponse(
                job_id=row["job_id"],
                kind=row["kind"],
                status=JobStatus(row["status"]),
                result=result,
                error=row["error"],
                created_at=row["created_at"],
                finished_at=row["finished_at"],
            )
