"""spec 03 FR-01 — `knowhow video probe` and the VideoAsset it returns."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from mentormind.capture.video.probe import ProbeError, probe, video_id_for
from mentormind.core.schemas import DataClassification
from tests.capture.video.conftest import MakeVideo, needs_ffmpeg

FFPROBE_JSON = json.dumps(
    {
        "format": {"duration": "193.793000"},
        "streams": [
            {"codec_type": "video", "avg_frame_rate": "30000/1001", "width": 1920, "height": 1080},
            {"codec_type": "audio", "avg_frame_rate": "0/0"},
        ],
    }
)


def _fake(output: str):
    return lambda cmd: output


def test_video_id_is_sha256_prefix_of_the_bytes(tmp_path: Path) -> None:
    f = tmp_path / "a.mp4"
    f.write_bytes(b"hello video")
    assert video_id_for(f) == "VID-" + hashlib.sha256(b"hello video").hexdigest()[:12]


def test_probe_reads_duration_fps_and_audio(tmp_path: Path) -> None:
    f = tmp_path / "a.mp4"
    f.write_bytes(b"x")
    asset = probe(f, process_id="PACK01", classification=DataClassification.PUBLIC, runner=_fake(FFPROBE_JSON))
    assert asset.duration_s == pytest.approx(193.793)
    assert asset.fps == pytest.approx(29.97, abs=0.01)
    assert asset.has_audio is True
    assert asset.process_id == "PACK01" and asset.data_classification is DataClassification.PUBLIC
    assert asset.video_id == video_id_for(f) and asset.path == str(f)


def test_probe_without_audio_stream(tmp_path: Path) -> None:
    f = tmp_path / "a.mp4"
    f.write_bytes(b"x")
    silent = json.dumps({"format": {"duration": "5"}, "streams": [{"codec_type": "video", "avg_frame_rate": "25/1"}]})
    asset = probe(f, process_id=None, classification=DataClassification.SYNTHETIC, runner=_fake(silent))
    assert asset.has_audio is False and asset.fps == 25.0 and asset.process_id is None


@pytest.mark.parametrize(
    "output",
    [
        "not json",
        json.dumps({"format": {}, "streams": []}),
        json.dumps({"format": {"duration": "3"}, "streams": [{"codec_type": "audio"}]}),
    ],
)
def test_unreadable_or_videoless_output_is_a_clear_error(tmp_path: Path, output: str) -> None:
    f = tmp_path / "a.mp4"
    f.write_bytes(b"x")
    with pytest.raises(ProbeError, match="a.mp4"):
        probe(f, process_id=None, classification=DataClassification.PUBLIC, runner=_fake(output))


def test_missing_file_is_a_clear_error(tmp_path: Path) -> None:
    with pytest.raises(ProbeError, match="Không thấy"):
        probe(tmp_path / "nope.mp4", process_id=None, classification=DataClassification.PUBLIC)


def test_missing_ffprobe_says_what_to_install(tmp_path: Path) -> None:
    f = tmp_path / "a.mp4"
    f.write_bytes(b"x")
    with pytest.raises(ProbeError, match="ffmpeg"):
        probe(f, process_id=None, classification=DataClassification.PUBLIC, ffprobe="no-such-ffprobe-binary")


@needs_ffmpeg
def test_probe_on_a_real_file(make_video: MakeVideo) -> None:
    video = make_video(audio=True)
    asset = probe(video, process_id="PACK01", classification=DataClassification.SYNTHETIC)
    assert asset.duration_s == pytest.approx(12.0, abs=0.5) and asset.fps == pytest.approx(10.0) and asset.has_audio
