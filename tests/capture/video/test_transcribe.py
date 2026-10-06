"""spec 03 FR-07, AC-05, AC-07 — `transcribe`: audio → local Whisper → transcript.json."""

from __future__ import annotations

import json
import sys
import wave
from pathlib import Path

import pytest

from mentormind.capture.video.media import MediaError
from mentormind.capture.video.pipeline import ClassificationMismatchError
from mentormind.capture.video.transcribe import (
    FasterWhisperTranscriber,
    SpokenLine,
    Transcriber,
    TranscriberError,
    extract_audio,
    merge_transcript,
    read_transcript,
    transcribe_video,
)
from mentormind.core.config import Settings
from mentormind.core.schemas import DataClassification
from mentormind.core.schemas.video import TranscriptSegment
from tests.capture.video.conftest import MakeVideo, needs_ffmpeg
from tests.capture.video.test_pipeline import PROBE

SETTINGS = Settings(_env_file=None)
PUBLIC, SYNTH = DataClassification.PUBLIC, DataClassification.SYNTHETIC
SILENT_PROBE = json.dumps(
    {"format": {"duration": "35.0"}, "streams": [{"codec_type": "video", "avg_frame_rate": "25/1"}]}
)


class FakeTranscriber:
    def __init__(self, lines: list[SpokenLine] | None = None) -> None:
        self.lines = lines if lines is not None else [SpokenLine(1.0, 4.0, "Xoay ngược vì trầy mặt", "vi")]
        self.calls: list[tuple[Path, str | None]] = []

    def transcribe(self, audio: Path, language: str | None) -> list[SpokenLine]:
        self.calls.append((audio, language))
        return self.lines


STUB_AUDIO_SECONDS = 10


def _audio_stub(command: list[str]) -> None:
    """Pretend to be ffmpeg: write a valid, silent 16 kHz mono WAV of ``STUB_AUDIO_SECONDS`` seconds."""
    with wave.open(command[-1], "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(16000)
        handle.writeframes(bytes(2 * 16000 * STUB_AUDIO_SECONDS))


def _run(tmp_path: Path, transcriber: Transcriber | None = None, **kw: object):
    video = tmp_path / "in.mp4"
    video.write_bytes(b"video-bytes")
    params: dict[str, object] = {
        "process_id": "PACK01",
        "classification": PUBLIC,
        "language": "vi",
        "out_root": tmp_path / "work",
        "transcriber": transcriber or FakeTranscriber(),
        "settings": SETTINGS,
        "ffprobe_runner": lambda cmd: PROBE,
        "audio_runner": _audio_stub,
    }
    params.update(kw)
    return transcribe_video(video, **params)  # type: ignore[arg-type]


def test_lines_become_transcript_segments_with_the_video_label(tmp_path: Path) -> None:
    result = _run(tmp_path, classification=SYNTH)
    [line] = result.lines
    assert (line.t_start, line.t_end, line.text, line.language) == (1.0, 4.0, "Xoay ngược vì trầy mặt", "vi")
    assert line.source == "inline" and line.video_id == result.asset.video_id
    assert line.data_classification is SYNTH  # AC-07
    stored = read_transcript(tmp_path / "work" / result.asset.video_id / "transcript.json")
    assert stored == [line]


def test_ac_05_a_video_without_audio_gives_an_empty_list_and_no_error(tmp_path: Path) -> None:
    fake = FakeTranscriber()
    result = _run(tmp_path, fake, ffprobe_runner=lambda cmd: SILENT_PROBE)
    assert result.lines == [] and fake.calls == []
    assert json.loads((tmp_path / "work" / result.asset.video_id / "transcript.json").read_text(encoding="utf-8")) == []


def test_auto_language_lets_whisper_detect_and_keeps_what_it_found(tmp_path: Path) -> None:
    fake = FakeTranscriber([SpokenLine(0.0, 2.0, "สวัสดี", "th")])
    result = _run(tmp_path, fake, language="auto")
    assert fake.calls[0][1] is None and result.lines[0].language == "th"


def test_a_fixed_language_is_passed_through(tmp_path: Path) -> None:
    fake = FakeTranscriber()
    _run(tmp_path, fake, language="vi")
    assert fake.calls[0][1] == "vi"


def test_blank_or_inverted_lines_are_dropped(tmp_path: Path) -> None:
    fake = FakeTranscriber(
        [SpokenLine(0.0, 1.0, "   ", "vi"), SpokenLine(5.0, 5.0, "zero length", "vi"), SpokenLine(2.0, 3.0, "ok", "vi")]
    )
    assert [t.text for t in _run(tmp_path, fake).lines] == ["ok"]


def test_rerun_replaces_inline_lines_but_keeps_cued_recall(tmp_path: Path) -> None:
    first = _run(tmp_path)
    path = tmp_path / "work" / first.asset.video_id / "transcript.json"
    recall = TranscriptSegment(
        video_id=first.asset.video_id, t_start=2.0, t_end=3.0, text="vì sao", language="vi",
        source="cued_recall", data_classification=PUBLIC,
    )  # fmt: skip
    merge_transcript(path, [recall], drop=lambda t: t.source == "cued_recall")
    _run(tmp_path, FakeTranscriber([SpokenLine(10.0, 12.0, "dòng mới", "vi")]))
    assert [(t.source, t.text) for t in read_transcript(path)] == [("cued_recall", "vì sao"), ("inline", "dòng mới")]


def test_transcript_is_sorted_by_start_time(tmp_path: Path) -> None:
    fake = FakeTranscriber([SpokenLine(9.0, 10.0, "b", "vi"), SpokenLine(1.0, 2.0, "a", "vi")])
    assert [t.text for t in _run(tmp_path, fake).lines] == ["a", "b"]


def test_ac_11_other_label_is_refused_until_force(tmp_path: Path) -> None:
    first = _run(tmp_path, classification=PUBLIC)
    path = tmp_path / "work" / first.asset.video_id / "transcript.json"
    before = path.read_bytes()
    with pytest.raises(ClassificationMismatchError):
        _run(tmp_path, classification=SYNTH)
    assert path.read_bytes() == before
    assert _run(tmp_path, classification=SYNTH, force=True).lines[0].data_classification is SYNTH


def test_audio_extraction_failure_leaves_no_transcript(tmp_path: Path) -> None:
    def broken(command: list[str]) -> None:
        raise MediaError("ffmpeg lỗi")

    with pytest.raises(MediaError):
        _run(tmp_path, audio_runner=broken)
    assert not list((tmp_path / "work").rglob("transcript.json"))


def test_missing_input_is_a_clear_error(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        transcribe_video(
            tmp_path / "nope.mp4", process_id=None, classification=PUBLIC, language="vi",
            out_root=tmp_path / "work", transcriber=FakeTranscriber(), settings=SETTINGS,
        )  # fmt: skip


def test_missing_whisper_library_says_what_to_install(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setitem(sys.modules, "faster_whisper", None)  # makes `import faster_whisper` raise ImportError
    with pytest.raises(TranscriberError, match="extra `video`"):
        FasterWhisperTranscriber("small").transcribe(tmp_path / "a.wav", "vi")


@needs_ffmpeg
def test_real_ffmpeg_extracts_16khz_mono_wav(make_video: MakeVideo, tmp_path: Path) -> None:
    wav = extract_audio(make_video(audio=True), tmp_path / "a.wav")
    with wave.open(str(wav)) as handle:
        assert handle.getframerate() == 16000 and handle.getnchannels() == 1 and handle.getnframes() > 16000
