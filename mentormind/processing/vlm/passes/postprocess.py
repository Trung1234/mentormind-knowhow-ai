"""Mandatory post-processing of pass A into draft WorkProfiles (spec 04 §3).

``reason``/``reason_source`` are forced to None whatever the model said (constitution art. 3,
AC-02), ``status="draft"``, evidence and model_info filled, every profile validated against the
contract before it is returned.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from datetime import UTC, datetime

from mentormind.core.guard import SupportsCloudFlag
from mentormind.core.providers.llm.context import strictest
from mentormind.core.schemas.video import Segment
from mentormind.core.schemas.work_profile import (
    SCHEMA_VERSION,
    WorkProfile,
    validate_against_contract,
)
from mentormind.processing.vlm.passes.models import PassAResult


def to_work_profiles(
    result: PassAResult,
    *,
    segments: Sequence[Segment],
    process_id: str,
    provider: SupportsCloudFlag,
    model: str,
    created_at: datetime | None = None,
) -> list[WorkProfile]:
    """Post-processing (spec 04 §3): draft profiles in time order, each validated by contract."""
    by_id = {s.segment_id: s for s in segments}
    code = re.sub(r"[^A-Z0-9]", "", process_id.upper()) or "UNKNOWN"
    created = created_at or datetime.now(UTC)
    profiles = []
    ordered = sorted(result.steps, key=lambda s: (s.t_start, s.t_end))
    for order, step in enumerate(ordered, start=1):
        segment = by_id[step.segment_id]
        sources = [by_id[sid] for sid in step.sources()]
        profile = WorkProfile(
            schema_version=SCHEMA_VERSION,
            profile_id=f"WP-{code}-{order:03d}",
            process_id=process_id,
            step_order=order,
            step=step.step,
            actor=step.actor,
            hand_action=step.hand_action,
            objects=step.objects,
            key_point=step.key_point_observed,
            # Constitution art. 3: a VLM never supplies the reason, whatever it returned.
            reason=None,
            reason_source=None,
            evidence={
                "video_id": segment.video_id,
                "t_start": step.t_start,
                "t_end": step.t_end,
                "segment_ids": [s.segment_id for s in sources],
                "keyframes": [kf for s in sources for kf in s.keyframes],
                "transcript_excerpt": None,
                "document_refs": [],
            },
            confidence=step.confidence,
            generated_by="vlm",
            model_info={"provider": provider.name, "model": model, "fps": step.fps},
            # A step merged across segments is as sensitive as the strictest of them.
            data_classification=strictest(s.data_classification for s in sources),
            status="draft",
            created_at=created,
        )
        validate_against_contract(profile)
        profiles.append(profile)
    return profiles
