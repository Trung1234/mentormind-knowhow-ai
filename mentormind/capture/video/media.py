"""Keyframes (spec 03 FR-05) and clips (FR-06) with ffmpeg.

Files are written under a ``.part`` name and renamed, so a crash never leaves a half-written
output that a later run would reuse. Existing non-empty outputs are reused unless ``force``.
"""

from __future__ import annotations

import subprocess
from collections.abc import Callable
from pathlib import Path

KEYFRAME_LONG_SIDE = 768
CLIP_LONG_SIDE = 640
KEYFRAME_EDGE_S = 0.1  # offset from the boundaries: the boundary frame often belongs to the next shot
Runner = Callable[[list[str]], None]


class MediaError(Exception):
    """ffmpeg could not produce a file; the message names the segment and what to do."""


def keyframe_times(t_start: float, t_end: float) -> list[float]:
    """Start, middle and end of a segment, nudged inward so no frame sits on a cut."""
    edge = min(KEYFRAME_EDGE_S, (t_end - t_start) / 4)
    return [t_start + edge, (t_start + t_end) / 2, t_end - edge]


def export_keyframes(
    video: Path,
    t_start: float,
    t_end: float,
    segment_id: str,
    out_dir: Path,
    *,
    ffmpeg: str = "ffmpeg",
    runner: Runner | None = None,
    force: bool = False,
) -> list[Path]:
    """Three JPGs (long side at most 768 px, never upscaled) named ``<segment_id>-{0,1,2}.jpg``."""
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for i, t in enumerate(keyframe_times(t_start, t_end)):
        target = out_dir / f"{segment_id}-{i}.jpg"
        command = [
            ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-ss", f"{t:.3f}", "-i", str(video),
            "-frames:v", "1", "-vf", _scale(KEYFRAME_LONG_SIDE), "-q:v", "3",
        ]  # fmt: skip
        _produce(command, target, segment_id, runner, force)
        paths.append(target)
    return paths


def export_clip(
    video: Path,
    t_start: float,
    t_end: float,
    segment_id: str,
    out_dir: Path,
    *,
    ffmpeg: str = "ffmpeg",
    runner: Runner | None = None,
    force: bool = False,
    copy: bool = False,
) -> Path:
    """``<segment_id>.mp4``: re-encoded H.264 without audio, long side at most 640 px.

    ``copy=True`` uses ``-c copy`` instead: faster, but it can only cut on the source's keyframes,
    which sit 2–5 s apart, so the boundaries drift (docs/plans/03-spike-notes.md).
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / f"{segment_id}.mp4"
    codec = (
        ["-c", "copy"]
        if copy
        else [
            "-vf",
            _scale(CLIP_LONG_SIDE),
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "23",
            "-pix_fmt",
            "yuv420p",
        ]
    )
    command = [
        ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-ss", f"{t_start:.3f}", "-i", str(video),
        "-t", f"{t_end - t_start:.3f}", "-an", *codec,
    ]  # fmt: skip
    _produce(command, target, segment_id, runner, force)
    return target


def _scale(long_side: int) -> str:
    return f"scale='if(gt(iw,ih),min({long_side},iw),-2)':'if(gt(iw,ih),-2,min({long_side},ih))'"


def _produce(command: list[str], target: Path, segment_id: str, runner: Runner | None, force: bool) -> None:
    if not force and target.is_file() and target.stat().st_size > 0:
        return
    partial = target.with_name(f"{target.stem}.part{target.suffix}")
    try:
        (runner or _run)([*command, str(partial)])
        partial.replace(target)
    except FileNotFoundError as exc:
        raise MediaError(
            f"{segment_id}: không chạy được {command[0]!r}: cài ffmpeg (macOS: `brew install ffmpeg`)."
        ) from exc
    except MediaError as exc:
        partial.unlink(missing_ok=True)
        raise MediaError(f"{segment_id}: {exc}") from exc
    except subprocess.CalledProcessError as exc:
        partial.unlink(missing_ok=True)
        raise MediaError(f"{segment_id}: ffmpeg lỗi: {(exc.stderr or str(exc)).strip()}") from exc


def _run(command: list[str]) -> None:
    subprocess.run(command, check=True, capture_output=True, text=True)
