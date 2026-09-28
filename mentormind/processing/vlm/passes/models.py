"""Data models of lượt A: the step as the VLM reports it, placed on the timeline, the run."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ObservedStep(BaseModel):
    """One step exactly as the VLM reported it (relative times). Unknown keys are dropped."""

    model_config = ConfigDict(extra="ignore")

    step: str = Field(min_length=3)
    hand_action: str | None = None
    objects: list[str] = Field(default_factory=list)
    key_point_observed: str | None = None
    t_start_rel: float = Field(ge=0)
    t_end_rel: float = Field(ge=0)
    confidence: float = Field(ge=0, le=1)


class PassAOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")

    #: One or two sentences on what the frames show, written before the steps.
    scene: str | None = None
    steps: list[ObservedStep]


class TimedStep(BaseModel):
    """A pass-A step placed on the video timeline (absolute seconds)."""

    segment_id: str
    t_start: float = Field(ge=0)
    t_end: float = Field(ge=0)
    step: str
    hand_action: str | None = None
    objects: list[str] = Field(default_factory=list)
    key_point_observed: str | None = None
    confidence: float = Field(ge=0, le=1)
    fps: float = Field(gt=0)
    keyframes: list[str] = Field(default_factory=list)


class FailedSegment(BaseModel):
    segment_id: str
    error: str
    raw_text: str


class PassAResult(BaseModel):
    steps: list[TimedStep] = Field(default_factory=list)
    failed: list[FailedSegment] = Field(default_factory=list)
    #: segment_id -> the model's own description of the segment ("scene").
    scenes: dict[str, str] = Field(default_factory=dict)
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_s: float = 0.0
    calls: int = 0

    @property
    def tokens_used(self) -> int:
        return self.prompt_tokens + self.completion_tokens
