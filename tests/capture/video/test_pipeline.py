"""spec 03 FR-05/06/09 — VideoCapturePipeline end to end on synthetic videos (AC-01, AC-07), media cache."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import pytest

from mentormind.capture.video import VideoCapturePipeline, media, store
from mentormind.capture.video.segmenters import FixedWindowSegmenter, Method, SceneSegmenter, Segmenter
from mentormind.core.config import Settings
from mentormind.core.providers.asr.backends.fake import FakeASR
from mentormind.core.schemas.common import DataClassification
from tests.capture.video.fakes import fake_ffmpeg, synthetic_video
from tests.capture.video.test_transcribe_and_align import SPEECH, fake_extract

SYNTHETIC = DataClassification.SYNTHETIC


def pipeline(asr: FakeASR | None = None, build: Any = None) -> VideoCapturePipeline:
    return VideoCapturePipeline(
        Settings(_env_file=None), build=build, asr=lambda: asr or FakeASR([SPEECH]), extract=fake_extract
    )


def test_ac_01_every_video_gives_3_segments_or_more_each_with_3_keyframes_and_a_clip(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_ffmpeg(monkeypatch)
    for n, seconds in enumerate((31, 47, 64)):
        video = synthetic_video(tmp_path / f"demo_{n}.mp4", seconds, size=(320, 240))
        result = pipeline().run(
            video, work_dir=tmp_path / "work", process_id="PACK01", classification=SYNTHETIC, method="fixed_window"
        )
        assert len(result.segments) >= 3, video.name
        for segment in result.segments:
            assert len(segment.keyframes) == 3 and all(Path(k).is_file() for k in segment.keyframes)
            assert Path(segment.clip_path).is_file()
        assert store.read_segments(store.segments_path(tmp_path / "work", result.asset.video_id)) == result.segments


def test_ac_07_segments_and_transcript_carry_the_videos_label(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake_ffmpeg(monkeypatch, audio=True)
    stages: list[str] = []
    result = pipeline().run(
        synthetic_video(tmp_path / "in.mp4", 25),
        work_dir=tmp_path / "work",
        process_id="PACK01",
        classification=DataClassification.FACTORY_CONFIDENTIAL,
        method="fixed_window",
        progress=lambda stage, done, total: stages.append(stage),
    )
    assert result.asset.has_audio and result.transcript
    labels = {s.data_classification for s in result.segments} | {t.data_classification for t in result.transcript}
    assert labels == {DataClassification.FACTORY_CONFIDENTIAL}
    assert stages[0] == "cut" and stages[-1] == "transcribe"  # cut first, then speech
    assert set(result.seconds) == {"probe", "cut", "media", "transcribe"}


def test_the_method_actually_used_is_reported(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake_ffmpeg(monkeypatch)

    def build(method: Method) -> Segmenter:
        if method == "hand_activity":
            from mentormind.capture.video.segmenters import HandActivitySegmenter, SegmenterUnavailable

            def missing() -> Any:
                raise SegmenterUnavailable("thiếu MediaPipe")

            return HandActivitySegmenter(detector=missing)
        return SceneSegmenter(detect=lambda v, threshold: [(0.0, 6.0), (6.0, 12.0)])

    result = pipeline(build=build).run(
        synthetic_video(tmp_path / "in.mp4", 12), work_dir=tmp_path / "w", process_id=None, classification=SYNTHETIC
    )
    assert (result.method, result.method_used) == ("hand_activity", "scene")
    assert {s.method for s in result.segments} == {"scene"}


def test_clips_are_browser_playable_h264_and_stale_ones_are_redone(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[list[str]] = []

    def run(args: list[str], check: bool) -> Any:
        calls.append(args)
        Path(args[-1]).write_bytes(b"mp4")
        return subprocess.CompletedProcess(args, 0)

    monkeypatch.setattr(media.subprocess, "run", run)
    media.cut_clip(Path("in.mkv"), tmp_path / "clips" / "S001.mp4", 1.0, 4.5)
    [args] = calls
    assert args[args.index("-c:v") + 1] == "libx264" and args[args.index("-pix_fmt") + 1] == "yuv420p"
    assert "+faststart" in args and "-an" in args and (tmp_path / "clips" / "S001.mp4").is_file()

    fake_ffmpeg(monkeypatch)
    video = synthetic_video(tmp_path / "in.mp4", 25)
    windows = pipeline(build=lambda m: FixedWindowSegmenter(motion=False))
    first = windows.run(
        video, work_dir=tmp_path / "w", process_id=None, classification=SYNTHETIC, method="fixed_window"
    )
    clip = Path(first.segments[0].clip_path)
    clip.write_bytes(b"from the 10 s cut")
    shots = pipeline(build=lambda m: SceneSegmenter(detect=lambda v, t: [(0.0, 4.0), (4.0, 25.0)]))
    second = shots.run(video, work_dir=tmp_path / "w", process_id=None, classification=SYNTHETIC, method="scene")
    assert (second.segments[0].t_start, second.segments[0].t_end) == (0.0, 4.0)
    assert Path(second.segments[0].clip_path).read_bytes() != b"from the 10 s cut"  # bounds changed: redone
