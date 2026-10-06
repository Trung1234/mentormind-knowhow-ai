"""spec 03 FR-01, FR-02 — `knowhow video probe|segment`."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from mentormind.capture.video import cli as video_cli
from mentormind.capture.video.segmenters import FixedWindowSegmenter
from mentormind.capture.video.transcribe import SpokenLine
from mentormind.core.cli import app
from mentormind.core.config import Settings
from tests.capture.video.test_media import RecordingRunner
from tests.capture.video.test_pipeline import PROBE
from tests.capture.video.test_transcribe import FakeTranscriber, _audio_stub

runner = CliRunner()


@pytest.fixture(autouse=True)
def fakes(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(video_cli, "build_segmenters", lambda settings: {"fixed_window": FixedWindowSegmenter(10.0)})
    monkeypatch.setattr(video_cli, "FFPROBE_RUNNER", lambda cmd: PROBE)
    monkeypatch.setattr(video_cli, "MEDIA_RUNNER", RecordingRunner())
    monkeypatch.setattr(video_cli, "AUDIO_RUNNER", _audio_stub)
    monkeypatch.setattr(video_cli, "build_transcriber", lambda settings, model=None: FakeTranscriber())
    monkeypatch.setattr(video_cli, "get_settings", lambda: Settings(_env_file=None, work_dir=tmp_path / "work"))


def _file(tmp_path: Path) -> Path:
    f = tmp_path / "a.mp4"
    f.write_bytes(b"video-bytes")
    return f


def test_video_group_is_registered_and_lists_commands() -> None:
    result = runner.invoke(app, ["video", "--help"])
    assert result.exit_code == 0 and "probe" in result.output and "segment" in result.output


def test_probe_prints_the_asset_as_json_and_defaults_to_the_strictest_label(tmp_path: Path) -> None:
    result = runner.invoke(app, ["video", "probe", str(_file(tmp_path))])
    data = json.loads(result.output)
    assert result.exit_code == 0 and data["data_classification"] == "factory_confidential"
    assert data["duration_s"] == 35.0 and data["has_audio"] is True


def test_segment_requires_a_classification(tmp_path: Path) -> None:
    result = runner.invoke(app, ["video", "segment", str(_file(tmp_path)), "--method", "fixed_window"])
    assert result.exit_code != 0 and not (tmp_path / "work").exists()


def test_segment_rejects_a_label_outside_the_enum(tmp_path: Path) -> None:
    result = runner.invoke(app, ["video", "segment", str(_file(tmp_path)), "--classification", "secret"])
    assert result.exit_code != 0 and not (tmp_path / "work").exists()


def test_segment_writes_files_and_prints_a_summary(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "video",
            "segment",
            str(_file(tmp_path)),
            "--process-id",
            "PACK01",
            "--classification",
            "synthetic",
            "--method",
            "fixed_window",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "VID-" in result.output and "4 đoạn" in result.output and "fixed_window" in result.output
    [segments] = list((tmp_path / "work").rglob("segments.json"))
    assert len(json.loads(segments.read_text(encoding="utf-8"))) == 4


def test_segment_prints_fallback_notes(tmp_path: Path) -> None:
    result = runner.invoke(
        app, ["video", "segment", str(_file(tmp_path)), "--classification", "public", "--method", "hand_activity"]
    )
    assert result.exit_code == 0 and "hand_activity" in result.output


def test_changing_the_label_is_an_error_until_force(tmp_path: Path) -> None:
    video = str(_file(tmp_path))
    base = ["video", "segment", video, "--method", "fixed_window"]
    assert runner.invoke(app, [*base, "--classification", "public"]).exit_code == 0
    refused = runner.invoke(app, [*base, "--classification", "synthetic"])
    assert refused.exit_code == 2 and "--force" in refused.output
    assert runner.invoke(app, [*base, "--classification", "synthetic", "--force"]).exit_code == 0


def test_missing_file_exits_with_a_clear_error(tmp_path: Path) -> None:
    result = runner.invoke(app, ["video", "segment", str(tmp_path / "nope.mp4"), "--classification", "public"])
    assert result.exit_code == 2 and "Không thấy" in result.output


def test_transcribe_requires_a_classification(tmp_path: Path) -> None:
    result = runner.invoke(app, ["video", "transcribe", str(_file(tmp_path))])
    assert result.exit_code != 0 and not (tmp_path / "work").exists()


def test_transcribe_writes_transcript_json_and_prints_a_summary(tmp_path: Path) -> None:
    result = runner.invoke(app, ["video", "transcribe", str(_file(tmp_path)), "--classification", "synthetic"])
    assert result.exit_code == 0, result.output
    assert "1 câu" in result.output and "vi" in result.output
    [transcript] = list((tmp_path / "work").rglob("transcript.json"))
    [line] = json.loads(transcript.read_text(encoding="utf-8"))
    assert line["data_classification"] == "synthetic" and line["source"] == "inline"


def test_transcribe_auto_language_is_accepted(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeTranscriber([SpokenLine(0.0, 1.0, "สวัสดี", "th")])
    monkeypatch.setattr(video_cli, "build_transcriber", lambda settings, model=None: fake)
    result = runner.invoke(
        app, ["video", "transcribe", str(_file(tmp_path)), "--classification", "public", "--language", "auto"]
    )
    assert result.exit_code == 0 and "th" in result.output and fake.calls[0][1] is None


def test_transcribe_changing_the_label_is_an_error_until_force(tmp_path: Path) -> None:
    base = ["video", "transcribe", str(_file(tmp_path))]
    assert runner.invoke(app, [*base, "--classification", "public"]).exit_code == 0
    refused = runner.invoke(app, [*base, "--classification", "synthetic"])
    assert refused.exit_code == 2 and "--force" in refused.output
    assert runner.invoke(app, [*base, "--classification", "synthetic", "--force"]).exit_code == 0


def test_transcribe_missing_whisper_is_a_clear_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from mentormind.capture.video.transcribe import TranscriberError

    class Broken:
        def transcribe(self, audio: Path, language: str | None) -> list[SpokenLine]:
            raise TranscriberError("Thiếu faster-whisper")

    monkeypatch.setattr(video_cli, "build_transcriber", lambda settings, model=None: Broken())
    result = runner.invoke(app, ["video", "transcribe", str(_file(tmp_path)), "--classification", "public"])
    assert result.exit_code == 2 and "faster-whisper" in result.output


def _processed_video(tmp_path: Path) -> str:
    """Run `segment` so the video has an asset.json; returns its video_id."""
    assert (
        runner.invoke(
            app, ["video", "segment", str(_file(tmp_path)), "--classification", "synthetic", "--method", "fixed_window"]
        ).exit_code
        == 0
    )
    return next((tmp_path / "work" / "video").iterdir()).name


def _recording(tmp_path: Path) -> Path:
    audio = tmp_path / "recall.wav"
    audio.write_bytes(b"RIFF")
    return audio


def test_ac_08_recall_audio_shifts_by_offset_and_marks_the_source(tmp_path: Path) -> None:
    video_id = _processed_video(tmp_path)
    result = runner.invoke(
        app,
        [
            "video",
            "transcribe",
            "--recall-audio",
            str(_recording(tmp_path)),
            "--video-id",
            video_id,
            "--offset",
            "12.5",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "cued_recall" in result.output and "offset 12.5s" in result.output
    [line] = json.loads((tmp_path / "work" / "video" / video_id / "transcript.json").read_text(encoding="utf-8"))
    assert line["t_start"] == 13.5 and line["source"] == "cued_recall" and line["data_classification"] == "synthetic"


def test_ac_08_unknown_video_id_exits_with_an_error_and_writes_nothing(tmp_path: Path) -> None:
    result = runner.invoke(
        app, ["video", "transcribe", "--recall-audio", str(_recording(tmp_path)), "--video-id", "VID-aaaaaaaaaaaa"]
    )
    assert result.exit_code == 2 and "VID-aaaaaaaaaaaa" in result.output
    assert not list((tmp_path / "work").rglob("transcript.json")) if (tmp_path / "work").exists() else True


def test_recall_audio_needs_a_video_id(tmp_path: Path) -> None:
    result = runner.invoke(app, ["video", "transcribe", "--recall-audio", str(_recording(tmp_path))])
    assert result.exit_code == 2 and "--video-id" in result.output


def test_recall_audio_cannot_be_combined_with_a_video_file_or_a_label(tmp_path: Path) -> None:
    audio = str(_recording(tmp_path))
    both = runner.invoke(
        app, ["video", "transcribe", str(_file(tmp_path)), "--recall-audio", audio, "--video-id", "VID-aaaaaaaaaaaa"]
    )
    labelled = runner.invoke(
        app,
        [
            "video",
            "transcribe",
            "--recall-audio",
            audio,
            "--video-id",
            "VID-aaaaaaaaaaaa",
            "--classification",
            "public",
        ],
    )
    assert both.exit_code == 2 and labelled.exit_code == 2 and "--classification" in labelled.output


def test_transcribe_needs_a_file_or_a_recall_audio() -> None:
    result = runner.invoke(app, ["video", "transcribe", "--classification", "public"])
    assert result.exit_code == 2 and "--recall-audio" in result.output


def test_video_id_is_rejected_without_recall_audio(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["video", "transcribe", str(_file(tmp_path)), "--classification", "public", "--video-id", "VID-aaaaaaaaaaaa"],
    )
    assert result.exit_code == 2 and "--recall-audio" in result.output


def test_malformed_video_id_exits_with_an_error(tmp_path: Path) -> None:
    result = runner.invoke(
        app, ["video", "transcribe", "--recall-audio", str(_recording(tmp_path)), "--video-id", "../../etc"]
    )
    assert result.exit_code == 2 and "video-id" in result.output
