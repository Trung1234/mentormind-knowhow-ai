"""Tiny synthetic videos so video tests need no real footage (constitution art. 6)."""

from __future__ import annotations

import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path

import cv2
import numpy as np
import pytest

FFMPEG = shutil.which("ffmpeg") is not None
needs_ffmpeg = pytest.mark.skipif(not FFMPEG, reason="ffmpeg/ffprobe not installed")

Colour = tuple[int, int, int]
MakeVideo = Callable[..., Path]


def write_video(
    path: Path,
    shots: list[tuple[Colour, float]],
    *,
    fps: int = 10,
    size: tuple[int, int] = (320, 180),
    still: bool = False,
) -> Path:
    """One flat colour per shot (a hard cut between shots) with a bar that moves unless ``still``."""
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter.fourcc(*"mp4v"), fps, size)
    for colour, seconds in shots:
        for i in range(int(round(seconds * fps))):
            frame = np.full((size[1], size[0], 3), colour, dtype=np.uint8)
            x = 0 if still else (i * 7) % (size[0] - 20)
            frame[:, x : x + 20] = (255 - colour[0], 255 - colour[1], 255 - colour[2])
            writer.write(frame)
    writer.release()
    return path


@pytest.fixture
def make_video(tmp_path: Path) -> MakeVideo:
    def _make(
        name: str = "v.mp4",
        shots: list[tuple[Colour, float]] | None = None,
        *,
        audio: bool = False,
        still: bool = False,
    ) -> Path:
        shots = shots or [((200, 30, 30), 4.0), ((30, 200, 30), 4.0), ((30, 30, 200), 4.0)]
        path = write_video(tmp_path / name, shots, still=still)
        if not audio:
            return path
        muxed = tmp_path / f"a_{name}"
        subprocess.run(
            ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(path), "-f", "lavfi",
             "-i", "sine=frequency=440:duration=30", "-shortest", "-c:v", "copy", "-c:a", "aac", str(muxed)],
            check=True,
        )  # fmt: skip
        return muxed

    return _make
