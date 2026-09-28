"""``knowhow vlm ...`` (spec 04 FR-05): one Typer app, commands grouped by purpose."""

from __future__ import annotations

import typer

from mentormind.processing.vlm.cli.diagnostics import ping_cmd, providers_cmd
from mentormind.processing.vlm.cli.sweep import sweep_cmd

app = typer.Typer(help="VLM mô tả thao tác từ video (spec 04).", no_args_is_help=True)
app.command("providers")(providers_cmd)
app.command("ping")(ping_cmd)
app.command("sweep")(sweep_cmd)

__all__ = ["app"]
