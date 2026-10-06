"""spec 03 FR-08, AC-06 — put each transcript line into the segment it overlaps most."""

from __future__ import annotations

from mentormind.capture.video.align import align_transcript
from mentormind.core.schemas import DataClassification
from mentormind.core.schemas.video import Segment, TranscriptSegment

VID = "VID-aaaaaaaaaaaa"
LABEL = DataClassification.PUBLIC


def _segment(index: int, t_start: float, t_end: float, video_id: str = VID) -> Segment:
    return Segment(
        segment_id=f"{video_id}-S{index:03d}",
        video_id=video_id,
        index=index,
        t_start=t_start,
        t_end=t_end,
        method="fixed_window",
        motion_score=None,
        keyframes=[],
        clip_path="c.mp4",
        data_classification=LABEL,
    )


def _line(t_start: float, t_end: float, text: str = "x", video_id: str = VID) -> TranscriptSegment:
    return TranscriptSegment(
        video_id=video_id, t_start=t_start, t_end=t_end, text=text, language="vi", data_classification=LABEL
    )


SEGMENTS = [_segment(1, 0, 10), _segment(2, 10, 20), _segment(3, 20, 30)]


def test_ac_06_a_line_across_a_boundary_goes_to_the_segment_holding_most_of_it() -> None:
    result = align_transcript(SEGMENTS, [_line(8.0, 14.0, "6s: 2s in S1, 4s in S2")])
    assert [t.text for t in result[f"{VID}-S002"]] == ["6s: 2s in S1, 4s in S2"]
    assert result[f"{VID}-S001"] == []


def test_ac_06_the_other_side_of_the_boundary() -> None:
    result = align_transcript(SEGMENTS, [_line(6.0, 11.0, "5s: 4s in S1, 1s in S2")])
    assert [t.text for t in result[f"{VID}-S001"]] == ["5s: 4s in S1, 1s in S2"]


def test_a_tie_goes_to_the_earlier_segment() -> None:
    result = align_transcript(SEGMENTS, [_line(8.0, 12.0, "tie")])
    assert [t.text for t in result[f"{VID}-S001"]] == ["tie"] and result[f"{VID}-S002"] == []


def test_every_segment_is_a_key_even_without_speech() -> None:
    result = align_transcript(SEGMENTS, [_line(1.0, 2.0)])
    assert list(result) == [s.segment_id for s in SEGMENTS]
    assert result[f"{VID}-S003"] == []


def test_a_line_outside_every_segment_is_dropped() -> None:
    result = align_transcript(SEGMENTS, [_line(40.0, 45.0, "after the video")])
    assert all(lines == [] for lines in result.values())


def test_lines_of_another_video_are_ignored() -> None:
    other = _line(1.0, 2.0, "someone else", video_id="VID-bbbbbbbbbbbb")
    assert align_transcript(SEGMENTS, [other])[f"{VID}-S001"] == []


def test_several_lines_in_one_segment_keep_time_order() -> None:
    result = align_transcript(SEGMENTS, [_line(5.0, 6.0, "b"), _line(1.0, 2.0, "a"), _line(11.0, 12.0, "c")])
    assert [t.text for t in result[f"{VID}-S001"]] == ["a", "b"] and [t.text for t in result[f"{VID}-S002"]] == ["c"]


def test_no_segments_gives_an_empty_mapping() -> None:
    assert align_transcript([], [_line(1.0, 2.0)]) == {}
