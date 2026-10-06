"""``hand_activity``: cut where the worker's hands rest (spec 03 FR-03, Should).

A worker repeats one movement, pauses a moment, then starts the next. Cutting in the pauses gives
one whole movement per segment for the VLM instead of a fixed window that may split it in two. On a
station camera that films one long shot this is the only strategy that follows the work: ``scene``
finds no cuts there.

Hand detection runs in a separate process and Python environment (``hand_worker.py``): MediaPipe
1.0.x aborts natively on macOS and 0.10.x pins ``numpy<2`` (docs/plans/03-spike-notes.md). A crash,
a timeout or a missing tool becomes a :class:`SegmenterError`, so the chain falls back to ``scene``
(AC-04). Everything that decides *where to cut* lives here, in plain Python, and is tested without
MediaPipe.
"""

from __future__ import annotations

import json
import math
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np

from mentormind.capture.video.segmenters import SegmenterError

MEDIAPIPE_PIN = "mediapipe==0.10.21"  # last release with the `solutions.hands` API
WORKER = Path(__file__).with_name("hand_worker.py")
_MIN_KNOWN_PAIRS = 5  # fewer movements than this say nothing about this worker's rhythm
Runner = Callable[[list[str], float], "subprocess.CompletedProcess[str]"]


def wrist_energy(wrists: list[list[list[float]]], fps: float) -> list[float | None]:
    """Wrist speed (normalised image units per second) between each pair of consecutive samples.

    Each wrist is matched to the nearest wrist of the previous sample, so the order MediaPipe lists
    them in does not matter. ``None`` when either sample shows no hand: the speed is unknown.
    """
    energy: list[float | None] = []
    for before, after in zip(wrists, wrists[1:], strict=False):
        if not before or not after:
            energy.append(None)
            continue
        steps = [min(math.dist(point, other) for other in before) for point in after]
        energy.append(sum(steps) / len(steps) * fps)
    return energy


def valley_cuts(energy: list[float | None], fps: float, *, min_len_s: float, ratio: float) -> list[float]:
    """Cut times at the middle of every rest: a run of at least ``min_len_s`` of slow wrists.

    "Slow" is relative to this worker: below ``ratio`` times the 75th percentile of their own
    speeds. Samples without a visible hand count as rest. Pair ``i`` spans ``[i, i + 1] / fps`` s.

    Raises:
        SegmenterError: too few measurable movements to judge the rhythm.
    """
    known = [e for e in energy if e is not None]
    if len(known) < _MIN_KNOWN_PAIRS:
        raise SegmenterError(f"quá ít chuyển động của tay để xác định nhịp ({len(known)} lần đo).")
    threshold = ratio * float(np.percentile(known, 75))
    cuts: list[float] = []
    run_start: int | None = None
    for i, value in enumerate([*energy, math.inf]):  # the sentinel closes a run that reaches the end
        slow = value is None or value < threshold
        if slow and run_start is None:
            run_start = i
        elif not slow and run_start is not None:
            if (i - run_start) / fps >= min_len_s - 1e-9:
                cuts.append(round((run_start + i) / 2 / fps, 3))
            run_start = None
    return cuts


class HandActivitySegmenter:
    method = "hand_activity"

    def __init__(
        self,
        *,
        python: str | None = None,
        worker: Path | None = None,
        min_presence: float = 0.1,
        valley_min_s: float = 0.4,
        valley_ratio: float = 0.2,
        timeout_s: float = 600.0,
        runner: Runner | None = None,
    ) -> None:
        self._python = python
        self._worker = worker or WORKER
        self._min_presence = min_presence
        self._valley_min_s = valley_min_s
        self._valley_ratio = valley_ratio
        self._timeout_s = timeout_s
        self._runner = runner or _run

    def cuts(self, video: Path, duration: float) -> list[float]:
        detections = self._detect(video)
        wrists: list[list[list[float]]] = detections["wrists"]
        fps = float(detections["sample_fps"])
        seen = sum(1 for sample in wrists if sample)
        presence = seen / len(wrists) if wrists else 0.0
        if presence < self._min_presence:
            raise SegmenterError(f"hầu như không thấy tay ({presence:.0%} số khung, cần ≥ {self._min_presence:.0%}).")
        cuts = valley_cuts(wrist_energy(wrists, fps), fps, min_len_s=self._valley_min_s, ratio=self._valley_ratio)
        return [c for c in cuts if 0 < c < duration]

    def _command(self, video: Path) -> list[str]:
        if self._python:
            return [self._python, str(self._worker), str(video)]
        uv = shutil.which("uv")
        if uv is None:
            raise SegmenterError(
                "cần `uv` trong PATH để chạy MediaPipe trong môi trường riêng, "
                "hoặc đặt KNOWHOW_HAND_PYTHON trỏ tới Python đã cài mediapipe 0.10.x."
            )
        return [
            uv, "run", "--no-project", "--python", "3.11", "--quiet",
            "--with", MEDIAPIPE_PIN, "python", str(self._worker), str(video),
        ]  # fmt: skip

    def _detect(self, video: Path) -> dict[str, Any]:
        command = self._command(video)
        try:
            result = self._runner(command, self._timeout_s)
        except subprocess.TimeoutExpired as exc:
            raise SegmenterError(f"MediaPipe chạy quá {self._timeout_s:g}s trên {video.name}.") from exc
        except OSError as exc:
            raise SegmenterError(f"không chạy được {command[0]!r}: {exc}") from exc
        if result.returncode != 0:
            tail = (result.stderr or "").strip().splitlines()[-1:] or ["(không có thông báo)"]
            raise SegmenterError(f"tiến trình MediaPipe dừng đột ngột (mã {result.returncode}): {tail[0][:200]}")
        try:
            data = json.loads(result.stdout)
            wrists = data["wrists"]
            if not isinstance(wrists, list) or float(data["sample_fps"]) <= 0:
                raise ValueError("định dạng sai")
        except (ValueError, KeyError, TypeError) as exc:
            raise SegmenterError(f"kết quả của worker không phải JSON hợp lệ ({exc}).") from exc
        return data


def _run(command: list[str], timeout: float) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)
