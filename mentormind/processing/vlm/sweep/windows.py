"""Fixed-window segments for ``knowhow vlm sweep`` until the spec 03 segmenter lands.

Spec 03 FR-03 lists ``fixed_window`` (10 s) as the fallback strategy; this is only that strategy,
so the sweep can run on a raw video today. Once ``knowhow video segment`` exists, sweep takes its
``segments.json`` instead (``--segments``). Clips are cut with ffmpeg (spec 03 FR-06), downscaled
to 640 px because the VLM only ever sees 448 px frames.
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
    """Cut ``video`` into ``window_s`` clips under ``out_dir`` (cached) and describe them."""
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("Cần ffmpeg trong PATH để cắt clip (spec 03 FR-06).")
    vid = video_id or video_id_for(video)
    out_dir.mkdir(parents=True, exist_ok=True)
    segments = []
    for index, (start, end) in enumerate(window_bounds(video_duration(video), window_s), start=1):
        clip = out_dir / f"{vid}-S{index:03d}.mp4"
        if not clip.exists():
            _cut(video, clip, start, end)
        segments.append(
            Segment(
                segment_id=f"{vid}-S{index:03d}",
                video_id=vid,
                index=index,
                t_start=round(start, 3),
                t_end=round(end, 3),
                method="fixed_window",
                motion_score=None,
                keyframes=[],
                clip_path=str(clip),
                data_classification=classification,
            )
        )
    return segments


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
