"""``describe_video`` — the whole spec 04 §3 pipeline: segments in, draft WorkProfiles out.

    pass A   describe every segment (VLM)                          passes/describe.py
    pass B   pass A a second time; keep steps both runs report     passes/consistency.py
    pass C   merge steps cut by segment boundaries (text LLM)      passes/merge.py
    post     reason=None, status=draft, evidence, contract check   passes/postprocess.py

Artefacts under ``work_dir`` (FR-06): ``pass_a/`` (run 1 raw answers), ``pass_b/pass_a/`` (run 2),
``pass_c.json``, ``failed_segments.json``, ``predictions.json`` (final steps), ``profiles.json``.
Frames are sampled once per segment and reused by both runs.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from mentormind.core.llm import LLMProvider
from mentormind.core.schemas.video import Segment
from mentormind.core.schemas.work_profile import WorkProfile
from mentormind.processing.vlm.frames.sampler import SampledFrames, sample_frames
from mentormind.processing.vlm.passes import describe_segments, to_work_profiles
from mentormind.processing.vlm.passes.consistency import self_consistent
from mentormind.processing.vlm.passes.describe import Sampler
from mentormind.processing.vlm.passes.merge import MergeReport, merge_steps
from mentormind.processing.vlm.passes.models import PassAResult
from mentormind.processing.vlm.providers.base import VLMProvider


class DescribeResult(BaseModel):
    profiles: list[WorkProfile]
    #: Steps after the last pass that ran (absolute times).
    steps: PassAResult
    #: Steps pass A reported on its first run, before pass B filtered them.
    pass_a_steps: int
    merge: MergeReport | None = None
    failed_segments: list[str]


def describe_video(
    segments: Sequence[Segment],
    vlm: VLMProvider,
    *,
    process_id: str,
    work_dir: Path,
    default_fps: float,
    max_frames: int,
    llm: LLMProvider | None = None,
    consistency: bool = True,
    sampler: Sampler = sample_frames,
) -> DescribeResult:
    """Run passes A, B (``consistency``) and C (when an ``llm`` is given) and post-process."""
    work_dir.mkdir(parents=True, exist_ok=True)
    cached = _cache(sampler)
    kwargs: dict[str, Any] = {
        "process_id": process_id,
        "default_fps": default_fps,
        "max_frames": max_frames,
        "sampler": cached,
    }
    first = describe_segments(segments, vlm, work_dir=work_dir, **kwargs)
    steps = first
    if consistency:
        second = describe_segments(segments, vlm, work_dir=work_dir / "pass_b", **kwargs)
        steps = self_consistent(first, second)
    report = None
    if llm is not None:
        steps, report = merge_steps(steps, segments, llm, process_id=process_id, work_dir=work_dir)
    profiles = to_work_profiles(
        steps, segments=segments, process_id=process_id, provider=vlm, model=vlm.model
    )
    failed = [f.segment_id for f in steps.failed]
    (work_dir / "failed_segments.json").unlink(missing_ok=True)
    if steps.failed:
        (work_dir / "failed_segments.json").write_text(
            json.dumps([f.model_dump() for f in steps.failed], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    (work_dir / "predictions.json").write_text(steps.model_dump_json(indent=2), encoding="utf-8")
    write_profiles(profiles, work_dir / "profiles.json")
    return DescribeResult(
        profiles=profiles,
        steps=steps,
        pass_a_steps=len(first.steps),
        merge=report,
        failed_segments=failed,
    )


def write_profiles(profiles: Sequence[WorkProfile], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps([p.to_contract_dict() for p in profiles], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def read_profiles(path: Path) -> list[WorkProfile]:
    return [WorkProfile.model_validate(p) for p in json.loads(path.read_text(encoding="utf-8"))]


def _cache(sampler: Sampler) -> Sampler:
    """The same frames for both pass-A runs: sample each segment once."""
    seen: dict[str, SampledFrames] = {}

    def sample(segment: Segment, destination: Any, **kwargs: Any) -> SampledFrames:
        if segment.segment_id not in seen:
            seen[segment.segment_id] = sampler(segment, destination, **kwargs)
        return seen[segment.segment_id]

    return sample
