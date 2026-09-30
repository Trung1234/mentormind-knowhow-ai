"""``knowhow vlm describe`` and ``knowhow vlm propose-reasons`` (spec 04 FR-05).

``describe`` takes the segments of spec 03 (``<video_id>`` reads
``data/work/video/<id>/segments.json``, or ``--segments FILE``) or, until spec 03 lands, a raw
``--video FILE`` cut into fixed 10 s windows (spec 03 FR-03 fallback, as ``sweep`` does). Drafts
go to the sink of ``KNOWHOW_PROFILE_SINK`` (spec 08's store when present, else
``data/work/vlm/<video_id>/profiles.json``); ``propose-reasons`` reads and updates them there.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Annotated

import typer

from mentormind.core.config import Settings, get_settings
from mentormind.core.schemas.common import DataClassification

if TYPE_CHECKING:
    from mentormind.core.providers.llm import LLMProvider
    from mentormind.core.schemas.video import Segment

WORK = Path("data/work")


def describe_cmd(
    video_id: Annotated[
        str | None, typer.Argument(help="video_id đã cắt đoạn bằng spec 03 (segments.json).")
    ] = None,
    video: Annotated[
        Path | None,
        typer.Option(
            exists=True, dir_okay=False, help="Video thô; cắt đoạn 10 s khi chưa có spec 03."
        ),
    ] = None,
    segments: Annotated[
        Path | None, typer.Option(exists=True, dir_okay=False, help="segments.json của spec 03.")
    ] = None,
    classification: Annotated[
        DataClassification,
        typer.Option(help="Nhãn dữ liệu của --video; mặc định coi là dữ liệu nhà máy."),
    ] = DataClassification.FACTORY_CONFIDENTIAL,
    process_id: Annotated[str, typer.Option(help="Mã công đoạn.")] = "PACK01",
    fps: Annotated[
        float | None,
        typer.Option(help="fps khi đoạn chưa có motion_score (mặc định KNOWHOW_VLM_FPS)."),
    ] = None,
    window: Annotated[float, typer.Option(min=3, help="Độ dài đoạn (s) cho --video.")] = 10.0,
    provider: Annotated[str | None, typer.Option(help="Ghi đè KNOWHOW_VLM_PROVIDER.")] = None,
    llm_provider: Annotated[
        str | None, typer.Option(help="LLM của lượt C; ghi đè KNOWHOW_LLM_PROVIDER.")
    ] = None,
    consistency: Annotated[
        bool, typer.Option(help="Lượt B: chạy lượt A 2 lần, giữ bước có ở cả 2 (gấp đôi token).")
    ] = True,
    merge: Annotated[
        bool, typer.Option(help="Lượt C: LLM gộp bước trùng giữa các đoạn kề.")
    ] = True,
) -> None:
    """Describe a video: passes A, B, C, then draft WorkProfiles."""
    from mentormind.core.guard import ConfidentialDataError, DataGuard
    from mentormind.core.providers.errors import ProviderError
    from mentormind.core.providers.llm.context import strictest
    from mentormind.core.providers.vlm import get_vlm_provider
    from mentormind.processing.vlm.pipeline import DescribePipeline
    from mentormind.processing.vlm.profiles import ProfileSinkError, get_profile_sink

    settings = get_settings()
    if provider:
        settings = settings.model_copy(update={"vlm_provider": provider})
    if llm_provider:
        settings = settings.model_copy(update={"llm_provider": llm_provider})
    try:
        sink = get_profile_sink(settings, work_dir=WORK)  # fail before any VLM call
        loaded = _segments(video_id, video, segments, classification, window)
        vid = loaded[0].video_id
        vlm = get_vlm_provider(settings)
        llm = _llm(settings) if merge else None
        label = strictest(s.data_classification for s in loaded)
        # Fail before any VLM token is spent when pass C could not run on this data.
        DataGuard.check(label, vlm)
        if llm is not None:
            DataGuard.check(label, llm)
        work_dir = WORK / "vlm" / vid / f"describe-{vlm.name}"
        pipeline = DescribePipeline(
            vlm,
            llm=llm,
            process_id=process_id,
            default_fps=fps or settings.vlm_fps,
            max_frames=settings.vlm_max_frames,
            consistency=consistency,
        )
        result = pipeline.run(loaded, work_dir)
    except ConfidentialDataError as exc:
        typer.secho(
            f"Lỗi: {exc}\nDữ liệu nhà máy chỉ chạy với provider tự host: KNOWHOW_VLM_PROVIDER="
            "local_openai và KNOWHOW_LLM_PROVIDER=local_openai (hoặc --no-merge).",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(1) from exc
    except (
        ProviderError, PermissionError, ValueError, RuntimeError, FileNotFoundError,
        ProfileSinkError,
    ) as exc:  # fmt: skip
        typer.secho(f"Lỗi: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1) from exc
    stored = sink.save(vid, result.profiles)
    moved = sum(a.profile_id != b.profile_id for a, b in zip(result.profiles, stored, strict=True))
    kept = len(result.steps.steps)
    typer.echo(f"provider={vlm.name} model={vlm.model} | {len(loaded)} đoạn | chi tiết: {work_dir}")
    typer.echo(
        f"lượt A: {result.pass_a_steps} bước" + (f" → lượt B giữ {kept}" if consistency else "")
    )
    if result.merge is not None:
        m = result.merge
        typer.echo(
            f"lượt C ({llm.name if llm else '-'}): gộp {m.merged}, đổi tên {m.renamed}, "
            f"bỏ bước bịa {m.invented_dropped}, từ chối {m.rejected}"
            + (f" | {m.error}" if m.error else "")
        )
    if result.failed_segments:
        typer.secho(f"{len(result.failed_segments)} đoạn lỗi JSON: {work_dir}/failed_segments.json",
                    fg=typer.colors.YELLOW)  # fmt: skip
    note = f" ({moved} đổi profile_id vì trùng profile của video khác)" if moved else ""
    typer.echo(f"{len(stored)} WorkProfile (draft) → {sink.where}{note}")


def propose_reasons_cmd(
    video_id: Annotated[str, typer.Argument(help="video_id đã chạy describe.")],
    llm_provider: Annotated[str | None, typer.Option(help="Ghi đè KNOWHOW_LLM_PROVIDER.")] = None,
) -> None:
    """Fill reasons from the expert's own words (transcript) into the video's profiles."""
    from mentormind.core.guard import ConfidentialDataError
    from mentormind.core.providers.errors import ProviderError
    from mentormind.processing.vlm.passes.reasons import propose_reasons
    from mentormind.processing.vlm.profiles import (
        FileProfileSink,
        ProfileSinkError,
        get_profile_sink,
    )

    settings = get_settings()
    if llm_provider:
        settings = settings.model_copy(update={"llm_provider": llm_provider})
    try:
        sink = get_profile_sink(settings, work_dir=WORK)
        profiles = sink.load(video_id)
    except ProfileSinkError as exc:
        typer.secho(f"Lỗi: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1) from exc
    if not profiles:
        typer.secho(
            f"Lỗi: {sink.where} chưa có profile nào của {video_id}; "
            "chạy `knowhow vlm describe` trước.",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(1)
    candidates = len([p for p in profiles if p.evidence.transcript_excerpt and p.reason is None])
    if candidates == 0:
        typer.echo(
            f"{len(profiles)} profile, không profile nào có transcript_excerpt (cần transcript của "
            "spec 03) → không có gì để làm."
        )
        return
    try:
        updated = propose_reasons(profiles, _llm(settings))
    except (ConfidentialDataError, ProviderError) as exc:
        typer.secho(f"Lỗi: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1) from exc
    changed = [new for old, new in zip(profiles, updated, strict=True) if old.reason != new.reason]
    if changed:
        # Only the profiles now in_review: re-saving untouched ones would count as id clashes.
        if isinstance(sink, FileProfileSink):
            sink.save(video_id, updated)
        else:
            sink.save(video_id, changed)
    typer.echo(
        f"{candidates} profile có transcript → điền lý do cho {len(changed)} (in_review) "
        f"→ {sink.where}"
    )


def _llm(settings: Settings) -> LLMProvider:
    from mentormind.core.providers.llm import get_llm_provider

    return get_llm_provider(settings)


def _segments(
    video_id: str | None,
    video: Path | None,
    segments: Path | None,
    classification: DataClassification,
    window: float,
) -> list[Segment]:
    from mentormind.core.schemas.video import Segment
    from mentormind.processing.vlm.sweep.windows import fixed_window_segments, video_id_for

    if [video_id, video, segments].count(None) != 2:
        raise ValueError("Chọn đúng một nguồn: <video_id>, --video hoặc --segments.")
    if video is not None:
        vid = video_id_for(video)
        return fixed_window_segments(
            video, out_dir=WORK / "video" / vid / "clips", classification=classification,
            window_s=window, video_id=vid,
        )  # fmt: skip
    path = segments or WORK / "video" / str(video_id) / "segments.json"
    if not path.is_file():
        raise FileNotFoundError(
            f"Không thấy {path} (spec 03 `knowhow video segment` chưa chạy). Dùng --video <file>."
        )
    loaded = [Segment.model_validate(s) for s in json.loads(path.read_text(encoding="utf-8"))]
    if not loaded:
        raise ValueError(f"{path} không có đoạn nào.")
    return loaded
