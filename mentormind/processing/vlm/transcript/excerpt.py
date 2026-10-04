"""A step's ``transcript_excerpt``: what the expert said during the segments it comes from (spec 04 §3).

Which line belongs to which segment is spec 03's job (FR-08 ``align_transcript``, Hoàng): it is
imported from ``SPEC03_MODULE`` when spec 03 provides it. Until then — or without a transcript —
there is no alignment and every excerpt stays ``None``, as before. Spec 04 only joins the aligned
lines of a step's segments.
"""

from __future__ import annotations

import importlib
import logging
from collections.abc import Mapping, Sequence

from mentormind.core.schemas.video import Segment, TranscriptSegment

log = logging.getLogger(__name__)

#: Module of spec 03 expected to define ``align_transcript(segments, transcripts)`` (FR-08).
SPEC03_MODULE = "mentormind.capture.video"

#: segment_id -> the transcript lines spec 03 aligned to it.
Aligned = Mapping[str, Sequence[TranscriptSegment]]


def align(segments: Sequence[Segment], transcript: Sequence[TranscriptSegment]) -> Aligned | None:
    """Spec 03's alignment of ``transcript`` to ``segments``; None without a transcript or spec 03."""
    if not transcript:
        return None
    try:
        align_transcript = importlib.import_module(SPEC03_MODULE).align_transcript
    except (ImportError, AttributeError):
        log.info("No %s.align_transcript (spec 03) yet: transcript_excerpt stays empty", SPEC03_MODULE)
        return None
    aligned: Aligned = align_transcript(segments, transcript)
    return aligned


def lines_for(segment_ids: Sequence[str], aligned: Aligned | None) -> list[TranscriptSegment]:
    """The lines spec 03 aligned to these segments, in time order (their labels join the profile's)."""
    if not aligned:
        return []
    lines = [line for sid in dict.fromkeys(segment_ids) for line in aligned.get(sid, ())]
    return sorted(lines, key=lambda t: (t.t_start, t.t_end))


def excerpt_for(segment_ids: Sequence[str], aligned: Aligned | None) -> str | None:
    """What the expert said during these segments; None when nothing (or no transcript)."""
    text = " ".join(line.text.strip() for line in lines_for(segment_ids, aligned) if line.text.strip())
    return text or None
