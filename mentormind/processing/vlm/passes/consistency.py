"""Pass B — self-consistency (spec 04 §3, T04-4).

Pass A runs twice on the same segments (``temperature=0.2``). A step survives only when BOTH runs
report it in the same segment: ``token_set_ratio(step) >= 70`` and overlapping times (the matching
rule of :mod:`passes.matching`), paired one-to-one, best score first. Small VLMs "see" plausible
actions that are not in the video; an invented step rarely comes back the same way twice.

The kept step is the first run's, with ``confidence = mean(c1, c2) x score / 100``. A segment that
failed in either run is failed: its steps cannot be confirmed.
"""

from __future__ import annotations

from mentormind.processing.vlm.passes.matching import MATCH_THRESHOLD, overlaps, similarity
from mentormind.processing.vlm.passes.models import PassAResult, TimedStep


def self_consistent(
    first: PassAResult, second: PassAResult, threshold: float = MATCH_THRESHOLD
) -> PassAResult:
    """Steps both runs agree on, plus both runs' failures, scenes and costs (AC-04)."""
    failed = {f.segment_id: f for f in [*first.failed, *second.failed]}
    kept: list[TimedStep] = []
    for segment_id in dict.fromkeys(s.segment_id for s in first.steps):
        if segment_id in failed:
            continue
        ours = [s for s in first.steps if s.segment_id == segment_id]
        theirs = [s for s in second.steps if s.segment_id == segment_id]
        kept += _agreed(ours, theirs, threshold)
    return PassAResult(
        steps=sorted(kept, key=lambda s: (s.t_start, s.t_end)),
        failed=list(failed.values()),
        scenes={**second.scenes, **first.scenes},
        prompt_tokens=first.prompt_tokens + second.prompt_tokens,
        completion_tokens=first.completion_tokens + second.completion_tokens,
        latency_s=first.latency_s + second.latency_s,
        calls=first.calls + second.calls,
    )


def _agreed(ours: list[TimedStep], theirs: list[TimedStep], threshold: float) -> list[TimedStep]:
    candidates = sorted(
        (
            (score, i, j)
            for i, a in enumerate(ours)
            for j, b in enumerate(theirs)
            if overlaps(a.t_start, a.t_end, b.t_start, b.t_end)
            and (score := similarity(a.step, b.step)) >= threshold
        ),
        reverse=True,
    )
    used_ours: set[int] = set()
    used_theirs: set[int] = set()
    kept = []
    for score, i, j in candidates:
        if i in used_ours or j in used_theirs:
            continue
        used_ours.add(i)
        used_theirs.add(j)
        confidence = (ours[i].confidence + theirs[j].confidence) / 2 * score / 100
        kept.append(ours[i].model_copy(update={"confidence": round(confidence, 3)}))
    return kept
