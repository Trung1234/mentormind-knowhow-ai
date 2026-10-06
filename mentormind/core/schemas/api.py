"""REST API Request & Response Schemas (Spec 08)."""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from mentormind.core.schemas.common import Citation, DataClassification
from mentormind.core.schemas.work_profile import (
    ErrorTag,
    ExceptionCase,
    Expert,
    ReasonSource,
)


class ReviewAction(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"


class ReviewRequest(BaseModel):
    action: ReviewAction
    reviewer: str = Field(min_length=1)
    comment: str | None = None
    error_tags: list[ErrorTag] = Field(default_factory=list)

    @model_validator(mode="after")
    def check_reject_reason(self) -> ReviewRequest:
        if self.action == ReviewAction.REJECT and not (self.comment and self.comment.strip()):
            raise ValueError("Từ chối (reject) bắt buộc phải nhập lý do (comment).")
        return self


class ProfilePatchRequest(BaseModel):
    step: str | None = Field(default=None, min_length=3)
    hand_action: str | None = None
    objects: list[str] | None = None
    key_point: str | None = None
    reason: str | None = None
    reason_source: ReasonSource | None = None
    exceptions: list[ExceptionCase] | None = None
    pass_criteria: str | None = None
    equipment_id: str | None = None
    part_numbers: list[str] | None = None
    expert: Expert | None = None


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


class JobResponse(BaseModel):
    job_id: str
    kind: str
    status: JobStatus
    result: Any | None = None
    error: str | None = None
    created_at: str | None = None
    finished_at: str | None = None


class DocumentIngestFile(BaseModel):
    """One uploaded file in the result of a ``POST /ingest/documents`` job (spec 08 §2)."""

    name: str
    doc_id: str | None = None
    extractor: str | None = None
    pages: int = 0
    chunks: int = 0
    #: Not a supported format (spec 02 FR-01); such a file has no ``error``.
    skipped: bool = False
    error: str | None = None


class DocumentIngestResult(BaseModel):
    """``JobResponse.result`` of a ``POST /ingest/documents`` job (spec 08 §2, AC-09)."""

    classification: DataClassification
    files: list[DocumentIngestFile] = Field(default_factory=list)
    chunks_indexed: int = 0


class VideoProcessProgress(BaseModel):
    """VLM calls done so far / expected, while a video job runs."""

    done: int = Field(ge=0)
    total: int = Field(ge=0)


class VideoProcessResult(BaseModel):
    """``JobResponse.result`` of a ``POST /videos/{video_id}/process`` job (spec 08 §2, AC-14)."""

    video_id: str
    process_id: str
    segments: int = 0
    #: ``profile_id`` of the drafts saved for this video, in step order.
    profiles: list[str] = Field(default_factory=list)
    failed_segments: list[str] = Field(default_factory=list)
    transcript_lines: int = 0
    reasons_filled: int = 0
    progress: VideoProcessProgress | None = None


class AskRequest(BaseModel):
    process_id: str
    question: str
    top_k: int = 5


class AssistantAnswer(BaseModel):
    answer: str
    refused: bool = False
    suggested_expert: str | None = None
    citations: list[Citation] = Field(default_factory=list)


class RcaRequest(BaseModel):
    lot_id: str | None = None
    symptom: str | None = None


class Hypothesis(BaseModel):
    hypothesis: str
    likelihood: Literal["high", "medium", "low"]
    evidence_refs: list[str] = Field(default_factory=list)


class WhyStep(BaseModel):
    order: int
    question: str
    answer: str
    verified: bool


class RcaReport(BaseModel):
    lot_id: str | None = None
    symptom: str
    hypotheses: list[Hypothesis] = Field(default_factory=list)
    five_whys: list[WhyStep] = Field(default_factory=list)
    related_lots: list[str] = Field(default_factory=list)
    preventive_actions: list[str] = Field(default_factory=list)
    disclaimer: str = "Kết quả phân tích dựa trên AI và dữ liệu mẫu, cần chuyên gia xác nhận trước khi áp dụng."


class LotRecord(BaseModel):
    lot_id: str
    process_id: str
    part_number: str
    produced_at: str
    defect_type: str | None = None
    status: str
