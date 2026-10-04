"""Scripted judge and assistant for the evaluation tests."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any

from mentormind.core.providers.llm.backends.fake import FakeLLM
from mentormind.core.providers.models import TokenUsage
from mentormind.core.schemas import Citation
from mentormind.core.schemas.agents import AskRequest, AssistantAnswer

#: What the judge answers for each metric prompt (the tag on the prompt's first line).
JUDGE: dict[str, Any] = {
    "faithfulness": {
        "claims": [
            {"claim": "a", "supported": True},
            {"claim": "b", "supported": True},
            {"claim": "c", "supported": False},
            {"claim": "d", "supported": True},
        ]
    },
    "answer_relevancy": {"questions": ["q"], "noncommittal": False},
    "context_precision": {"verdicts": [True, False]},
    "context_recall": {"sentences": [{"sentence": "s", "attributed": True}]},
}


class ScriptedJudge(FakeLLM):
    """Answers by metric; ``answer_relevancy`` echoes the question so the similarity is 1."""

    def _complete(
        self,
        prompt: str,
        *,
        system: str | None,
        json_schema: Mapping[str, Any] | None,
        temperature: float | None,
        max_tokens: int | None,
    ) -> tuple[str, TokenUsage | None]:
        super()._complete(
            prompt,
            system=system,
            json_schema=json_schema,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        tag = prompt.split("]", 1)[0].lstrip("[")
        answer = dict(JUDGE[tag])
        if tag == "answer_relevancy":
            question = prompt.split("CÂU HỎI GỐC: ", 1)[1].splitlines()[0]
            answer = {"questions": [question], "noncommittal": False}
        return json.dumps(answer, ensure_ascii=False), None


def cite(*refs: str) -> list[Citation]:
    return [Citation(source_type="work_profile", ref_id=r, snippet=f"nội dung {r}", score=0.8) for r in refs]


class ScriptedAssistant:
    """Per-qid answers keyed by question text."""

    def __init__(self, answers: Mapping[str, AssistantAnswer]) -> None:
        self.answers = answers
        self.asked: list[AskRequest] = []

    def ask(self, request: AskRequest) -> AssistantAnswer:
        self.asked.append(request)
        return self.answers[request.question]


def answered(text: str, refs: Sequence[str]) -> AssistantAnswer:
    return AssistantAnswer(answer=text, citations=cite(*refs), confidence=0.8, refused=False)


REFUSED = AssistantAnswer(answer="Chưa có thông tin.", confidence=0.0, refused=True)
