"""spec 03 FR-03, AC-01, AC-02, AC-03, AC-04 — strategies and the fallback chain."""

from __future__ import annotations

from pathlib import Path

import pytest

from mentormind.capture.video.postprocess import MAX_SEGMENT_S, MIN_SEGMENT_S
from mentormind.capture.video.segmenters import (
    FixedWindowSegmenter,
    SceneSegmenter,
    Segmenter,
    SegmenterError,
    plan_segments,
)
from tests.capture.video.conftest import MakeVideo


class FakeSegmenter:
    def __init__(self, method: str, cuts: list[float] | None = None, error: str | None = None) -> None:
        self.method = method
        self._cuts = cuts or []
        self._error = error
        self.calls = 0

    def cuts(self, video: Path, duration: float) -> list[float]:
        self.calls += 1
        if self._error:
            raise SegmenterError(self._error)
        return self._cuts


def _registry(*segmenters: Segmenter) -> dict[str, Segmenter]:
    return {s.method: s for s in segmenters}


def test_fixed_window_cuts_every_window() -> None:
    assert FixedWindowSegmenter(10.0).cuts(Path("x"), 35.0) == [10.0, 20.0, 30.0]
    assert FixedWindowSegmenter(10.0).cuts(Path("x"), 10.0) == []


def test_fixed_window_rejects_a_non_positive_window() -> None:
    with pytest.raises(ValueError, match="window"):
        FixedWindowSegmenter(0)


def test_ac_01_scene_segmenter_finds_the_cuts_of_a_real_video(make_video: MakeVideo) -> None:
    video = make_video()  # three flat-colour shots, hard cuts at 4 s and 8 s
    cuts = SceneSegmenter(threshold=20.0).cuts(video, 12.0)
    assert len(cuts) == 2 and cuts[0] == pytest.approx(4.0, abs=0.3) and cuts[1] == pytest.approx(8.0, abs=0.3)


def test_plan_uses_the_requested_method_when_it_gives_enough_pieces() -> None:
    plan = plan_segments(Path("x"), 40.0, "scene", _registry(FakeSegmenter("scene", [10.0, 20.0, 30.0])))
    assert plan.method == "scene" and len(plan.bounds) == 4 and plan.notes == []


def test_ac_04_hand_activity_missing_falls_back_to_scene_without_crashing() -> None:
    registry = _registry(FakeSegmenter("scene", [10.0, 20.0, 30.0]))  # no hand_activity registered
    plan = plan_segments(Path("x"), 40.0, "hand_activity", registry)
    assert plan.method == "scene" and any("hand_activity" in n for n in plan.notes)


def test_ac_04_hand_activity_error_falls_back_to_scene() -> None:
    registry = _registry(
        FakeSegmenter("hand_activity", error="mediapipe aborted"), FakeSegmenter("scene", [10.0, 20.0])
    )
    plan = plan_segments(Path("x"), 30.0, "hand_activity", registry)
    assert plan.method == "scene" and any("mediapipe aborted" in n for n in plan.notes)


def test_scene_library_missing_falls_back_to_fixed_window() -> None:
    registry = _registry(FakeSegmenter("scene", error="thiếu scenedetect"), FakeSegmenter("fixed_window", [10.0, 20.0]))
    plan = plan_segments(Path("x"), 30.0, "scene", registry)
    assert plan.method == "fixed_window" and any("scenedetect" in n for n in plan.notes)


def test_too_few_scene_pieces_fall_back_to_fixed_window() -> None:
    # a single continuous shot: scene finds nothing, but AC-01 wants >= 3 pieces
    registry = _registry(FakeSegmenter("scene", []), FakeSegmenter("fixed_window", [10.0, 20.0]))
    plan = plan_segments(Path("x"), 30.0, "scene", registry)
    assert plan.method == "fixed_window" and len(plan.bounds) == 3 and any("ít hơn 3" in n for n in plan.notes)


def test_a_short_video_may_end_with_fewer_than_three_pieces() -> None:
    registry = _registry(FakeSegmenter("scene", []), FakeSegmenter("fixed_window", []))
    plan = plan_segments(Path("x"), 6.0, "scene", registry)
    assert plan.method == "fixed_window" and plan.bounds == [(0.0, 6.0)]


def test_unknown_method_is_an_error() -> None:
    with pytest.raises(ValueError, match="method"):
        plan_segments(Path("x"), 30.0, "magic", _registry(FakeSegmenter("scene")))


def test_ac_02_ac_03_hold_after_planning_a_real_video(make_video: MakeVideo) -> None:
    video = make_video(shots=[((200, 30, 30), 1.0), ((30, 200, 30), 30.0), ((30, 30, 200), 4.0)])
    registry: dict[str, Segmenter] = {"scene": SceneSegmenter(20.0), "fixed_window": FixedWindowSegmenter(10.0)}
    plan = plan_segments(video, 35.0, "scene", registry)
    assert all(MIN_SEGMENT_S <= e - s <= MAX_SEGMENT_S for s, e in plan.bounds)
    assert plan.bounds[0][0] == 0.0 and plan.bounds[-1][1] == pytest.approx(35.0)
    assert all(a[1] == b[0] for a, b in zip(plan.bounds, plan.bounds[1:], strict=False))


def test_scene_detection_does_not_drag_pyav_into_the_process(tmp_path: Path, make_video: MakeVideo) -> None:
    """scenedetect imports PyAV when it finds it, and on macOS PyAV's and OpenCV's wheels both bundle
    libavdevice, so the Objective-C runtime warns of duplicate classes ("mysterious crashes").
    We read with OpenCV only, so PyAV must stay out of the process that cuts scenes."""
    import subprocess
    import sys

    video = make_video()
    code = (
        "import sys\n"
        "from pathlib import Path\n"
        "from mentormind.capture.video.segmenters import SceneSegmenter\n"
        f"cuts = SceneSegmenter(20.0).cuts(Path({str(video)!r}), 12.0)\n"
        "assert len(cuts) == 2, cuts\n"
        "print('av-loaded:', 'av' in sys.modules)\n"
    )
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
    assert "av-loaded: False" in result.stdout
    assert "objc" not in result.stderr
