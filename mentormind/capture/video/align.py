"""``align_transcript``: attach transcript lines to segments (spec 03 FR-08, AC-06)."""

from __future__ import annotations

from collections.abc import Sequence

from mentormind.core.schemas.video import Segment, TranscriptSegment


def align_transcript(
    segments: Sequence[Segment], transcripts: Sequence[TranscriptSegment]
) -> dict[str, list[TranscriptSegment]]:
    """Give each line to the segment it overlaps the most (the earlier one on a tie).

    Every segment id is a key, with an empty list when nobody speaks there. A line that overlaps no
    segment, or belongs to another video, is left out. Lines in a segment stay in time order.
    """
    result: dict[str, list[TranscriptSegment]] = {s.segment_id: [] for s in segments}
    for line in sorted(transcripts, key=lambda t: (t.t_start, t.t_end)):
        best_id: str | None = None
        best = 0.0
        for segment in segments:
            if segment.video_id != line.video_id:
                continue
            overlap = min(segment.t_end, line.t_end) - max(segment.t_start, line.t_start)
            if overlap > best + 1e-9:  # strict: an equal overlap keeps the earlier segment
                best_id, best = segment.segment_id, overlap
        if best_id is not None:
            result[best_id].append(line)
    return result
