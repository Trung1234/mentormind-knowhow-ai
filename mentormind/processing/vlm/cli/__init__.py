"""``knowhow vlm ...`` (spec 04 FR-05): one Typer app, commands grouped by purpose."""

from __future__ import annotations

import typer

from mentormind.processing.vlm.cli.diagnostics import ping_cmd, providers_cmd
from mentormind.processing.vlm.cli.sweep import sweep_cmd

app = typer.Typer(help="VLM mô tả thao tác từ video (spec 04).", no_args_is_help=True)
# Help texts are user-facing, hence Vietnamese (CLAUDE.md); docstrings stay English.
app.command(
    "providers", help="Liệt kê các VLM provider đã đăng ký, provider đang chọn, đã có key chưa."
)(providers_cmd)
app.command(
    "ping", help="Gọi thử VLM đang cấu hình với nhiều khung hình; in kết quả, độ trễ, token."
)(ping_cmd)
app.command(
    "sweep", help="Chạy lượt A ở nhiều fps trên một video, so với ground truth; in bảng cho slide."
)(sweep_cmd)

__all__ = ["app"]
