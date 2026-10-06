"""spec 03 FR-03 (`hand_activity`), AC-04 — cut where the worker's hands rest, isolated in a subprocess."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from mentormind.capture.video.hand_activity import (
    HandActivitySegmenter,
    valley_cuts,
    wrist_energy,
)
from mentormind.capture.video.segmenters import (
    FixedWindowSegmenter,
    SceneSegmenter,
    Segmenter,
    SegmenterError,
    plan_segments,
)
from tests.capture.video.conftest import MakeVideo

FPS = 5.0
HAND = [[0.5, 0.5]]


def _moving(n: int, start: float = 0.1) -> list[list[list[float]]]:
    return [[[start + 0.05 * i, 0.5]] for i in range(n)]  # wrist drifts 0.05 per sample


def _still(n: int, at: float = 0.5) -> list[list[list[float]]]:
    return [[[at, 0.5]] for _ in range(n)]


def _result(wrists: list[list[list[float]]], returncode: int = 0, stdout: str | None = None):
    payload = (
        stdout
        if stdout is not None
        else json.dumps({"sample_fps": FPS, "duration_s": len(wrists) / FPS, "wrists": wrists})
    )
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=payload, stderr="W0000 noise\nboom")


def _runs(*parts: tuple[float | None, int]) -> list[float | None]:
    """Build an energy series from (value, repeat) runs."""
    return [value for value, count in parts for _ in range(count)]


def _segmenter(response, **kw: object) -> HandActivitySegmenter:
    return HandActivitySegmenter(runner=lambda command, timeout: response, **kw)  # type: ignore[arg-type]


# --- energy -------------------------------------------------------------------------------------


def test_a_still_wrist_has_zero_energy_and_a_moving_one_has_positive_energy() -> None:
    assert wrist_energy(_still(4), FPS) == [0.0, 0.0, 0.0]
    assert wrist_energy(_moving(3), FPS) == pytest.approx([0.25, 0.25])  # 0.05 per sample * 5 samples/s


def test_energy_is_unknown_when_a_frame_has_no_hand() -> None:
    assert wrist_energy([HAND, [], HAND], FPS) == [None, None]


def test_hands_are_matched_by_nearest_wrist_not_by_order() -> None:
    a = [[0.1, 0.5], [0.9, 0.5]]
    b = [[0.9, 0.5], [0.1, 0.5]]  # same two wrists, listed in the other order
    assert wrist_energy([a, b], FPS) == [0.0]


# --- valleys ------------------------------------------------------------------------------------


def test_a_rest_of_at_least_0_4_s_gives_a_cut_at_its_middle() -> None:
    energy = _runs((1.0, 10), (0.0, 3), (1.0, 10))
    assert valley_cuts(energy, FPS, min_len_s=0.4, ratio=0.2) == [pytest.approx((10 + 13) / 2 / FPS)]


def test_a_rest_shorter_than_0_4_s_is_not_a_boundary() -> None:
    energy = _runs((1.0, 10), (0.0, 1), (1.0, 10))
    assert valley_cuts(energy, FPS, min_len_s=0.4, ratio=0.2) == []


def test_rests_are_relative_to_how_fast_this_worker_moves() -> None:
    slow = _runs((0.02, 10), (0.0, 3), (0.02, 10))  # a slow worker: 0.02 is still "moving"
    assert len(valley_cuts(slow, FPS, min_len_s=0.4, ratio=0.2)) == 1


def test_frames_without_a_visible_hand_count_as_rest() -> None:
    energy = _runs((1.0, 10), (None, 4), (1.0, 10))
    assert len(valley_cuts(energy, FPS, min_len_s=0.4, ratio=0.2)) == 1


def test_two_separate_rests_give_two_cuts() -> None:
    energy = _runs((1.0, 8), (0.0, 3), (1.0, 8), (0.0, 3), (1.0, 8))
    assert len(valley_cuts(energy, FPS, min_len_s=0.4, ratio=0.2)) == 2


def test_too_little_movement_to_judge_is_an_error() -> None:
    with pytest.raises(SegmenterError, match="chuyển động"):
        valley_cuts([None] * 30, FPS, min_len_s=0.4, ratio=0.2)


# --- the segmenter (worker output faked) --------------------------------------------------------


def test_cuts_come_from_the_rests_between_movements() -> None:
    wrists = _moving(20) + _still(3, at=0.9) + _moving(20, start=0.1) + _still(3, at=0.9) + _moving(20)
    cuts = _segmenter(_result(wrists)).cuts(Path("v.mp4"), len(wrists) / FPS)
    assert len(cuts) == 2 and cuts[0] == pytest.approx(21.5 / FPS, abs=0.5) and cuts == sorted(cuts)


def test_a_video_where_hands_are_rarely_seen_is_refused_with_the_measured_share() -> None:
    wrists = _moving(5) + [[] for _ in range(95)]  # 5% of the samples
    with pytest.raises(SegmenterError, match=r"5%"):
        _segmenter(_result(wrists)).cuts(Path("v.mp4"), 20.0)


def test_the_presence_threshold_is_configurable() -> None:
    wrists = _moving(20) + _still(3, at=0.9) + _moving(20) + [[] for _ in range(100)]  # about 30% seen
    assert _segmenter(_result(wrists), min_presence=0.25).cuts(Path("v.mp4"), 30.0)
    with pytest.raises(SegmenterError, match="tay"):
        _segmenter(_result(wrists), min_presence=0.5).cuts(Path("v.mp4"), 30.0)


@pytest.mark.parametrize("code", [-6, 134, 1])
def test_a_worker_that_dies_is_a_segmenter_error_with_the_exit_code(code: int) -> None:
    with pytest.raises(SegmenterError, match=rf"{code}"):
        _segmenter(_result([], returncode=code, stdout="")).cuts(Path("v.mp4"), 10.0)


def test_garbage_output_is_a_segmenter_error() -> None:
    with pytest.raises(SegmenterError, match="JSON"):
        _segmenter(_result([], stdout="not json")).cuts(Path("v.mp4"), 10.0)


def test_a_timeout_is_a_segmenter_error() -> None:
    def slow(command: list[str], timeout: float) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired(command, timeout)

    with pytest.raises(SegmenterError, match="quá"):
        HandActivitySegmenter(runner=slow, timeout_s=5).cuts(Path("v.mp4"), 10.0)


def test_without_uv_or_a_configured_python_the_error_says_what_to_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("mentormind.capture.video.hand_activity.shutil.which", lambda name: None)
    with pytest.raises(SegmenterError, match="KNOWHOW_HAND_PYTHON"):
        HandActivitySegmenter(runner=lambda c, t: _result([])).cuts(Path("v.mp4"), 10.0)


def test_a_configured_python_is_used_instead_of_uv() -> None:
    seen: list[list[str]] = []

    def runner(command: list[str], timeout: float) -> subprocess.CompletedProcess[str]:
        seen.append(command)
        return _result(_moving(20) + _still(3, at=0.9) + _moving(20))

    HandActivitySegmenter(python="/opt/venv/bin/python", runner=runner).cuts(Path("v.mp4"), 8.6)
    assert seen[0][0] == "/opt/venv/bin/python" and seen[0][-1] == "v.mp4" and "uv" not in seen[0][0]


def test_without_a_configured_python_the_worker_runs_in_an_isolated_uv_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("mentormind.capture.video.hand_activity.shutil.which", lambda name: "/usr/bin/uv")
    seen: list[list[str]] = []

    def runner(command: list[str], timeout: float) -> subprocess.CompletedProcess[str]:
        seen.append(command)
        return _result(_moving(20) + _still(3, at=0.9) + _moving(20))

    HandActivitySegmenter(runner=runner).cuts(Path("v.mp4"), 8.6)
    command = seen[0]
    assert command[:3] == ["/usr/bin/uv", "run", "--no-project"] and "mediapipe==0.10.21" in command


# --- isolation, with a REAL subprocess ----------------------------------------------------------


def test_a_native_abort_in_the_worker_does_not_take_the_parent_down(tmp_path: Path) -> None:
    crash = tmp_path / "crash.py"
    crash.write_text("import os, sys\nprint('partial', flush=True)\nos.abort()\n")  # SIGABRT, like mediapipe 1.0.x
    segmenter = HandActivitySegmenter(python=sys.executable, worker=crash)
    with pytest.raises(SegmenterError, match=r"-6|134"):
        segmenter.cuts(Path("v.mp4"), 10.0)
    assert os.getpid() > 0  # still alive, and the chain can fall back:
    registry: dict[str, Segmenter] = {
        "hand_activity": segmenter,
        "scene": FixedWindowSegmenter(10.0),
        "fixed_window": FixedWindowSegmenter(10.0),
    }
    plan = plan_segments(Path("v.mp4"), 35.0, "hand_activity", registry)
    assert plan.method == "scene" and any("hand_activity" in n for n in plan.notes)


def test_a_real_subprocess_returning_valid_json_is_parsed(tmp_path: Path) -> None:
    wrists = _moving(20) + _still(3, at=0.9) + _moving(20)
    fake = tmp_path / "fake_worker.py"
    fake.write_text(
        f"import json\nprint(json.dumps({{'sample_fps': {FPS}, 'duration_s': 8.6, 'wrists': {wrists!r}}}))\n"
    )
    cuts = HandActivitySegmenter(python=sys.executable, worker=fake).cuts(Path("v.mp4"), 8.6)
    assert len(cuts) == 1


def test_hand_activity_cuts_flow_through_plan_segments() -> None:
    wrists = _moving(30) + _still(3, at=0.9) + _moving(30) + _still(3, at=0.9) + _moving(30)  # ~19 s, two rests
    hand = _segmenter(_result(wrists))
    scene_never_used = SceneSegmenter(20.0)
    plan = plan_segments(
        Path("v.mp4"), 19.0, "hand_activity",
        {"hand_activity": hand, "scene": scene_never_used, "fixed_window": FixedWindowSegmenter(10.0)},
    )  # fmt: skip
    assert plan.method == "hand_activity" and plan.notes == [] and len(plan.bounds) == 3


# --- the real MediaPipe worker (slow, needs `uv` and a network on first use) ---------------------

pytestmark_real = pytest.mark.skipif(
    os.environ.get("KNOWHOW_RUN_SAMPLE_TESTS") != "1", reason="runs real MediaPipe: set KNOWHOW_RUN_SAMPLE_TESTS=1"
)


@pytestmark_real
def test_the_real_worker_runs_in_its_own_environment_and_reports_no_hands_on_a_synthetic_video(
    make_video: MakeVideo,
) -> None:
    video = make_video()
    cuts = None
    with pytest.raises(SegmenterError, match="tay"):  # flat colours: no hand anywhere → refused, not crashed
        cuts = HandActivitySegmenter(min_presence=0.1).cuts(video, 12.0)
    assert cuts is None
