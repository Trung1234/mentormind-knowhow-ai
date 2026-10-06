"""spec 03 AC-01..03 on the real LASI demo video, scored against `data/video/groundtruth.json`.

Slow (about 25 s: ffmpeg writes 31 clips) and needs the video, which the team keeps in Git LFS on
the spec 04 branch. Run: ``KNOWHOW_RUN_SAMPLE_TESTS=1 uv run pytest tests/capture/video/test_lasi.py``.
The ground truth is still a draft (docs/plans/03-spike-notes.md), so the thresholds are loose.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from statistics import median

import pytest

from mentormind.capture.video.motion import ffmpeg_gray_frames, motion_profile, motion_score
from mentormind.capture.video.pipeline import SegmentResult, segment_video
from mentormind.capture.video.segmenters import FixedWindowSegmenter, SceneSegmenter
from mentormind.capture.video.transcribe import FasterWhisperTranscriber, transcribe_video
from mentormind.core.config import Settings
from mentormind.core.schemas import DataClassification

DATA = Path(__file__).resolve().parents[3] / "data" / "video"
GROUND_TRUTH = DATA / "groundtruth.json"
_STILL_TYPES = {"interview", "logo", "title", "overlay", "other", "meeting", "visit", "aerial"}
VIDEO = next(iter(DATA.glob("LASI*.mkv")), None)

pytestmark = pytest.mark.skipif(
    os.environ.get("KNOWHOW_RUN_SAMPLE_TESTS") != "1" or VIDEO is None or VIDEO.stat().st_size < 1_000_000,
    reason="slow test on the real LASI video: set KNOWHOW_RUN_SAMPLE_TESTS=1 (the .mkv is a Git LFS file)",
)


@pytest.fixture(scope="module")
def result(tmp_path_factory: pytest.TempPathFactory) -> SegmentResult:
    assert VIDEO is not None
    settings = Settings(_env_file=None)
    return segment_video(
        VIDEO,
        process_id="PACK01",
        classification=DataClassification.PUBLIC,
        method="scene",
        out_root=tmp_path_factory.mktemp("work"),
        segmenters={"scene": SceneSegmenter(settings.scene_threshold), "fixed_window": FixedWindowSegmenter(10.0)},
        settings=settings,
    )


def test_ac_01_02_03_on_the_real_video(result: SegmentResult) -> None:
    segments = result.segments
    assert len(segments) >= 3 and result.method == "scene"
    assert all(3.0 <= s.t_end - s.t_start <= 20.0 for s in segments)
    assert segments[0].t_start == 0.0 and segments[-1].t_end == pytest.approx(result.asset.duration_s, abs=0.01)
    assert all(a.t_end == b.t_start for a, b in zip(segments, segments[1:], strict=False))
    assert all(len(s.keyframes) == 3 and Path(s.clip_path).stat().st_size > 0 for s in segments)


def test_cuts_agree_with_the_hand_labelled_scenes(result: SegmentResult) -> None:
    truth = sorted(s["t_start"] for s in json.loads(GROUND_TRUTH.read_text(encoding="utf-8"))["scenes"][1:])
    found = [s.t_start for s in result.segments[1:]]
    hit = sum(any(abs(f - t) <= 1.0 for f in found) for t in truth)
    assert hit / len(truth) >= 0.5  # cuts under 3 s are merged away on purpose, so recall is capped


def test_ac_10_motion_score_separates_work_scenes_from_interviews(result: SegmentResult) -> None:
    assert all(s.motion_score is not None and 0.0 <= s.motion_score <= 1.0 for s in result.segments)
    assert VIDEO is not None
    diffs = motion_profile(ffmpeg_gray_frames(VIDEO))
    scale = Settings(_env_file=None).motion_scale
    work: list[float] = []
    idle: list[float] = []
    for scene in json.loads(GROUND_TRUTH.read_text(encoding="utf-8"))["scenes"]:
        score = motion_score(diffs, scene["t_start"], scene["t_end"], scale=scale)
        if score is not None:
            (work if scene["type"] == "work" else idle if scene["type"] in _STILL_TYPES else []).append(score)
    wins = sum(w > i for w in work for i in idle) + 0.5 * sum(w == i for w in work for i in idle)
    assert wins / (len(work) * len(idle)) >= 0.85  # AUC; 0.93 when measured
    assert median(work) >= 0.3 > median(idle)  # spec 04: below 0.3 is "low motion", above is not


def test_transcribe_real_whisper_detects_the_thai_audio(tmp_path: Path) -> None:
    """Whisper `small` on 35 s of the LASI interview (speech starts near 16 s); needs the cached model."""
    assert VIDEO is not None
    clip = tmp_path / "clip.mkv"
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", "10", "-i", str(VIDEO), "-t", "35", "-c", "copy", str(clip)],
        check=True,
    )  # fmt: skip
    settings = Settings(_env_file=None)
    result = transcribe_video(
        clip,
        process_id="PACK01",
        classification=DataClassification.PUBLIC,
        language="auto",
        out_root=tmp_path / "work",
        transcriber=FasterWhisperTranscriber(settings.whisper_model, settings.whisper_compute_type),
        settings=settings,
    )
    assert len(result.lines) >= 3 and {t.language for t in result.lines} == {"th"}
    assert all(0.0 <= t.t_start < t.t_end <= result.asset.duration_s + 0.5 for t in result.lines)
