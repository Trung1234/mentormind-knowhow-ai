"""Segments ``describe`` runs on: spec 03's ``segments.json``, or the fixed-window fallback (FR-05).

Until spec 03's ``knowhow video segment`` exists, a raw video is cut into 10 s windows (clip + 3
keyframes each, ``sweep/windows.py``) and the segments are written where spec 03 writes them,
``<work>/video/<video_id>/segments.json``. ``describe <video_id>`` and the API (spec 08) read them
back from there, so when spec 03 lands only the cutting step changes.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import cv2

from mentormind.core.schemas.common import DataClassification
from mentormind.core.schemas.video import Segment, VideoAsset
from mentormind.processing.vlm.sweep.windows import fixed_window_segments, video_id_for


def segments_path(work_dir: Path, video_id: str) -> Path:
    return work_dir / "video" / video_id / "segments.json"


def probe_video(
    video: Path, *, process_id: str | None, classification: DataClassification, video_id: str | None = None
) -> VideoAsset:
    """Spec 03 §3 ``VideoAsset`` of a raw video (stand-in for spec 03 ``video probe``).

    Raises:
        ValueError: OpenCV cannot read the video's frame count or fps.
    """
    capture = cv2.VideoCapture(str(video))
    try:
        frames = capture.get(cv2.CAP_PROP_FRAME_COUNT)
        fps = capture.get(cv2.CAP_PROP_FPS) or 0.0
    finally:
        capture.release()
    if frames <= 0 or fps <= 0:
        raise ValueError(f"không đọc được số khung hình/fps của {video.name}")
    return VideoAsset(
        video_id=video_id or video_id_for(video),
        path=str(video),
        duration_s=round(frames / fps, 3),
        fps=round(fps, 3),
        has_audio=_has_audio(video),
        process_id=process_id,
        data_classification=classification,
    )


def _has_audio(video: Path) -> bool:
    """Whether ffprobe sees an audio stream; ``False`` without ffprobe (nothing to transcribe then)."""
    if shutil.which("ffprobe") is None:
        return False
    found = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index", "-of", "csv=p=0", str(video)],
        capture_output=True, text=True, check=False,
    )  # fmt: skip
    return bool(found.stdout.strip())


def cut_fixed_windows(
    video: Path, *, work_dir: Path, classification: DataClassification, window_s: float = 10.0
) -> list[Segment]:
    """Cut ``video`` into ``window_s`` windows and save them as its ``segments.json``."""
    vid = video_id_for(video)
    segments = fixed_window_segments(
        video, out_dir=work_dir / "video" / vid / "clips", classification=classification,
        window_s=window_s, video_id=vid,
    )  # fmt: skip
    write_segments(segments_path(work_dir, vid), segments)
    return segments


def read_segments(path: Path) -> list[Segment]:
    """The segments of a ``segments.json``.

    Raises:
        FileNotFoundError: no such file.
        ValueError: the file lists no segment.
    """
    if not path.is_file():
        raise FileNotFoundError(f"Không thấy {path} (spec 03 `knowhow video segment` chưa chạy). Dùng --video <file>.")
    loaded = [Segment.model_validate(s) for s in json.loads(path.read_text(encoding="utf-8"))]
    if not loaded:
        raise ValueError(f"{path} không có đoạn nào.")
    return loaded


def write_segments(path: Path, segments: list[Segment]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.part")
    tmp.write_text(
        json.dumps([s.model_dump(mode="json") for s in segments], ensure_ascii=False, indent=2), encoding="utf-8"
    )
    tmp.replace(path)
