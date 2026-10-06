"""``knowhow video probe``: ffprobe a file into a :class:`VideoAsset` (spec 03 FR-01)."""

from __future__ import annotations

import hashlib
import json
import subprocess
from collections.abc import Callable
from pathlib import Path

from mentormind.core.schemas import DataClassification
from mentormind.core.schemas.video import VideoAsset

_HASH_BLOCK = 1 << 20
Runner = Callable[[list[str]], str]


class ProbeError(Exception):
    """The file cannot be read as a video; the message says why and what to do."""


def video_id_for(path: Path) -> str:
    """``VID-`` + sha256[:12] of the file bytes (spec 03 §3), stable across machines."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(_HASH_BLOCK):
            digest.update(block)
    return f"VID-{digest.hexdigest()[:12]}"


def probe(
    path: Path,
    *,
    process_id: str | None,
    classification: DataClassification,
    ffprobe: str = "ffprobe",
    runner: Runner | None = None,
) -> VideoAsset:
    """Read duration, fps and audio presence with ffprobe.

    Raises:
        ProbeError: file missing, ffprobe not installed, or the output has no video stream.
    """
    if not path.is_file():
        raise ProbeError(f"Không thấy file video: {path}")
    command = [ffprobe, "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(path)]
    try:
        output = (runner or _run)(command)
    except FileNotFoundError as exc:
        raise ProbeError(f"Không chạy được {ffprobe!r}: cài ffmpeg (macOS: `brew install ffmpeg`).") from exc
    except subprocess.CalledProcessError as exc:
        raise ProbeError(f"{path.name}: ffprobe không đọc được file ({exc.stderr.strip() or exc})") from exc
    try:
        info = json.loads(output)
        streams = info["streams"]
        video = next(s for s in streams if s.get("codec_type") == "video")
        return VideoAsset(
            video_id=video_id_for(path),
            path=str(path),
            duration_s=float(info["format"]["duration"]),
            fps=_fps(video.get("avg_frame_rate") or video.get("r_frame_rate") or ""),
            has_audio=any(s.get("codec_type") == "audio" for s in streams),
            process_id=process_id,
            data_classification=classification,
        )
    except (ValueError, KeyError, StopIteration, ZeroDivisionError) as exc:
        raise ProbeError(f"{path.name}: không có luồng video hợp lệ trong kết quả ffprobe.") from exc


def _fps(rate: str) -> float:
    numerator, _, denominator = rate.partition("/")
    value = float(numerator) / float(denominator or 1)
    if value <= 0:
        raise ValueError(rate)
    return value


def _run(command: list[str]) -> str:
    return subprocess.run(command, check=True, capture_output=True, text=True).stdout
