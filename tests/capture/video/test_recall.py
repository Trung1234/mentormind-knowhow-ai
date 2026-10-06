"""spec 03 FR-07b, AC-08, AC-07 — expert's video-cued recall audio → transcript lines on the video's clock."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from mentormind.capture.video.transcribe import (
    SpokenLine,
    read_transcript,
    transcribe_recall,
    transcribe_video,
)
from mentormind.core.config import Settings
from mentormind.core.schemas import DataClassification
from mentormind.core.schemas.video import VideoAsset
from tests.capture.video.test_transcribe import FakeTranscriber, _audio_stub

SETTINGS = Settings(_env_file=None)
VID = "VID-aaaaaaaaaaaa"
SYNTH = DataClassification.SYNTHETIC
LINES = [
    SpokenLine(0.0, 3.0, "Tôi xoay ngược vì nếu không sẽ trầy mặt", "vi"),
    SpokenLine(5.0, 8.0, "Lực ấn vừa phải", "vi"),
]


def _asset(tmp_path: Path, video_id: str = VID, label: DataClassification = SYNTH, duration: float = 60.0) -> Path:
    work = tmp_path / "work" / video_id
    work.mkdir(parents=True)
    asset = VideoAsset(
        video_id=video_id, path="v.mp4", duration_s=duration, fps=25.0, has_audio=False,
        process_id="PACK01", data_classification=label,
    )  # fmt: skip
    (work / "asset.json").write_text(asset.model_dump_json(), encoding="utf-8")
    return work


def _recall(tmp_path: Path, transcriber: FakeTranscriber | None = None, **kw: object):
    audio = tmp_path / "recall.wav"
    audio.write_bytes(b"RIFF")  # content is irrelevant: the fake audio runner writes the real WAV
    params: dict[str, object] = {
        "video_id": VID,
        "offset": 0.0,
        "language": "vi",
        "out_root": tmp_path / "work",
        "transcriber": transcriber or FakeTranscriber(LINES),
        "settings": SETTINGS,
        "audio_runner": _audio_stub,
    }
    params.update(kw)
    return transcribe_recall(audio, **params)  # type: ignore[arg-type]


def test_ac_08_offset_shifts_every_timestamp_and_marks_the_source(tmp_path: Path) -> None:
    work = _asset(tmp_path)
    result = _recall(tmp_path, offset=12.5)
    assert [(t.t_start, t.t_end) for t in result.lines] == [(12.5, 15.5), (17.5, 20.5)]
    assert {t.source for t in result.lines} == {"cued_recall"} and {t.video_id for t in result.lines} == {VID}
    assert read_transcript(work / "transcript.json") == result.lines


def test_ac_08_default_offset_is_zero(tmp_path: Path) -> None:
    _asset(tmp_path)
    assert [t.t_start for t in _recall(tmp_path).lines] == [0.0, 5.0]


def test_ac_07_lines_carry_the_label_of_the_video_asset(tmp_path: Path) -> None:
    _asset(tmp_path, label=DataClassification.FACTORY_CONFIDENTIAL)
    assert {t.data_classification for t in _recall(tmp_path).lines} == {DataClassification.FACTORY_CONFIDENTIAL}


def test_ac_08_unknown_video_id_is_an_error_and_writes_nothing(tmp_path: Path) -> None:
    fake = FakeTranscriber(LINES)
    with pytest.raises(FileNotFoundError, match="VID-aaaaaaaaaaaa"):
        _recall(tmp_path, fake)
    assert fake.calls == [] and not (tmp_path / "work").exists()


@pytest.mark.parametrize("bad", ["../../etc", "VID-a/b", "", "vid-aaaaaaaaaaaa", "VID-"])
def test_a_malformed_video_id_never_reaches_the_filesystem(tmp_path: Path, bad: str) -> None:
    with pytest.raises(ValueError, match="video-id"):
        _recall(tmp_path, video_id=bad)
    assert not (tmp_path / "work").exists()


def test_negative_offset_is_refused(tmp_path: Path) -> None:
    _asset(tmp_path)
    with pytest.raises(ValueError, match="offset"):
        _recall(tmp_path, offset=-1.0)


def test_missing_audio_file_is_a_clear_error(tmp_path: Path) -> None:
    _asset(tmp_path)
    with pytest.raises(FileNotFoundError, match="nope.wav"):
        transcribe_recall(
            tmp_path / "nope.wav", video_id=VID, offset=0.0, language="vi", out_root=tmp_path / "work",
            transcriber=FakeTranscriber(LINES), settings=SETTINGS,
        )  # fmt: skip


def test_recall_keeps_the_inline_lines_and_inline_rerun_keeps_recall(tmp_path: Path) -> None:
    video = tmp_path / "in.mp4"
    video.write_bytes(b"video-bytes")
    inline = FakeTranscriber([SpokenLine(1.0, 2.0, "lời khi quay", "vi")])
    first = transcribe_video(
        video, process_id="PACK01", classification=SYNTH, language="vi", out_root=tmp_path / "work",
        transcriber=inline, settings=SETTINGS, audio_runner=_audio_stub,
        ffprobe_runner=lambda cmd: json.dumps({"format": {"duration": "60"}, "streams": [{"codec_type": "video", "avg_frame_rate": "25/1"}, {"codec_type": "audio"}]}),
    )  # fmt: skip
    video_id = first.asset.video_id
    _recall(tmp_path, video_id=video_id)
    path = tmp_path / "work" / video_id / "transcript.json"
    assert sorted(t.source for t in read_transcript(path)) == ["cued_recall", "cued_recall", "inline"]
    transcribe_video(
        video, process_id="PACK01", classification=SYNTH, language="vi", out_root=tmp_path / "work",
        transcriber=inline, settings=SETTINGS, audio_runner=_audio_stub,
        ffprobe_runner=lambda cmd: json.dumps({"format": {"duration": "60"}, "streams": [{"codec_type": "video", "avg_frame_rate": "25/1"}, {"codec_type": "audio"}]}),
    )  # fmt: skip
    assert sorted(t.source for t in read_transcript(path)) == ["cued_recall", "cued_recall", "inline"]


def test_running_the_same_recording_again_replaces_it_even_when_the_asr_words_differ(tmp_path: Path) -> None:
    # Real Whisper splits the same audio differently from run to run, so exact-duplicate checks cannot work:
    # a recording owns the video time it covers (offset .. offset + audio length).
    work = _asset(tmp_path)
    _recall(tmp_path, FakeTranscriber(LINES))
    again = [
        SpokenLine(0.5, 4.0, "câu khác hẳn", "vi"),
        SpokenLine(4.0, 6.0, "một câu nữa", "vi"),
        SpokenLine(6.0, 9.0, "và câu ba", "vi"),
    ]
    result = _recall(tmp_path, FakeTranscriber(again))
    assert [t.text for t in read_transcript(work / "transcript.json")] == ["câu khác hẳn", "một câu nữa", "và câu ba"]
    assert any("thay 2 câu" in n for n in result.notes)


def test_a_recording_for_another_stretch_of_the_video_is_appended(tmp_path: Path) -> None:
    work = _asset(tmp_path)
    _recall(tmp_path, FakeTranscriber(LINES))  # covers 0..10 s
    _recall(tmp_path, FakeTranscriber([SpokenLine(1.0, 3.0, "ghi âm lần hai", "vi")]), offset=30.0)  # covers 30..40 s
    assert [t.text for t in read_transcript(work / "transcript.json")][-1] == "ghi âm lần hai"
    assert len(read_transcript(work / "transcript.json")) == 3


def test_an_overlapping_recording_replaces_the_lines_it_overlaps(tmp_path: Path) -> None:
    work = _asset(tmp_path)
    _recall(tmp_path, FakeTranscriber(LINES))  # 0..10 s
    # covers 6..16 s: overlaps the 5..8 s line but not the 0..3 s one
    _recall(tmp_path, FakeTranscriber([SpokenLine(0.0, 2.0, "thay thế", "vi")]), offset=6.0)
    texts = [t.text for t in read_transcript(work / "transcript.json")]
    assert "thay thế" in texts and "Lực ấn vừa phải" not in texts and "Tôi xoay ngược vì nếu không sẽ trầy mặt" in texts


def test_a_recording_that_runs_past_the_video_is_noted_not_refused(tmp_path: Path) -> None:
    _asset(tmp_path, duration=10.0)
    result = _recall(tmp_path, offset=12.5)
    assert any("vượt quá" in n for n in result.notes) and len(result.lines) == 2
