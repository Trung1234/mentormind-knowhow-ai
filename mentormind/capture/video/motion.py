"""``Segment.motion_score``: how much a segment moves, 0..1 (spec 03 FR-09, AC-10).

Spec 04 picks the VLM sampling rate from this score (>= 0.6 → 8 fps, < 0.3 → 2 fps), so it must be
absolute, not normalised per video. ffmpeg decodes the video once at 5 fps into 160x90 gray frames;
the mean absolute difference between consecutive frames, divided by 255, is the raw motion of one
pair. A segment's raw motion is the **median** of the pairs inside it: a hard cut is one huge
difference that would inflate a mean, and the median separated hand-labelled work scenes from
interviews and logos best on the LASI video (AUC 0.93, docs/plans/03-spike-notes.md).
"""

from __future__ import annotations

import statistics
import subprocess
from collections.abc import Iterable, Iterator
from pathlib import Path

import numpy as np

from mentormind.capture.video.media import MediaError

SAMPLE_FPS = 5.0
FRAME_WIDTH = 160
FRAME_HEIGHT = 90  # fixed (aspect ignored): a difference between two frames does not need it
FRAME_BYTES = FRAME_WIDTH * FRAME_HEIGHT


def ffmpeg_gray_frames(video: Path, *, ffmpeg: str = "ffmpeg") -> Iterator[bytes]:
    """Yield raw gray frames of ``video`` at 5 fps, one ``FRAME_BYTES`` chunk each (streamed).

    Raises:
        MediaError: ffmpeg is missing or fails.
    """
    command = [
        ffmpeg, "-hide_banner", "-loglevel", "error", "-i", str(video),
        "-vf", f"fps={SAMPLE_FPS},scale={FRAME_WIDTH}:{FRAME_HEIGHT},format=gray", "-f", "rawvideo", "-",
    ]  # fmt: skip
    try:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except FileNotFoundError as exc:
        raise MediaError(f"Không chạy được {ffmpeg!r}: cài ffmpeg (macOS: `brew install ffmpeg`).") from exc
    assert process.stdout is not None and process.stderr is not None
    try:
        while len(frame := process.stdout.read(FRAME_BYTES)) == FRAME_BYTES:
            yield frame
    finally:
        process.stdout.close()
        error = process.stderr.read().decode(errors="replace").strip()
        process.stderr.close()
        if process.wait() != 0:
            raise MediaError(f"ffmpeg lỗi khi đọc {video.name} để tính motion_score: {error}")


def motion_profile(frames: Iterable[bytes]) -> list[float]:
    """Mean absolute difference (0..1) between each pair of consecutive frames.

    Pair ``i`` spans ``[i / SAMPLE_FPS, (i + 1) / SAMPLE_FPS]`` seconds.
    """
    diffs: list[float] = []
    previous: np.ndarray | None = None
    for raw in frames:
        current = np.frombuffer(raw, dtype=np.uint8).astype(np.float32)
        if previous is not None:
            diffs.append(float(np.abs(current - previous).mean() / 255.0))
        previous = current
    return diffs


def motion_score(diffs: list[float], t_start: float, t_end: float, *, scale: float) -> float | None:
    """Median difference of the pairs fully inside ``[t_start, t_end]``, divided by ``scale``, clipped to 0..1.

    ``None`` when no complete pair fits (a segment shorter than 0.4 s, or past the end of the video).

    Raises:
        ValueError: ``scale`` is not positive.
    """
    if scale <= 0:
        raise ValueError(f"scale phải > 0, nhận {scale}.")
    first = int(np.ceil(t_start * SAMPLE_FPS - 1e-6))
    last = int(np.floor(t_end * SAMPLE_FPS + 1e-6))  # exclusive end index of pairs
    inside = diffs[first : min(last, len(diffs))]
    if not inside:
        return None
    return round(min(1.0, statistics.median(inside) / scale), 4)
