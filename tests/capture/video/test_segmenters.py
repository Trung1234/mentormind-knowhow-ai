"""spec 03 FR-03 — the three cutting methods, motion_score, and the fallback chain (AC-04, AC-11)."""

from __future__ import annotations

import logging
import sys
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest

from mentormind.capture.video.segmenters import (
    Cut,
    FixedWindowSegmenter,
    HandActivitySegmenter,
    Method,
    SceneSegmenter,
    Segmenter,
    SegmenterUnavailable,
    cut_with_fallback,
)
from mentormind.capture.video.segmenters.hand_activity import rest_boundaries, wrist_speeds
from mentormind.core.schemas.common import DataClassification
from mentormind.core.schemas.video import VideoAsset
from tests.capture.video.fakes import synthetic_video

Point = tuple[float, float]


def asset(duration: float) -> VideoAsset:
    return VideoAsset(
        video_id="VID-TEST", path="x.mp4", duration_s=duration, fps=25.0, has_audio=False,
        process_id="PACK01", data_classification=DataClassification.SYNTHETIC,
    )  # fmt: skip


def no_frames(duration: float) -> Callable[[Path, float, int], Iterator[tuple[float, Any]]]:
    """Timestamps only: the fake hand detector reads its script, not the pixels."""

    def frames(video: Path, fps: float, long_side: int) -> Iterator[tuple[float, Any]]:
        return ((i / fps, None) for i in range(round(duration * fps) + 1))

    return frames


class ScriptedHands:
    def __init__(self, script: Callable[[float], list[Point]]) -> None:
        self.script = script
        self.closed = False

    def wrists(self, frame: Any, t: float) -> list[Point]:
        return self.script(round(t, 3))

    def close(self) -> None:
        self.closed = True


def operator(t: float) -> list[Point]:
    """0–3 s brisk work, 3–4 s hands still, 4–7 s slow work with a 0.2 s missed detection, then hands gone."""
    if t < 3:
        return [(0.3 if round(t * 5) % 2 else 0.5, 0.5)]  # 0.2 frame widths every 0.2 s = 1.0/s
    if t <= 4:
        return [(0.4, 0.5)]
    if 5.4 < t < 5.6:
        return []  # one frame without hands: a missed detection, not a rest
    if t < 7:
        return [(0.42 if round(t * 5) % 2 else 0.4, 0.5)]  # 0.1/s: slow, still above the rest threshold
    return []


def test_ac_11_hands_resting_0_4s_or_more_mark_a_boundary_shorter_gaps_do_not() -> None:
    hands = ScriptedHands(operator)
    cutter = HandActivitySegmenter(detector=lambda: hands, frames=no_frames(10))
    cuts = cutter.cut(Path("x.mp4"), asset(10))
    assert [(c.t_start, c.t_end) for c in cuts] == [(0.0, 3.5), (3.5, 10.0)]  # no cut at 5.5 s, none in the tail
    fast, slow = (c.motion_score for c in cuts)
    assert fast is not None and slow is not None and 0 <= slow < fast <= 1
    assert hands.closed  # the detector is released after the run


def test_rest_needs_activity_on_both_sides() -> None:
    still = [(i / 5, 0.0) for i in range(1, 20)]
    assert rest_boundaries(still) == []  # hands never moved: no boundary (FR-04 splits a long cut)
    assert wrist_speeds([(0.0, []), (1.0, [(0.5, 0.5)])]) == [(0.0, 0.0)]


def test_ac_04_without_mediapipe_hand_activity_falls_back_to_scene(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture, tmp_path: Path
) -> None:
    monkeypatch.setitem(sys.modules, "mediapipe", None)  # import fails
    video = synthetic_video(tmp_path / "in.mp4", 12)

    def build(method: Method) -> Segmenter:
        if method == "hand_activity":
            return HandActivitySegmenter(model=tmp_path / "hand.task")
        return SceneSegmenter(detect=lambda v, threshold: [(0.0, 5.0), (5.0, 12.0)])

    with caplog.at_level(logging.WARNING):
        cuts, used = cut_with_fallback("hand_activity", video, asset(12), build=build)
    assert used == "scene" and [(c.t_start, c.t_end) for c in cuts] == [(0.0, 5.0), (5.0, 12.0)]
    assert "hand_activity" in caplog.text and "scene" in caplog.text


def test_without_scenedetect_scene_falls_back_to_fixed_windows(tmp_path: Path) -> None:
    def missing(video: Path, threshold: float) -> list[tuple[float, float]]:
        raise SegmenterUnavailable("thiếu thư viện scenedetect")

    def build(method: Method) -> Segmenter:
        return SceneSegmenter(detect=missing) if method == "scene" else FixedWindowSegmenter(motion=False)

    cuts, used = cut_with_fallback("scene", Path("x.mp4"), asset(25), build=build)
    assert used == "fixed_window" and [(c.t_start, c.t_end) for c in cuts] == [(0, 10), (10, 20), (20, 25)]


def test_scene_and_fixed_windows_score_motion_from_frame_differences(tmp_path: Path) -> None:
    video = synthetic_video(tmp_path / "in.mp4", 12)  # brightness rises frame after frame
    for cutter in (FixedWindowSegmenter(), SceneSegmenter(detect=lambda v, threshold: [])):
        cuts = cutter.cut(video, asset(12))
        assert cuts and all(c.motion_score is not None and 0 < c.motion_score <= 1 for c in cuts), cutter.name
    single = SceneSegmenter(detect=lambda v, threshold: []).cut(video, asset(12))
    assert [(c.t_start, c.t_end) for c in single] == [(0.0, 12.0)]  # one shot: FR-04 will split it


def test_every_method_name_has_a_segmenter() -> None:
    assert {FixedWindowSegmenter.name, SceneSegmenter.name, HandActivitySegmenter.name} == {
        "fixed_window",
        "scene",
        "hand_activity",
    }
    assert Cut(1, 4).duration == 3
