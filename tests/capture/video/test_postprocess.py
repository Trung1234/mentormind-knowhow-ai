"""spec 03 FR-04, AC-02, AC-03 — merge short pieces, split long ones, keep full coverage."""

from __future__ import annotations

import math

import pytest

from mentormind.capture.video.postprocess import bounds_from_cuts, postprocess


def _check(bounds: list[tuple[float, float]], duration: float) -> None:
    assert bounds[0][0] == 0.0 and bounds[-1][1] == pytest.approx(duration)
    for (_, end), (start, _) in zip(bounds, bounds[1:], strict=False):
        assert end == start  # contiguous: no gap, no overlap (AC-03)


def test_bounds_from_cuts_covers_the_whole_video() -> None:
    assert bounds_from_cuts([5.0, 12.5], 20.0) == [(0.0, 5.0), (5.0, 12.5), (12.5, 20.0)]
    assert bounds_from_cuts([], 8.0) == [(0.0, 8.0)]


def test_bounds_from_cuts_ignores_cuts_outside_or_duplicated() -> None:
    assert bounds_from_cuts([0.0, 5.0, 5.0, 99.0, -1.0], 10.0) == [(0.0, 5.0), (5.0, 10.0)]


def test_ac_02_short_piece_merges_into_the_previous_one() -> None:
    out = postprocess([(0, 10), (10, 12), (12, 25)], 25.0)
    assert out == [(0.0, 12.0), (12.0, 25.0)]


def test_short_first_piece_merges_into_the_next_one() -> None:
    assert postprocess([(0, 1.5), (1.5, 12)], 12.0) == [(0.0, 12.0)]


def test_consecutive_short_pieces_all_get_absorbed() -> None:
    out = postprocess([(0, 10), (10, 11), (11, 12), (12, 13), (13, 23)], 23.0)
    assert all(end - start >= 3 for start, end in out)
    _check(out, 23.0)


def test_ac_02_long_piece_is_split_into_equal_parts_of_at_most_15s() -> None:
    out = postprocess([(0, 47)], 47.0)
    assert len(out) == math.ceil(47 / 15) == 4
    assert all(end - start <= 15 for start, end in out)
    _check(out, 47.0)


def test_piece_of_exactly_20s_is_left_alone() -> None:
    assert postprocess([(0, 20)], 20.0) == [(0.0, 20.0)]


def test_merge_can_create_a_long_piece_which_is_then_split() -> None:
    out = postprocess([(0, 19), (19, 21), (21, 40)], 40.0)  # 21s after merge → split
    assert all(3 <= end - start <= 20 for start, end in out)
    _check(out, 40.0)


@pytest.mark.parametrize("duration", [2.0, 1.0])
def test_video_shorter_than_3s_stays_one_piece(duration: float) -> None:
    assert postprocess([(0, duration)], duration) == [(0.0, duration)]


def test_ac_02_ac_03_hold_for_many_random_looking_cuts() -> None:
    cuts = [0.4, 1.0, 4.2, 4.9, 9.9, 31.0, 31.5, 60.2, 61.0, 100.0]
    out = postprocess(bounds_from_cuts(cuts, 130.0), 130.0)
    assert all(3 <= end - start <= 20 for start, end in out)
    _check(out, 130.0)
