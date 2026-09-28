"""Agent prompts live in each agent's ``prompts/*.md``, never in Python (spec 06 FR-05)."""

from __future__ import annotations

from pathlib import Path


def render_prompt(prompts_dir: Path, name: str, **values: object) -> str:
    return (prompts_dir / name).read_text(encoding="utf-8").format(**values)
