"""``knowhow video segment``: probe → cut → keyframes + clips → ``segments.json`` (spec 03 FR-02).

Everything runs on this machine, so the data guard is consulted with a local provider only to keep
one central checkpoint for when a provider changes (constitution art. 2 and 5).
"""

from __future__ import annotations

import json
import os
import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path

from mentormind.capture.video.media import MediaError, export_clip, export_keyframes
from mentormind.capture.video.media import Runner as MediaRunner
from mentormind.capture.video.motion import ffmpeg_gray_frames, motion_profile, motion_score
from mentormind.capture.video.probe import Runner as ProbeRunner
from mentormind.capture.video.probe import probe
from mentormind.capture.video.segmenters import Segmenter, plan_segments
from mentormind.core.config import Settings
from mentormind.core.guard.data_guard import DataGuard
from mentormind.core.schemas import DataClassification
from mentormind.core.schemas.video import Segment, VideoAsset


class ClassificationMismatchError(ValueError):
    """The video was already processed with another label (never downgrade silently)."""


class LocalProvider:
    name = "local-video"
    is_cloud = False


@dataclass
class SegmentResult:
    asset: VideoAsset
    segments: list[Segment]
    #: The strategy that really produced the segments (may differ from the one requested).
    method: str
    notes: list[str] = field(default_factory=list)
    seconds: float = 0.0
    work_dir: Path = Path()


def segment_video(
    video: Path,
    *,
    process_id: str | None,
    classification: DataClassification,
    method: str,
    out_root: Path,
    segmenters: dict[str, Segmenter],
    settings: Settings,
    force: bool = False,
    ffprobe_runner: ProbeRunner | None = None,
    media_runner: MediaRunner | None = None,
    motion_frames: Callable[[Path], Iterable[bytes]] | None = None,
) -> SegmentResult:
    """Cut ``video`` and write ``<out_root>/<video_id>/{asset,segments}.json`` plus keyframes and clips.

    JSON is written last and atomically, so a failed run leaves no ``segments.json`` that points at
    missing media. Running again on the same bytes reuses existing media and rewrites identical JSON.

    Raises:
        FileNotFoundError: ``video`` does not exist.
        ConfidentialDataError: the data guard refuses ``classification`` for a local provider.
        ClassificationMismatchError: already processed with another label and no ``force``.
        ProbeError, MediaError, SegmenterError: a tool is missing or failed (messages say what to do).
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
    plan = plan_segments(video, asset.duration_s, method, segmenters)
    diffs, motion_note = _motion_profile(video, settings, motion_frames)
    notes = [*plan.notes, *([motion_note] if motion_note else [])]
    segments = []
    for index, (t_start, t_end) in enumerate(plan.bounds, start=1):
        segment_id = f"{asset.video_id}-S{index:03d}"
        keyframes = export_keyframes(
            video, t_start, t_end, segment_id, work / "keyframes",
            ffmpeg=settings.ffmpeg_bin, runner=media_runner, force=force,
        )  # fmt: skip
        clip = export_clip(
            video, t_start, t_end, segment_id, work / "clips",
            ffmpeg=settings.ffmpeg_bin, runner=media_runner, force=force,
        )  # fmt: skip
        segments.append(
            Segment(
                segment_id=segment_id,
                video_id=asset.video_id,
                index=index,
                t_start=t_start,
                t_end=t_end,
                method=plan.method,  # validated by plan_segments
                motion_score=motion_score(diffs, t_start, t_end, scale=settings.motion_scale),
                keyframes=[str(p) for p in keyframes],
                clip_path=str(clip),
                data_classification=asset.data_classification,
            )
        )
    _write_json(work / "asset.json", asset.model_dump_json(indent=2))
    _write_json(
        work / "segments.json",
        json.dumps([s.model_dump(mode="json") for s in segments], ensure_ascii=False, indent=2) + "\n",
    )
    return SegmentResult(
        asset=asset,
        segments=segments,
        method=plan.method,
        notes=notes,
        seconds=time.perf_counter() - started,
        work_dir=work,
    )


def _motion_profile(
    video: Path, settings: Settings, frames: Callable[[Path], Iterable[bytes]] | None
) -> tuple[list[float], str | None]:
    """Differences between consecutive frames, or ``[]`` and a note when ffmpeg cannot supply them.

    ``motion_score`` is optional (spec 03 Should): losing it must not lose the segments.
    """
    try:
        source = frames(video) if frames is not None else ffmpeg_gray_frames(video, ffmpeg=settings.ffmpeg_bin)
        return motion_profile(source), None
    except MediaError as exc:
        return [], f"motion_score: bỏ qua ({exc})"


def check_label_unchanged(asset_path: Path, wanted: DataClassification) -> None:
    if not asset_path.is_file():
        return
    try:
        held = VideoAsset.model_validate_json(asset_path.read_text(encoding="utf-8")).data_classification
    except ValueError:
        return  # unreadable output carries no label to protect: rewrite it
    if held is not wanted:
        raise ClassificationMismatchError(
            f"{asset_path.parent.name} đã xử lý với nhãn {held.value}, không đổi sang {wanted.value} khi chưa có --force."
        )


def _write_json(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    try:
        tmp.write_text(text, encoding="utf-8")
        os.replace(tmp, path)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
