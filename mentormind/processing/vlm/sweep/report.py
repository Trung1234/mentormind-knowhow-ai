"""Sweep outputs: the CSV of spec 04 §6 and a markdown table to paste into the slides."""

from __future__ import annotations

import csv
from collections.abc import Sequence
from pathlib import Path

from mentormind.processing.vlm.sweep.metrics import SweepRow

CSV_COLUMNS = [
    "fps",
    "recall",
    "precision",
    "order_accuracy",
    "key_point_recall",
    "tokens_used",
    "latency_s",
    "fps_effective",
    "predicted",
    "truth",
    "recall_essential",
    "recall_time_only",
    "failed_segments",
    "provider",
    "model",
]


def write_csv(rows: Sequence[SweepRow], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: "" if v is None else v for k, v in row.model_dump().items()})


def markdown_table(rows: Sequence[SweepRow]) -> str:
    header = (
        "| fps | fps thực | recall | recall (chính) | recall (chỉ thời gian) | precision | order |"
        " key_point | bước dự đoán | token | độ trễ (s) |"
    )
    lines = [header, "|" + "---|" * 11]
    for r in rows:
        lines.append(
            f"| {r.fps:g} | {r.fps_effective:g} | {r.recall:.2f} | {_fmt(r.recall_essential)} | "
            f"{_fmt(r.recall_time_only)} | {r.precision:.2f} | {_fmt(r.order_accuracy)} | "
            f"{_fmt(r.key_point_recall)} | {r.predicted} | {r.tokens_used} | {r.latency_s:.1f} |"
        )
    return "\n".join(lines)


def _fmt(value: float | None) -> str:
    return "—" if value is None else f"{value:.2f}"
