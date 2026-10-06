"""Cut strategies and the fallback chain (spec 03 FR-03, FR-04, AC-04).

A :class:`Segmenter` only proposes interior cut times; :func:`plan_segments` turns them into
3–20 s pieces and decides when to fall back (constitution art. 5: tools behind an interface).
"""

from __future__ import annotations

import sys
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from mentormind.capture.video.postprocess import Bounds, bounds_from_cuts, postprocess

MIN_SEGMENTS = 3  # spec 03 AC-01
_SCENE_MIN_LEN_FRAMES = 15  # ~0.5 s: PySceneDetect ignores cuts closer than this


class SegmenterError(Exception):
    """A strategy cannot run (library missing, tool crashed); the chain falls back."""


class Segmenter(Protocol):
    method: str

    def cuts(self, video: Path, duration: float) -> list[float]:
        """Interior cut times in seconds, ascending.

        Raises:
            SegmenterError: the strategy is unavailable or failed.
        """
        ...


class FixedWindowSegmenter:
    method = "fixed_window"

    def __init__(self, window_s: float = 10.0) -> None:
        if window_s <= 0:
            raise ValueError(f"window phải > 0, nhận {window_s}.")
        self._window = window_s

    def cuts(self, video: Path, duration: float) -> list[float]:
        count = int((duration - 1e-6) // self._window)
        return [round(i * self._window, 3) for i in range(1, count + 1)]


class SceneSegmenter:
    method = "scene"

    def __init__(self, threshold: float = 20.0) -> None:
        self._threshold = threshold

    def cuts(self, video: Path, duration: float) -> list[float]:
        try:
            with _without_pyav():
                from scenedetect import ContentDetector, detect
        except ImportError as exc:
            raise SegmenterError("Thiếu scenedetect: cài extra `video` (uv sync --extra video).") from exc
        try:
            scenes = detect(str(video), ContentDetector(threshold=self._threshold, min_scene_len=_SCENE_MIN_LEN_FRAMES))
        except Exception as exc:  # scenedetect raises many unrelated types for unreadable input
            raise SegmenterError(f"PySceneDetect lỗi trên {video.name}: {exc}") from exc
        return [round(start.get_seconds(), 3) for start, _ in scenes[1:]]


@contextmanager
def _without_pyav() -> Iterator[None]:
    """Keep PyAV out of the process while ``scenedetect`` is imported.

    ``scenedetect`` treats PyAV as an optional backend and loads it when present (it is, through
    faster-whisper). We read with OpenCV only, and on macOS the PyAV and OpenCV wheels both bundle
    libavdevice, so loading both makes the Objective-C runtime warn of duplicate classes that "may
    cause spurious casting failures and mysterious crashes". A ``None`` entry in ``sys.modules``
    makes ``import av`` raise ``ImportError``, which ``scenedetect`` already handles.
    """
    if "av" in sys.modules:  # already loaded (e.g. by faster-whisper in this process): nothing to hide
        yield
        return
    sys.modules["av"] = None  # type: ignore[assignment]
    try:
        yield
    finally:
        sys.modules.pop("av", None)


@dataclass
class SegmentPlan:
    bounds: Bounds
    #: The strategy that actually produced ``bounds`` (may differ from the one requested).
    method: str
    #: Why the plan fell back, for the run log.
    notes: list[str] = field(default_factory=list)


def plan_segments(video: Path, duration: float, method: str, segmenters: dict[str, Segmenter]) -> SegmentPlan:
    """Cut ``video`` with ``method``; fall back along hand_activity → scene → fixed_window.

    Falls back when a strategy is missing or fails (AC-04), and from ``scene`` when it leaves
    fewer than 3 pieces (a single continuous shot, spec 03b D1). ``fixed_window`` is the end of
    the chain: a short video may legitimately end up with fewer than 3 pieces.

    Raises:
        ValueError: ``method`` is not a known strategy name.
    """
    chain = ["hand_activity", "scene", "fixed_window"]
    if method not in chain:
        raise ValueError(f"method không hợp lệ: {method!r} (chọn một trong {', '.join(chain)}).")
    notes: list[str] = []
    for name in chain[chain.index(method) :]:
        segmenter = segmenters.get(name)
        if segmenter is None:
            notes.append(f"{name}: chưa có sẵn, chuyển sang chiến lược kế tiếp")
            continue
        try:
            bounds = postprocess(bounds_from_cuts(segmenter.cuts(video, duration), duration), duration)
        except SegmenterError as exc:
            notes.append(f"{name}: {exc}")
            continue
        if len(bounds) < MIN_SEGMENTS and name != "fixed_window":
            notes.append(f"{name}: chỉ ra {len(bounds)} đoạn (ít hơn 3), chuyển sang chiến lược kế tiếp")
            continue
        return SegmentPlan(bounds=bounds, method=name, notes=notes)
    raise SegmenterError("; ".join(notes) or "Không có chiến lược cắt nào chạy được.")
