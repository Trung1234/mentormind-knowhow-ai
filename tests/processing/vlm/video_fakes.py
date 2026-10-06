"""Synthetic videos and a stand-in for ffmpeg, for the fixed-window fallback (spec 04 FR-05)."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest

from mentormind.processing.vlm.sweep import windows


def synthetic_video(path: Path, seconds: float, *, fps: int = 4, size: tuple[int, int] = (64, 48)) -> Path:
    """An mp4 whose frames get brighter over time (OpenCV only, no ffmpeg needed)."""
    width, height = size
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter.fourcc(*"mp4v"), fps, (width, height))
    for i in range(round(seconds * fps)):
        writer.write(np.full((height, width, 3), (i * 9) % 256, dtype=np.uint8))
    writer.release()
    return path


def fake_ffmpeg(monkeypatch: pytest.MonkeyPatch) -> None:
    """Clips come from ffmpeg in real runs; here each clip is a small synthetic video of the window's length."""
    monkeypatch.setattr(windows.shutil, "which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr(windows, "_cut", lambda video, clip, start, end: synthetic_video(clip, end - start))
