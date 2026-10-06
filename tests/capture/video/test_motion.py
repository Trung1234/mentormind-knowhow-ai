"""spec 03 FR-09, AC-10 — `motion_score`: frame differences, 0..1, absolute."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from mentormind.capture.video.media import MediaError
from mentormind.capture.video.motion import (
    FRAME_BYTES,
    SAMPLE_FPS,
    ffmpeg_gray_frames,
    motion_profile,
    motion_score,
)
from tests.capture.video.conftest import MakeVideo, needs_ffmpeg

DARK = bytes(FRAME_BYTES)
BRIGHT = bytes([255]) * FRAME_BYTES


def test_identical_frames_have_zero_difference_and_opposite_frames_one() -> None:
    assert motion_profile([DARK, DARK, DARK]) == [0.0, 0.0]
    assert motion_profile([DARK, BRIGHT]) == [1.0]


def test_fewer_than_two_frames_give_no_differences() -> None:
    assert motion_profile([]) == [] and motion_profile([DARK]) == []


def test_score_is_scaled_clipped_and_uses_only_pairs_inside_the_segment() -> None:
    diffs = [0.05] * 50  # pair i spans [i/5, (i+1)/5]
    assert motion_score(diffs, 0.0, 10.0, scale=0.1) == pytest.approx(0.5)
    assert motion_score(diffs, 0.0, 10.0, scale=0.025) == 1.0  # clipped to 1
    assert motion_score([0.0] * 50, 0.0, 10.0, scale=0.1) == 0.0


def test_a_hard_cut_inside_the_segment_does_not_inflate_the_score() -> None:
    diffs = [0.01] * 20 + [0.9] + [0.01] * 20  # one cut = one huge difference
    assert motion_score(diffs, 0.0, 8.2, scale=0.1) == pytest.approx(0.1)


def test_segment_with_no_complete_pair_has_no_score() -> None:
    assert motion_score([0.05] * 10, 0.0, 0.1, scale=0.1) is None
    assert motion_score([], 0.0, 10.0, scale=0.1) is None
    assert motion_score([0.05] * 10, 50.0, 60.0, scale=0.1) is None


def test_only_the_requested_window_counts() -> None:
    diffs = [0.0] * 25 + [0.1] * 25  # still for 5 s, then moving
    assert motion_score(diffs, 0.0, 5.0, scale=0.1) == 0.0
    assert motion_score(diffs, 5.0, 10.0, scale=0.1) == 1.0


def test_scale_must_be_positive() -> None:
    with pytest.raises(ValueError, match="scale"):
        motion_score([0.1] * 10, 0.0, 2.0, scale=0)


def test_ffmpeg_failure_is_a_media_error(tmp_path: Path) -> None:
    with pytest.raises(MediaError, match="ffmpeg"):
        list(ffmpeg_gray_frames(tmp_path / "nope.mp4", ffmpeg="no-such-ffmpeg-binary"))


@needs_ffmpeg
def test_ac_10_still_shot_scores_low_and_moving_shot_scores_higher(make_video: MakeVideo, tmp_path: Path) -> None:
    from tests.capture.video.conftest import write_video

    still = write_video(tmp_path / "still.mp4", [((30, 30, 30), 4.0)], still=True)
    moving = write_video(tmp_path / "moving.mp4", [((30, 30, 30), 4.0)])
    s = motion_score(motion_profile(ffmpeg_gray_frames(still)), 0.0, 4.0, scale=0.1)
    m = motion_score(motion_profile(ffmpeg_gray_frames(moving)), 0.0, 4.0, scale=0.1)
    assert s is not None and m is not None and s < 0.05 and m > s + 0.2


@needs_ffmpeg
def test_sampling_rate_matches_the_pair_timing(make_video: MakeVideo) -> None:
    frames = list(ffmpeg_gray_frames(make_video()))  # 12 s
    assert abs(len(frames) - 12 * SAMPLE_FPS) <= 2 and all(len(f) == FRAME_BYTES for f in frames)
    assert isinstance(np.frombuffer(frames[0], dtype=np.uint8), np.ndarray)
