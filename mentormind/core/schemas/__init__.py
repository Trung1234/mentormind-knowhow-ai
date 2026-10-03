"""Pydantic models for every data I/O in the system (spec 01 FR-08)."""

from mentormind.core.schemas.api import (
    AskRequest,
    AssistantAnswer,
    Hypothesis,
    JobResponse,
    JobStatus,
    LotRecord,
    ProfilePatchRequest,
    RcaReport,
    RcaRequest,
    ReviewAction,
    ReviewRequest,
    WhyStep,
)
from mentormind.core.schemas.common import Citation, DataClassification
from mentormind.core.schemas.document import ChunkKind, DocumentChunk
from mentormind.core.schemas.vector import VectorChunk, VectorHit
from mentormind.core.schemas.video import Segment, TranscriptSegment, VideoAsset
from mentormind.core.schemas.work_profile import (
    SCHEMA_VERSION,
    Actor,
    ContractValidationError,
    ErrorTag,
    Evidence,
    ExceptionCase,
    Expert,
    GeneratedBy,
    ModelInfo,
    ProfileStatus,
    ReasonSource,
    Review,
    WorkProfile,
    validate_against_contract,
)

# Aliases for compatibility
ExceptionItem = ExceptionCase
ExpertInfo = Expert
ReviewInfo = Review

__all__ = [
    "SCHEMA_VERSION",
    "Actor",
    "AskRequest",
    "AssistantAnswer",
    "ChunkKind",
    "Citation",
    "ContractValidationError",
    "DataClassification",
    "DocumentChunk",
    "ErrorTag",
    "Evidence",
    "ExceptionCase",
    "ExceptionItem",
    "Expert",
    "ExpertInfo",
    "GeneratedBy",
    "Hypothesis",
    "JobResponse",
    "JobStatus",
    "LotRecord",
    "ModelInfo",
    "ProfilePatchRequest",
    "ProfileStatus",
    "RcaReport",
    "RcaRequest",
    "ReasonSource",
    "Review",
    "ReviewAction",
    "ReviewInfo",
    "ReviewRequest",
    "Segment",
    "TranscriptSegment",
    "VectorChunk",
    "VectorHit",
    "VideoAsset",
    "WhyStep",
    "WorkProfile",
    "validate_against_contract",
]
