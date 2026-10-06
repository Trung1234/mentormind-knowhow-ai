"""spec 04 FR-05 / AC-21 — the fixed_window fallback: 3 keyframes per window and a segments.json."""

from __future__ import annotations

from pathlib import Path

import cv2
import pytest

from mentormind.core.providers.vlm.backends.fake import FakeVLM
from mentormind.core.schemas.common import DataClassification
from mentormind.processing.vlm.pipeline import DescribePipeline
from mentormind.processing.vlm.segments import cut_fixed_windows, probe_video, read_segments, segments_path
from mentormind.processing.vlm.sweep import windows
from tests.processing.vlm.passes.test_describe import fake_sampler
from tests.processing.vlm.test_pipeline import RUN_1
from tests.processing.vlm.video_fakes import fake_ffmpeg, synthetic_video

SYNTHETIC = DataClassification.SYNTHETIC


@pytest.fixture(autouse=True)
def _no_ffmpeg(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_ffmpeg(monkeypatch)


def test_ac_21_every_window_has_three_keyframes_and_the_segments_are_saved(tmp_path: Path) -> None:
    video = synthetic_video(tmp_path / "in.mp4", 25, size=(1280, 720))
    segments = cut_fixed_windows(video, work_dir=tmp_path / "work", classification=SYNTHETIC)
    assert [(s.t_start, s.t_end) for s in segments] == [(0, 10), (10, 20), (20, 25)]
    for segment in segments:
        assert len(segment.keyframes) == 3, segment.segment_id
        for keyframe in segment.keyframes:
            image = cv2.imread(keyframe)
            assert image is not None
            assert max(image.shape[:2]) == 768  # spec 03 FR-05: long side 768 px
    saved = segments_path(tmp_path / "work", segments[0].video_id)
    assert read_segments(saved) == segments


def test_ac_21_a_second_run_does_not_read_the_video_again(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    video = synthetic_video(tmp_path / "in.mp4", 12)
    first = cut_fixed_windows(video, work_dir=tmp_path / "work", classification=SYNTHETIC)
    monkeypatch.setattr(windows._FrameReader, "at", lambda self, t: pytest.fail("keyframes are cached"))
    assert cut_fixed_windows(video, work_dir=tmp_path / "work", classification=SYNTHETIC) == first


def test_ac_21_profiles_carry_the_keyframes_of_their_segment(tmp_path: Path) -> None:
    segments = cut_fixed_windows(
        synthetic_video(tmp_path / "in.mp4", 20), work_dir=tmp_path / "work", classification=SYNTHETIC
    )
    pipeline = DescribePipeline(
        FakeVLM(RUN_1), process_id="PACK01", default_fps=4.0, max_frames=48, consistency=False, sampler=fake_sampler
    )
    profiles = pipeline.run(segments, tmp_path / "run").profiles
    assert profiles
    by_segment = {s.segment_id: s.keyframes for s in segments}
    for profile in profiles:
        expected = [k for sid in profile.evidence.segment_ids for k in by_segment[sid]]
        assert profile.evidence.keyframes == expected


def test_a_video_id_reads_back_the_saved_segments(tmp_path: Path) -> None:
    segments = cut_fixed_windows(
        synthetic_video(tmp_path / "in.mp4", 10), work_dir=tmp_path / "work", classification=SYNTHETIC
    )
    assert read_segments(segments_path(tmp_path / "work", segments[0].video_id)) == segments
    with pytest.raises(FileNotFoundError, match="--video"):
        read_segments(segments_path(tmp_path / "work", "VID-000000000000"))


def test_probe_reads_duration_and_fps(tmp_path: Path) -> None:
    asset = probe_video(synthetic_video(tmp_path / "in.mp4", 6), process_id="PACK01", classification=SYNTHETIC)
    assert (asset.duration_s, asset.fps, asset.process_id) == (6.0, 4.0, "PACK01")
    assert asset.video_id.startswith("VID-") and asset.data_classification == SYNTHETIC
    with pytest.raises(ValueError):
        probe_video(tmp_path / "missing.mp4", process_id="PACK01", classification=SYNTHETIC)
