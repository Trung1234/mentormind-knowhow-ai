"""The four Ragas metrics (spec 09 §3B), judged by an LLM through the project's own provider.

Definitions follow Ragas:

* ``faithfulness``      claims of the answer supported by the contexts / all claims
* ``answer_relevancy``  mean similarity between the question and questions regenerated from the
                        answer; 0 when the answer is noncommittal
* ``context_precision`` average precision of the contexts' usefulness for the ground truth, in rank
                        order (useful contexts ranked first score higher)
* ``context_recall``    sentences of the ground truth found in the contexts / all sentences

The judge is an ordinary ``LLMProvider``, so every call goes through DataGuard, PII masking and the
audit log (the ``ragas`` package would call its own client and bypass them). Similarity of
questions is ``token_set_ratio`` for now; swap in the spec 05 embedder when it exists.
A metric the judge cannot answer (bad JSON) is ``None`` for that question, never a made-up number.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from rapidfuzz import fuzz, utils

from mentormind.core.providers.errors import InvalidJSONError
from mentormind.core.providers.llm import LLMProvider
from mentormind.core.providers.parsing import parse_json_object
from mentormind.core.schemas import DataClassification

log = logging.getLogger(__name__)
PROMPTS = Path(__file__).resolve().parent / "prompts"


class LlmJudge:
    def __init__(self, llm: LLMProvider) -> None:
        self.llm = llm
        self.failures = 0

    def faithfulness(self, answer: str, contexts: Sequence[str], label: DataClassification) -> float | None:
        data = self._judge("faithfulness.md", label, contexts=_numbered(contexts), answer=answer)
        claims = [c for c in (data or {}).get("claims", []) if isinstance(c, dict)]
        if not claims:
            return None
        return sum(bool(c.get("supported")) for c in claims) / len(claims)

    def answer_relevancy(self, question: str, answer: str, label: DataClassification) -> float | None:
        data = self._judge("answer_relevancy.md", label, question=question, answer=answer)
        if data is None:
            return None
        if data.get("noncommittal"):
            return 0.0
        generated = [q for q in data.get("questions", []) if isinstance(q, str) and q.strip()]
        if not generated:
            return None
        scores = [fuzz.token_set_ratio(q, question, processor=utils.default_process) for q in generated]
        return sum(scores) / len(scores) / 100

    def context_precision(
        self, question: str, contexts: Sequence[str], ground_truth: str, label: DataClassification
    ) -> float | None:
        if not contexts:
            return None
        data = self._judge(
            "context_precision.md",
            label,
            question=question,
            ground_truth=ground_truth,
            contexts=_numbered(contexts),
            n=len(contexts),
        )
        verdicts = [bool(v) for v in (data or {}).get("verdicts", [])][: len(contexts)]
        if not verdicts or not any(verdicts):
            return 0.0 if verdicts else None
        hits, total = 0, 0.0
        for rank, useful in enumerate(verdicts, start=1):
            if useful:
                hits += 1
                total += hits / rank
        return total / hits

    def context_recall(self, contexts: Sequence[str], ground_truth: str, label: DataClassification) -> float | None:
        data = self._judge("context_recall.md", label, ground_truth=ground_truth, contexts=_numbered(contexts))
        sentences = [s for s in (data or {}).get("sentences", []) if isinstance(s, dict)]
        if not sentences:
            return None
        return sum(bool(s.get("attributed")) for s in sentences) / len(sentences)

    def _judge(self, template: str, label: DataClassification, **values: Any) -> dict[str, Any] | None:
        prompt = (PROMPTS / template).read_text(encoding="utf-8").format(**values)
        text = self.llm.generate(prompt, classification=label, temperature=0.0).text
        try:
            return parse_json_object(text)
        except InvalidJSONError:
            self.failures += 1
            log.warning("judge answer for %s is not JSON", template)
            return None


def _numbered(contexts: Sequence[str]) -> str:
    return "\n".join(f"[{i}] {c}" for i, c in enumerate(contexts, start=1)) or "(không có)"
