"""``knowhow video transcribe``: local Whisper → ``transcript.json`` (spec 03 FR-07, AC-05, AC-07).

Speech recognition runs on this machine only (constitution art. 2): the audio never leaves it.
The model itself is downloaded once into the Hugging Face cache on first use.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
import time
import wave
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, Protocol

from mentormind.capture.video.media import MediaError
from mentormind.capture.video.pipeline import LocalProvider, check_label_unchanged
from mentormind.capture.video.probe import Runner as ProbeRunner
from mentormind.capture.video.probe import probe
from mentormind.core.config import Settings
from mentormind.core.guard.data_guard import DataGuard
from mentormind.core.schemas import DataClassification
from mentormind.core.schemas.video import TranscriptSegment, VideoAsset

Source = Literal["inline", "cued_recall"]
AudioRunner = Callable[[list[str]], None]
AUDIO_RATE = 16000  # Hz, mono: what Whisper expects


class TranscriberError(Exception):
    """The speech recogniser cannot run (library or model missing); the message says what to do."""


@dataclass(frozen=True)
class SpokenLine:
    """One recognised sentence, in seconds from the start of the audio."""

    start: float
    end: float
    text: str
    language: str


class Transcriber(Protocol):
    def transcribe(self, audio: Path, language: str | None) -> list[SpokenLine]:
        """``language=None`` lets the model detect it.

        Raises:
            TranscriberError: the library or model is unavailable.
        """
        ...


class FasterWhisperTranscriber:
    """faster-whisper on CPU. ``vad_filter`` keeps Whisper from inventing text over silence."""

    def __init__(self, model: str = "small", compute_type: str = "int8") -> None:
        self._model_name = model
        self._compute_type = compute_type
        self._model: Any = None

    def transcribe(self, audio: Path, language: str | None) -> list[SpokenLine]:
        if self._model is None:
            try:
                from faster_whisper import WhisperModel
            except ImportError as exc:
                raise TranscriberError("Thiếu faster-whisper: cài extra `video` (uv sync --extra video).") from exc
            try:
                self._model = WhisperModel(self._model_name, device="cpu", compute_type=self._compute_type)
            except Exception as exc:  # model download / load failures come in many types
                raise TranscriberError(
                    f"Không nạp được model Whisper {self._model_name!r} (lần đầu cần mạng để tải về cache): {exc}"
                ) from exc
        segments, info = self._model.transcribe(str(audio), language=language, vad_filter=True)
        detected = language or info.language
        return [SpokenLine(float(s.start), float(s.end), str(s.text), detected) for s in segments]


@dataclass
class TranscribeResult:
    asset: VideoAsset
    lines: list[TranscriptSegment]
    seconds: float = 0.0
    work_dir: Path = Path()
    notes: list[str] = field(default_factory=list)


def transcribe_video(
    video: Path,
    *,
    process_id: str | None,
    classification: DataClassification,
    language: str,
    out_root: Path,
    transcriber: Transcriber,
    settings: Settings,
    force: bool = False,
    ffprobe_runner: ProbeRunner | None = None,
    audio_runner: AudioRunner | None = None,
) -> TranscribeResult:
    """Transcribe the audio of ``video`` into ``<out_root>/<video_id>/transcript.json``.

    ``language="auto"`` lets Whisper detect it. A video without an audio stream gives ``[]`` (AC-05).
    Re-running replaces this video's ``inline`` lines and keeps any ``cued_recall`` lines. The label
    comes from the video's ``asset.json`` (AC-07); asking for another one is an error without ``force``.

    Raises:
        FileNotFoundError: ``video`` does not exist.
        ClassificationMismatchError: already processed with another label and no ``force``.
        ProbeError, MediaError, TranscriberError: a tool is missing or failed.
    """
    if not video.is_file():
        raise FileNotFoundError(f"Không thấy file video: {video}")
    DataGuard.check(classification, LocalProvider())
    started = time.perf_counter()
    asset = probe(
        video, process_id=process_id, classification=classification, ffprobe=settings.ffprobe_bin, runner=ffprobe_runner
    )
    work = out_root / asset.video_id
    if not force:
        check_label_unchanged(work / "asset.json", classification)
    spoken: list[SpokenLine] = []
    if asset.has_audio:
        with tempfile.TemporaryDirectory() as tmp:
            wav = extract_audio(video, Path(tmp) / "audio.wav", ffmpeg=settings.ffmpeg_bin, runner=audio_runner)
            spoken = transcriber.transcribe(wav, None if language == "auto" else language)
    lines = merge_transcript(
        work / "transcript.json",
        to_transcript_segments(spoken, asset, "inline"),
        drop=lambda t: t.source == "inline",  # a re-run replaces the inline lines and keeps the recall ones
    )
    _write_asset(work / "asset.json", asset)
    return TranscribeResult(
        asset=asset,
        lines=[t for t in lines if t.source == "inline"],
        seconds=time.perf_counter() - started,
        work_dir=work,
    )


_VIDEO_ID = re.compile(r"^VID-[A-Za-z0-9_-]+$")


def transcribe_recall(
    audio: Path,
    *,
    video_id: str,
    offset: float,
    language: str,
    out_root: Path,
    transcriber: Transcriber,
    settings: Settings,
    audio_runner: AudioRunner | None = None,
) -> TranscribeResult:
    """Transcribe an expert's video-cued recall recording for a (silent) video that was already processed.

    The expert replays the video and speaks; timestamps are the audio's own plus ``offset`` (the
    moment, on the video's clock, when the recording started). Lines are tagged ``cued_recall``,
    take their label from the video's ``asset.json`` (AC-07) and are stored in ``transcript.json``.

    A recording owns the video time it covers (``offset`` to ``offset`` + audio length): recall lines
    already stored in that stretch are replaced, others are kept. Real ASR splits the same audio
    differently on every run, so comparing words could not tell a re-run from a new recording.

    Raises:
        ValueError: ``video_id`` is malformed (it becomes a folder name) or ``offset`` is negative.
        FileNotFoundError: the audio file or the video's ``asset.json`` does not exist (nothing is written).
        MediaError, TranscriberError: a tool is missing or failed.
    """
    if not _VIDEO_ID.fullmatch(video_id):
        raise ValueError(f"--video-id {video_id!r} không hợp lệ (dạng VID-<mã>).")
    if offset < 0:
        raise ValueError(f"--offset phải >= 0, nhận {offset}.")
    work = out_root / video_id
    if not (work / "asset.json").is_file():
        raise FileNotFoundError(
            f"Không thấy video {video_id} trong {out_root} — chạy `knowhow video segment` hoặc `transcribe` trước."
        )
    if not audio.is_file():
        raise FileNotFoundError(f"Không thấy file ghi âm: {audio}")
    asset = VideoAsset.model_validate_json((work / "asset.json").read_text(encoding="utf-8"))
    DataGuard.check(asset.data_classification, LocalProvider())
    started = time.perf_counter()
    with tempfile.TemporaryDirectory() as tmp:
        wav = extract_audio(audio, Path(tmp) / "recall.wav", ffmpeg=settings.ffmpeg_bin, runner=audio_runner)
        span = _wav_seconds(wav)
        spoken = transcriber.transcribe(wav, None if language == "auto" else language)
    shifted = [SpokenLine(line.start + offset, line.end + offset, line.text, line.language) for line in spoken]
    new = to_transcript_segments(shifted, asset, "cued_recall")
    notes = []
    if new and max(t.t_end for t in new) > asset.duration_s + 1.0:
        notes.append(
            f"có câu kết thúc sau {asset.duration_s:.1f}s (hết video): kiểm tra lại --offset ({offset:g}s) — lời bình vượt quá video"
        )
    span_start, span_end = offset, offset + span
    replaced = [t for t in read_transcript(work / "transcript.json") if _in_span(t, span_start, span_end)]
    merge_transcript(work / "transcript.json", new, drop=lambda t: _in_span(t, span_start, span_end))
    if replaced:
        notes.append(f"đã thay {len(replaced)} câu ghi âm cũ trong khoảng {span_start:g}–{span_end:g}s của video")
    return TranscribeResult(asset=asset, lines=new, seconds=time.perf_counter() - started, work_dir=work, notes=notes)


def extract_audio(video: Path, out: Path, *, ffmpeg: str = "ffmpeg", runner: AudioRunner | None = None) -> Path:
    """Write ``video``'s audio as 16 kHz mono WAV.

    Raises:
        MediaError: ffmpeg is missing or fails.
    """
    command = [
        ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", str(video),
        "-vn", "-ac", "1", "-ar", str(AUDIO_RATE), str(out),
    ]  # fmt: skip
    try:
        (runner or _run)(command)
    except FileNotFoundError as exc:
        raise MediaError(f"Không chạy được {ffmpeg!r}: cài ffmpeg (macOS: `brew install ffmpeg`).") from exc
    except subprocess.CalledProcessError as exc:
        raise MediaError(f"ffmpeg không tách được audio của {video.name}: {(exc.stderr or str(exc)).strip()}") from exc
    return out


def _wav_seconds(path: Path) -> float:
    try:
        with wave.open(str(path)) as handle:
            return handle.getnframes() / handle.getframerate()
    except (wave.Error, EOFError, ZeroDivisionError) as exc:
        raise MediaError(f"Không đọc được thời lượng audio đã tách từ {path.name}: {exc}") from exc


def _in_span(line: TranscriptSegment, start: float, end: float) -> bool:
    """A cued-recall line that overlaps the video time a recording covers (that recording owns it)."""
    return line.source == "cued_recall" and line.t_start < end and line.t_end > start


def to_transcript_segments(lines: list[SpokenLine], asset: VideoAsset, source: Source) -> list[TranscriptSegment]:
    """Drop blank text and lines whose end is not after their start; carry the video's label (AC-07)."""
    return [
        TranscriptSegment(
            video_id=asset.video_id,
            t_start=round(line.start, 3),
            t_end=round(line.end, 3),
            text=line.text.strip(),
            language=line.language,
            source=source,
            data_classification=asset.data_classification,
        )
        for line in lines
        if line.text.strip() and line.end > line.start
    ]


def read_transcript(path: Path) -> list[TranscriptSegment]:
    if not path.is_file():
        return []
    return [TranscriptSegment.model_validate(item) for item in json.loads(path.read_text(encoding="utf-8"))]


def merge_transcript(
    path: Path, new: list[TranscriptSegment], *, drop: Callable[[TranscriptSegment], bool]
) -> list[TranscriptSegment]:
    """Store ``new`` in ``path`` in place of the existing lines for which ``drop`` is true.

    Everything else already stored is kept. The result is sorted by start time and written
    atomically. Returns everything now stored.
    """
    kept = [t for t in read_transcript(path) if not drop(t)]
    merged = sorted([*kept, *new], key=lambda t: (t.t_start, t.t_end, t.source))
    _write_text(path, json.dumps([t.model_dump(mode="json") for t in merged], ensure_ascii=False, indent=2) + "\n")
    return merged


def _write_asset(path: Path, asset: VideoAsset) -> None:
    _write_text(path, asset.model_dump_json(indent=2))


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    try:
        tmp.write_text(text, encoding="utf-8")
        os.replace(tmp, path)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise


def _run(command: list[str]) -> None:
    subprocess.run(command, check=True, capture_output=True, text=True)
