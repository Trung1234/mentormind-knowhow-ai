"""spec 03 FR-02, AC-01, AC-07, AC-11 — `segment_video` end to end with fake ffmpeg/ffprobe."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from mentormind.capture.video.media import MediaError
from mentormind.capture.video.pipeline import ClassificationMismatchError, segment_video
from mentormind.capture.video.probe import video_id_for
from mentormind.capture.video.segmenters import FixedWindowSegmenter, SceneSegmenter, Segmenter
from mentormind.core.config import Settings
from mentormind.core.guard.data_guard import ConfidentialDataError
from mentormind.core.schemas import DataClassification
from mentormind.core.schemas.video import Segment, VideoAsset
from tests.capture.video.conftest import MakeVideo, needs_ffmpeg
from tests.capture.video.test_media import RecordingRunner

SETTINGS = Settings(_env_file=None)
PROBE = json.dumps(
    {
        "format": {"duration": "35.0"},
        "streams": [{"codec_type": "video", "avg_frame_rate": "25/1"}, {"codec_type": "audio"}],
    }
)
PUBLIC, SYNTH = DataClassification.PUBLIC, DataClassification.SYNTHETIC


def _video(tmp_path: Path, content: bytes = b"video-bytes") -> Path:
    f = tmp_path / "in" / "a.mp4"
    f.parent.mkdir(exist_ok=True)
    f.write_bytes(content)
    return f


def _run(tmp_path: Path, video: Path | None = None, classification: DataClassification = PUBLIC, **kw: object):
    params: dict[str, object] = {
        "process_id": "PACK01",
        "classification": classification,
        "method": "fixed_window",
        "out_root": tmp_path / "work",
        "segmenters": {"fixed_window": FixedWindowSegmenter(10.0)},
        "settings": SETTINGS,
        "ffprobe_runner": lambda cmd: PROBE,
        "media_runner": RecordingRunner(),
        "motion_frames": lambda video: [],
    }
    params.update(kw)
    return segment_video(video or _video(tmp_path), **params)  # type: ignore[arg-type]


def test_segments_json_is_a_flat_list_that_spec_04_can_load(tmp_path: Path) -> None:
    result = _run(tmp_path)
    work = tmp_path / "work" / result.asset.video_id
    raw = json.loads((work / "segments.json").read_text(encoding="utf-8"))
    assert isinstance(raw, list) and len(raw) == 4  # 35 s in 10 s windows
    segments = [Segment.model_validate(s) for s in raw]  # what vlm/cli/describe.py does
    assert [s.index for s in segments] == [1, 2, 3, 4]
    assert segments[0].segment_id == f"{result.asset.video_id}-S001"
    assert VideoAsset.model_validate_json((work / "asset.json").read_text(encoding="utf-8")) == result.asset


def test_every_segment_has_three_keyframes_and_a_clip_on_disk(tmp_path: Path) -> None:
    result = _run(tmp_path)
    for segment in result.segments:
        assert len(segment.keyframes) == 3 and all(Path(p).is_file() for p in segment.keyframes)
        assert Path(segment.clip_path).is_file() and segment.method == "fixed_window" and segment.motion_score is None


def test_ac_07_classification_reaches_the_asset_and_every_segment(tmp_path: Path) -> None:
    result = _run(tmp_path, classification=SYNTH)
    assert result.asset.data_classification is SYNTH
    assert {s.data_classification for s in result.segments} == {SYNTH}


def test_confidential_video_is_allowed_because_everything_runs_locally(tmp_path: Path) -> None:
    result = _run(tmp_path, classification=DataClassification.FACTORY_CONFIDENTIAL)
    assert {s.data_classification for s in result.segments} == {DataClassification.FACTORY_CONFIDENTIAL}


def test_ac_09_running_twice_gives_identical_files_and_reuses_the_media(tmp_path: Path) -> None:
    runner = RecordingRunner()
    first = _run(tmp_path, media_runner=runner)
    path = tmp_path / "work" / first.asset.video_id / "segments.json"
    before, calls = path.read_bytes(), len(runner.commands)
    _run(tmp_path, media_runner=runner)
    assert path.read_bytes() == before and len(runner.commands) == calls


def test_ac_11_other_classification_is_refused_and_force_overrides(tmp_path: Path) -> None:
    first = _run(tmp_path, classification=PUBLIC)
    path = tmp_path / "work" / first.asset.video_id / "segments.json"
    before = path.read_bytes()
    with pytest.raises(ClassificationMismatchError, match="public"):
        _run(tmp_path, classification=SYNTH)
    assert path.read_bytes() == before
    forced = _run(tmp_path, classification=SYNTH, force=True)
    assert {s.data_classification for s in forced.segments} == {SYNTH}


def test_media_failure_writes_no_json(tmp_path: Path) -> None:
    with pytest.raises(MediaError):
        _run(tmp_path, media_runner=RecordingRunner(fail=True))
    assert not list((tmp_path / "work").rglob("segments.json"))


def test_fallback_notes_are_returned_for_the_log(tmp_path: Path) -> None:
    registry: dict[str, Segmenter] = {"fixed_window": FixedWindowSegmenter(10.0)}
    result = _run(tmp_path, method="hand_activity", segmenters=registry)
    assert result.method == "fixed_window" and any("hand_activity" in n for n in result.notes)


def test_missing_input_is_a_clear_error(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        _run(tmp_path, video=tmp_path / "nope.mp4")


def test_confidential_guard_runs_before_any_work(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(classification: object, provider: object) -> None:
        raise ConfidentialDataError("blocked")

    monkeypatch.setattr("mentormind.capture.video.pipeline.DataGuard.check", refuse)
    runner = RecordingRunner()
    with pytest.raises(ConfidentialDataError):
        _run(tmp_path, media_runner=runner)
    assert runner.commands == []


@needs_ffmpeg
def test_ac_01_real_video_end_to_end(make_video: MakeVideo, tmp_path: Path) -> None:
    video = make_video()  # 12 s, hard cuts at 4 s and 8 s
    result = segment_video(
        video,
        process_id="PACK01",
        classification=SYNTH,
        method="scene",
        out_root=tmp_path / "work",
        segmenters={"scene": SceneSegmenter(20.0)},
        settings=SETTINGS,
    )
    assert result.asset.video_id == video_id_for(video) and result.method == "scene"
    assert len(result.segments) == 3
    assert all(len(s.keyframes) == 3 and Path(s.clip_path).stat().st_size > 0 for s in result.segments)


def test_ac_10_every_segment_gets_a_motion_score_between_0_and_1(tmp_path: Path) -> None:
    # 35 s at 5 fps: first 15 s still, then moving
    dark, bright = bytes(14400), bytes([255]) * 14400
    frames = [dark] * 75 + [dark if i % 2 else bright for i in range(100)]
    result = _run(tmp_path, motion_frames=lambda video: frames)
    scores = [s.motion_score for s in result.segments]
    assert all(s is not None and 0.0 <= s <= 1.0 for s in scores)
    assert scores[0] == 0.0 and scores[-1] == 1.0  # still first window, flickering last window


def test_motion_failure_keeps_the_segments_and_notes_it(tmp_path: Path) -> None:
    def broken(video: Path) -> list[bytes]:
        raise MediaError("ffmpeg lỗi")

    result = _run(tmp_path, motion_frames=broken)
    assert len(result.segments) == 4 and {s.motion_score for s in result.segments} == {None}
    assert any("motion_score" in n for n in result.notes)
