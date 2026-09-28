"""Hand-labelled truth for the sweep (spec 04 §6): ``{step, t_start, t_end, key_point?}``."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class TruthStep(BaseModel):
    """One hand-labelled step (spec 04 §6: ``{step, t_start, t_end, key_point?}``)."""

    model_config = ConfigDict(extra="ignore")

    step: str
    t_start: float = Field(ge=0)
    t_end: float = Field(ge=0)
    key_point: str | None = None
    #: Part of the main process; ``recall_essential`` counts only these.
    essential: bool = True


def load_truth(path: Path) -> list[TruthStep]:
    """Truth file: a bare list of steps, or an object with a ``steps`` list (+ metadata)."""
    data = json.loads(path.read_text(encoding="utf-8"))
    items = data["steps"] if isinstance(data, dict) else data
    return [TruthStep.model_validate(item) for item in items]
