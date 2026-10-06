"""Fixed-window segments for ``knowhow vlm sweep``/``describe --video`` until the spec 03 segmenter lands.

Spec 03 FR-03 lists ``fixed_window`` (10 s) as the fallback strategy; this is only that strategy,
so the sweep can run on a raw video today. Once ``knowhow video segment`` exists, sweep takes its
``segments.json`` instead (``--segments``). Clips are cut with ffmpeg (spec 03 FR-06), downscaled
to 640 px because the VLM only ever sees 448 px frames; keyframes follow spec 03 FR-05.
"""

from __future__ import annotations

import hashlib
import shutil
import subprocess
from pathlib import Path

import cv2

from mentormind.core.schemas.common import DataClassification
from mentormind.core.schemas.video import Segment

MIN_SEGMENT_S = 3.0  # spec 03 FR-04: shorter tail windows merge into the previous one
KEYFRAME_LONG_SIDE = 768  # spec 03 FR-05
KEYFRAME_END_MARGIN_S = 0.05
KEYFRAME_RETRY_BACK_S = 0.5


def video_id_for(path: Path) -> str:
    """``VID-`` + sha256[:12] of the file (spec 03 §3)."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return f"VID-{digest.hexdigest()[:12]}"


def video_duration(path: Path) -> float:
    capture = cv2.VideoCapture(str(path))
    try:
        frames = capture.get(cv2.CAP_PROP_FRAME_COUNT)
        fps = capture.get(cv2.CAP_PROP_FPS) or 0.0
    finally:
        capture.release()
    if frames <= 0 or fps <= 0:
        raise ValueError(f"Không đọc được thời lượng video {path}")
    return float(frames / fps)


def window_bounds(duration: float, window_s: float) -> list[tuple[float, float]]:
    bounds: list[tuple[float, float]] = []
    start = 0.0
    while start < duration - 1e-6:
        end = min(start + window_s, duration)
        if bounds and end - start < MIN_SEGMENT_S:
            bounds[-1] = (bounds[-1][0], end)
        else:
            bounds.append((start, end))
        start = end
    return bounds


def fixed_window_segments(
    video: Path,
    *,
    out_dir: Path,
    classification: DataClassification,
    window_s: float = 10.0,
    video_id: str | None = None,
) -> list[Segment]:
    """Cut ``video`` into ``window_s`` clips under ``out_dir`` and describe them.

    Each window also gets 3 keyframes (spec 03 FR-05) in ``out_dir``'s sibling ``keyframes/``.
    Clips and keyframes are cached: a second run only reads the video for what is missing.
    """
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("Cần ffmpeg trong PATH để cắt clip (spec 03 FR-06).")
    vid = video_id or video_id_for(video)
    out_dir.mkdir(parents=True, exist_ok=True)
    frames = _FrameReader(video)
    segments = []
    try:
        for index, (start, end) in enumerate(window_bounds(video_duration(video), window_s), start=1):
            segment_id = f"{vid}-S{index:03d}"
            clip = out_dir / f"{segment_id}.mp4"
            if not clip.exists():
                _cut(video, clip, start, end)
            keyframes = _keyframes(frames, out_dir.parent / "keyframes", segment_id, start, end)
            segments.append(
                Segment(
                    segment_id=segment_id,
                    video_id=vid,
                    index=index,
                    t_start=round(start, 3),
                    t_end=round(end, 3),
                    method="fixed_window",
                    motion_score=None,
                    keyframes=[str(path) for path in keyframes],
                    clip_path=str(clip),
                    data_classification=classification,
                )
            )
    finally:
        frames.close()
    return segments


class _FrameReader:
    """Frames of a video by time; the file is opened on first use, so cached keyframes cost nothing."""

    def __init__(self, video: Path) -> None:
        self._video = video
        self._capture: cv2.VideoCapture | None = None

    def at(self, t: float) -> cv2.typing.MatLike | None:
        if self._capture is None:
            self._capture = cv2.VideoCapture(str(self._video))
        self._capture.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
        ok, frame = self._capture.read()
        return frame if ok else None

    def close(self) -> None:
        if self._capture is not None:
            self._capture.release()


def _keyframes(frames: _FrameReader, out_dir: Path, segment_id: str, start: float, end: float) -> list[Path]:
    """Start, middle and end of a window as JPG, long side at most 768 px (spec 03 FR-05)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    # The last one sits just before ``end``: the frame at ``end`` opens the next window.
    times = (start, (start + end) / 2, max(start, end - KEYFRAME_END_MARGIN_S))
    paths = []
    for position, t in enumerate(times):
        path = out_dir / f"{segment_id}_k{position}.jpg"
        if not path.exists():
            frame = frames.at(t)
            if frame is None and t > start:  # the very end of a file is not always seekable
                frame = frames.at(max(start, t - KEYFRAME_RETRY_BACK_S))
            if frame is None:  # unreadable position: one keyframe fewer, the segment itself is fine
                continue
            cv2.imwrite(str(path), _fit(frame, KEYFRAME_LONG_SIDE))
        paths.append(path)
    return paths


def _fit(frame: cv2.typing.MatLike, long_side: int) -> cv2.typing.MatLike:
    height, width = frame.shape[:2]
    scale = long_side / max(height, width)
    if scale >= 1:
        return frame
    return cv2.resize(frame, (round(width * scale), round(height * scale)), interpolation=cv2.INTER_AREA)


def _cut(video: Path, clip: Path, start: float, end: float) -> None:
    tmp = clip.with_suffix(".part.mp4")
    subprocess.run(
        [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-ss", f"{start:.3f}", "-i", str(video), "-t", f"{end - start:.3f}",
            "-an", "-vf", "scale=640:-2", "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
            str(tmp),
        ],
        check=True,
    )  # fmt: skip
    tmp.replace(clip)
