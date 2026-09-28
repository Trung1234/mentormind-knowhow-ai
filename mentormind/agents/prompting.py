"""Agent prompts live in ``agents/prompts/*.md``, never in Python (spec 06 FR-05)."""

from __future__ import annotations

from pathlib import Path

PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"


def render_prompt(name: str, **values: object) -> str:
    return (PROMPTS_DIR / name).read_text(encoding="utf-8").format(**values)
