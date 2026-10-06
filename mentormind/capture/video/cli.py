"""``knowhow video ...`` (spec 03 FR-01, FR-02)."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from mentormind.capture.video.hand_activity import HandActivitySegmenter
from mentormind.capture.video.media import MediaError
from mentormind.capture.video.media import Runner as MediaRunner
from mentormind.capture.video.pipeline import ClassificationMismatchError, SegmentResult, segment_video
from mentormind.capture.video.probe import ProbeError, probe
from mentormind.capture.video.probe import Runner as ProbeRunner
from mentormind.capture.video.segmenters import FixedWindowSegmenter, SceneSegmenter, Segmenter, SegmenterError
from mentormind.capture.video.transcribe import (
    AudioRunner,
    FasterWhisperTranscriber,
    Transcriber,
    TranscriberError,
    TranscribeResult,
    transcribe_recall,
    transcribe_video,
)
from mentormind.core.config import Settings, get_settings
from mentormind.core.guard.data_guard import ConfidentialDataError
from mentormind.core.schemas import DataClassification

app = typer.Typer(help="Cắt video thành đoạn, keyframe và clip (spec 03).", no_args_is_help=True)

# Test seams: tests replace these so no real ffmpeg is needed.
FFPROBE_RUNNER: ProbeRunner | None = None
MEDIA_RUNNER: MediaRunner | None = None
AUDIO_RUNNER: AudioRunner | None = None

_ERRORS = (
    FileNotFoundError,
    ConfidentialDataError,
    ClassificationMismatchError,
    ProbeError,
    MediaError,
    SegmenterError,
    TranscriberError,
)


def build_segmenters(settings: Settings) -> dict[str, Segmenter]:
    """All three strategies. ``hand_activity`` runs MediaPipe in its own process and falls back to ``scene``."""
    return {
        "hand_activity": HandActivitySegmenter(
            python=settings.hand_python,
            min_presence=settings.hand_min_presence,
            valley_min_s=settings.hand_valley_min_s,
            valley_ratio=settings.hand_valley_ratio,
            timeout_s=settings.hand_timeout_s,
        ),
        "scene": SceneSegmenter(settings.scene_threshold),
        "fixed_window": FixedWindowSegmenter(settings.segment_window_s),
    }


def build_transcriber(settings: Settings, model: str | None = None) -> Transcriber:
    """Local faster-whisper only: speech recognition never goes to a cloud service (art. 2)."""
    return FasterWhisperTranscriber(model or settings.whisper_model, settings.whisper_compute_type)


@app.command("probe", help="In VideoAsset (JSON) của một file video.")
def probe_cmd(
    video: Annotated[Path, typer.Argument(help="File video.")],
    process_id: Annotated[str | None, typer.Option("--process-id", help="Công đoạn, VD PACK01.")] = None,
    classification: Annotated[
        DataClassification,
        typer.Option("--classification", case_sensitive=False, help="Nhãn dữ liệu; mặc định nghiêm nhất."),
    ] = DataClassification.FACTORY_CONFIDENTIAL,
) -> None:
    settings = get_settings()
    try:
        asset = probe(
            video,
            process_id=process_id,
            classification=classification,
            ffprobe=settings.ffprobe_bin,
            runner=FFPROBE_RUNNER,
        )
    except ProbeError as exc:
        typer.echo(f"Lỗi: {exc}", err=True)
        raise typer.Exit(2) from exc
    typer.echo(asset.model_dump_json(indent=2))


@app.command("segment", help="Cắt đoạn, xuất keyframe + clip, ghi segments.json (data/work/video/<video_id>/).")
def segment_cmd(
    video: Annotated[Path, typer.Argument(help="File video.")],
    classification: Annotated[
        DataClassification,
        typer.Option("--classification", case_sensitive=False, help="Nhãn dữ liệu bắt buộc, áp cho mọi đoạn."),
    ],
    process_id: Annotated[str | None, typer.Option("--process-id", help="Công đoạn, VD PACK01.")] = None,
    method: Annotated[
        str, typer.Option("--method", help="scene | fixed_window | hand_activity (tự rơi về chiến lược kế tiếp).")
    ] = "scene",
    force: Annotated[bool, typer.Option("--force", help="Làm lại media và cho phép đổi nhãn.")] = False,
) -> None:
    settings = get_settings()
    try:
        result = segment_video(
            video,
            process_id=process_id,
            classification=classification,
            method=method,
            out_root=settings.work_dir / "video",
            segmenters=build_segmenters(settings),
            settings=settings,
            force=force,
            ffprobe_runner=FFPROBE_RUNNER,
            media_runner=MEDIA_RUNNER,
        )
    except ValueError as exc:  # bad --method, or a label change without --force
        typer.echo(f"Lỗi: {exc}", err=True)
        raise typer.Exit(2) from exc
    except _ERRORS as exc:
        typer.echo(f"Lỗi: {exc}", err=True)
        raise typer.Exit(2) from exc
    typer.echo(_summary(result))


def _summary(result: SegmentResult) -> str:
    lines = [
        f"{result.asset.video_id} | {result.method} | {len(result.segments)} đoạn | "
        f"{result.asset.duration_s:.1f}s video | {result.seconds:.1f}s xử lý | {result.work_dir}"
    ]
    lines.extend(f"  lưu ý: {note}" for note in result.notes)
    return "\n".join(lines)


@app.command(
    "transcribe",
    help="Phiên âm bằng Whisper local → transcript.json: audio của video, hoặc --recall-audio cho video câm.",
)
def transcribe_cmd(
    video: Annotated[Path | None, typer.Argument(help="File video (bỏ trống khi dùng --recall-audio).")] = None,
    classification: Annotated[
        DataClassification | None,
        typer.Option("--classification", case_sensitive=False, help="Nhãn dữ liệu bắt buộc khi phiên âm <file>."),
    ] = None,
    process_id: Annotated[str | None, typer.Option("--process-id", help="Công đoạn, VD PACK01.")] = None,
    language: Annotated[
        str | None, typer.Option("--language", help="Mã ngôn ngữ (vi, en, th, ...) hoặc auto để Whisper tự nhận diện.")
    ] = None,
    model: Annotated[str | None, typer.Option("--model", help="Model Whisper: tiny | base | small | ...")] = None,
    force: Annotated[bool, typer.Option("--force", help="Cho phép đổi nhãn đã ghi.")] = False,
    recall_audio: Annotated[
        Path | None, typer.Option("--recall-audio", help="File ghi âm video-cued recall của chuyên gia (video câm).")
    ] = None,
    video_id: Annotated[
        str | None, typer.Option("--video-id", help="video_id đã xử lý, dùng với --recall-audio.")
    ] = None,
    offset: Annotated[
        float, typer.Option("--offset", min=0, help="Giây trên đồng hồ video khi bắt đầu ghi âm (mặc định 0).")
    ] = 0.0,
) -> None:
    settings = get_settings()
    try:
        if recall_audio is not None:
            _require(video is None, "Không dùng <file> cùng với --recall-audio.")
            _require(video_id is not None, "--recall-audio cần --video-id.")
            _require(classification is None, "Nhãn lấy từ video đã xử lý: bỏ --classification khi dùng --recall-audio.")
            assert video_id is not None
            result = transcribe_recall(
                recall_audio,
                video_id=video_id,
                offset=offset,
                language=language or settings.whisper_language,
                out_root=settings.work_dir / "video",
                transcriber=build_transcriber(settings, model),
                settings=settings,
                audio_runner=AUDIO_RUNNER,
            )
            typer.echo(_recall_summary(result, offset))
            return
        _require(video is not None, "Cần <file> video hoặc --recall-audio.")
        _require(classification is not None, "--classification bắt buộc khi phiên âm <file>.")
        _require(video_id is None, "--video-id chỉ dùng với --recall-audio.")
        assert video is not None and classification is not None
        result = transcribe_video(
            video,
            process_id=process_id,
            classification=classification,
            language=language or settings.whisper_language,
            out_root=settings.work_dir / "video",
            transcriber=build_transcriber(settings, model),
            settings=settings,
            force=force,
            ffprobe_runner=FFPROBE_RUNNER,
            audio_runner=AUDIO_RUNNER,
        )
    except _ERRORS as exc:  # ClassificationMismatchError is a ValueError, listed above
        typer.echo(f"Lỗi: {exc}", err=True)
        raise typer.Exit(2) from exc
    except ValueError as exc:  # bad --video-id / --offset, or a usage conflict
        typer.echo(f"Lỗi: {exc}", err=True)
        raise typer.Exit(2) from exc
    typer.echo(_transcribe_summary(result))


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _transcribe_summary(result: TranscribeResult) -> str:
    languages = ", ".join(sorted({t.language for t in result.lines})) or "-"
    note = "" if result.asset.has_audio else " (video không có audio)"
    return (
        f"{result.asset.video_id} | {len(result.lines)} câu | ngôn ngữ: {languages} | "
        f"{result.seconds:.1f}s xử lý | {result.work_dir / 'transcript.json'}{note}"
    )


def _recall_summary(result: TranscribeResult, offset: float) -> str:
    languages = ", ".join(sorted({t.language for t in result.lines})) or "-"
    lines = [
        f"{result.asset.video_id} | {len(result.lines)} câu cued_recall | ngôn ngữ: {languages} | "
        f"offset {offset:g}s | {result.seconds:.1f}s xử lý | {result.work_dir / 'transcript.json'}"
    ]
    lines.extend(f"  lưu ý: {note}" for note in result.notes)
    return "\n".join(lines)
