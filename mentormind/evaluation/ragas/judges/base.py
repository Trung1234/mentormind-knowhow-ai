"""What every judge shares: the sample it scores, the embedder it may use, the score columns."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

#: Score dict of one sample: column of ``ragas_results.csv`` -> value (None = not computable).
Scores = dict[str, float | None]


@dataclass(frozen=True)
class JudgeSample:
    question: str
    answer: str
    #: Snippets of the citations the answer carries, in rank order.
    contexts: Sequence[str]
    ground_truth: str


class TextEmbedder(Protocol):
    """``knowledge_base.store.embedding.BgeM3Embedder`` (or a fake)."""

    def embed(self, texts: Sequence[str]) -> list[list[float]]: ...


def round_score(value: object) -> float | None:
    """A score rounded like the summary; NaN and non-numbers -> None (never a made-up number)."""
    if isinstance(value, int | float) and not math.isnan(value):
        return round(float(value), 3)
    return None
