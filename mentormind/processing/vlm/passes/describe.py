"""Pass A — describe each segment (spec 04 §3, T04-3).

For every :class:`Segment`: sample frames (FR-02b), ask the VLM with ``prompts/pass_a_describe.md``,
validate the answer against :data:`PASS_A_SCHEMA`; an invalid answer is retried ONCE with
``prompts/repair_json.md`` and, if still invalid, the segment goes to ``failed_segments.json``
while the other segments carry on (AC-06). Raw answers are kept under
``data/work/vlm/<video_id>/pass_a/`` (FR-06).

Post-processing into WorkProfiles lives in :mod:`processing.vlm.passes.postprocess`.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from mentormind.core.providers.errors import InvalidJSONError
from mentormind.core.providers.models import TokenUsage
from mentormind.core.providers.parsing import parse_json_object
from mentormind.core.schemas.video import Segment
from mentormind.processing.vlm.frames.sampler import SampledFrames, sample_frames
from mentormind.processing.vlm.passes.models import (
    FailedSegment,
    PassAOutput,
    PassAResult,
    TimedStep,
)
from mentormind.processing.vlm.passes.prompting import render_prompt
from mentormind.processing.vlm.providers.base import VLMProvider
from mentormind.processing.vlm.providers.models import VLMResponse

PASS_A_TEMPERATURE = 0.2

PASS_A_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        # Describe first, extract second: without it Qwen3-VL-8B answered {"steps": []} for every
        # segment of the demo video (spec 04 v1.5).
        "scene": {"type": "string"},
        "steps": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "step": {"type": "string"},
                    "hand_action": {"type": ["string", "null"]},
                    "objects": {"type": "array", "items": {"type": "string"}},
                    "key_point_observed": {"type": ["string", "null"]},
                    "t_start_rel": {"type": "number"},
                    "t_end_rel": {"type": "number"},
                    "confidence": {"type": "number"},
                },
                "required": ["step", "t_start_rel", "t_end_rel", "confidence"],
            },
        },
    },
    "required": ["scene", "steps"],
}

Sampler = Callable[..., SampledFrames]


def describe_segments(
    segments: Sequence[Segment],
    provider: VLMProvider,
    *,
    process_id: str,
    work_dir: Path,
    default_fps: float,
    max_frames: int,
    temperature: float = PASS_A_TEMPERATURE,
    sampler: Sampler = sample_frames,
) -> PassAResult:
    """Run pass A over ``segments`` (in order). Never raises for one bad segment."""
    result = PassAResult()
    for segment in segments:
        _describe_one(
            segment,
            provider,
            result,
            process_id=process_id,
            work_dir=work_dir,
            default_fps=default_fps,
            max_frames=max_frames,
            temperature=temperature,
            sampler=sampler,
        )
    if result.failed:
        (work_dir / "failed_segments.json").write_text(
            json.dumps([f.model_dump() for f in result.failed], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    return result


def _describe_one(
    segment: Segment,
    provider: VLMProvider,
    result: PassAResult,
    *,
    process_id: str,
    work_dir: Path,
    default_fps: float,
    max_frames: int,
    temperature: float,
    sampler: Sampler,
) -> None:
    sampled = sampler(
        segment,
        provider,
        out_dir=work_dir / "frames" / segment.segment_id,
        default_fps=default_fps,
        max_frames=max_frames,
    )
    duration = max(segment.t_end - segment.t_start, 0.0)
    prompt = render_prompt(
        "pass_a_describe.md",
        process_id=process_id,
        duration=f"{duration:.1f}",
        fps=f"{sampled.fps:g}",
        timestamps=", ".join(f"{t:.1f}" for t in sampled.timestamps),
    )
    output: PassAOutput | None = None
    error = ""
    raw_text = ""
    for attempt in range(2):  # the answer, then at most ONE repair (spec 04 §3)
        text_prompt = (
            prompt
            if attempt == 0
            else render_prompt("repair_json.md", original_prompt=prompt, error=error)
        )
        response = provider.generate(
            sampled.paths,
            text_prompt,
            classification=segment.data_classification,
            json_schema=PASS_A_SCHEMA,
            temperature=temperature,
        )
        _account(result, response)
        raw_text = response.text
        _save_raw(work_dir, segment, attempt, text_prompt, response, sampled)
        try:
            output = PassAOutput.model_validate(parse_json_object(response.text))
            break
        except (InvalidJSONError, ValidationError) as exc:
            error = _short_error(exc)
    if output is None:
        result.failed.append(
            FailedSegment(segment_id=segment.segment_id, error=error, raw_text=raw_text)
        )
        return
    if output.scene:
        result.scenes[segment.segment_id] = output.scene
    for step in output.steps:
        start = min(step.t_start_rel, duration)
        end = min(max(step.t_end_rel, step.t_start_rel), duration)
        result.steps.append(
            TimedStep(
                segment_id=segment.segment_id,
                t_start=round(segment.t_start + start, 2),
                t_end=round(segment.t_start + end, 2),
                step=step.step.strip(),
                hand_action=step.hand_action,
                objects=step.objects,
                key_point_observed=step.key_point_observed,
                confidence=step.confidence,
                fps=sampled.fps,
                keyframes=list(segment.keyframes),
            )
        )


def _account(result: PassAResult, response: VLMResponse) -> None:
    usage = response.usage or TokenUsage(prompt_tokens=0, completion_tokens=0)
    result.prompt_tokens += usage.prompt_tokens
    result.completion_tokens += usage.completion_tokens
    result.latency_s += response.latency_s
    result.calls += 1


def _save_raw(
    work_dir: Path,
    segment: Segment,
    attempt: int,
    prompt: str,
    response: VLMResponse,
    sampled: SampledFrames,
) -> None:
    raw_dir = work_dir / "pass_a"
    raw_dir.mkdir(parents=True, exist_ok=True)
    suffix = "" if attempt == 0 else ".repair"
    record = {
        "segment_id": segment.segment_id,
        "t_start": segment.t_start,
        "t_end": segment.t_end,
        "fps": sampled.fps,
        "frame_timestamps": sampled.timestamps,
        "prompt": prompt,
        "response": response.model_dump(mode="json"),
    }
    (raw_dir / f"{segment.segment_id}{suffix}.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _short_error(exc: Exception) -> str:
    if isinstance(exc, ValidationError):
        first = exc.errors()[0]
        return f"sai schema tại {'/'.join(map(str, first['loc']))}: {first['msg']}"
    return "không phải JSON"
