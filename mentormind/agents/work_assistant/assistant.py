"""Work Assistant (spec 06 §3, T06-2): a new worker asks about a step, gets a grounded answer.

1. Retrieve (spec 05 ``HybridRetriever``). Passages a cloud LLM may not receive are dropped first
   (constitution art. 2): ``factory_confidential``, or unlabelled (fail closed).
2. Nothing left, or the best score below ``KNOWHOW_ASSIST_MIN_SCORE`` -> refuse and name the expert
   with the most contributions to the process.
3. Ask the LLM (``prompts/assistant.md``): context only, markers [n], reason and exceptions if any.
4. Post-check: every marker must point at a source and there must be at least one; otherwise ask
   again once, and refuse if the second answer still fails (constitution art. 4: no answer without
   a source).
5. ``confidence`` = mean score of the citations the answer actually uses.
"""

from __future__ import annotations

import re
import time
from pathlib import Path

from mentormind.agents.ports import ExpertDirectory, Retriever, passage_label
from mentormind.agents.prompting import render_prompt
from mentormind.agents.trace import TraceLog
from mentormind.core.providers.llm import LLMProvider, strictest
from mentormind.core.providers.llm.context import ContextPassage, filter_passages
from mentormind.core.schemas import Citation
from mentormind.core.schemas.agents import AskRequest, AssistantAnswer
from mentormind.knowledge_base.retrieval.hybrid import RetrievedContext

PROMPTS = Path(__file__).resolve().parent / "prompts"
DEFAULT_MIN_SCORE = 0.35
REFUSAL = (
    "Mình chưa có thông tin đã được chuyên gia duyệt để trả lời câu này, nên không trả lời để tránh hướng dẫn sai."
)
RETRY_NOTE = (
    "\n\nLƯU Ý: câu trả lời trước thiếu marker nguồn hoặc dùng số nguồn không có. Mỗi ý phải kèm "
    "[n] với n trong khoảng 1..{n}."
)
_MARKER = re.compile(r"\[(\d+)\]")


class WorkAssistant:
    def __init__(
        self,
        retriever: Retriever,
        llm: LLMProvider,
        *,
        experts: ExpertDirectory | None = None,
        min_score: float = DEFAULT_MIN_SCORE,
        trace: TraceLog | None = None,
    ) -> None:
        self.retriever = retriever
        self.llm = llm
        self.experts = experts
        self.min_score = min_score
        self.trace = trace or TraceLog(None)

    def ask(self, request: AskRequest) -> AssistantAnswer:
        """Answer ``request`` from retrieved context only, or refuse (spec 06 FR-01)."""
        started = time.perf_counter()
        context = self.retriever.retrieve(request.question, request.process_id)
        sources = self._allowed_sources(context)
        prompts: list[str] = []
        answer = self._answer(request, context, sources, prompts)
        self.trace.write(
            kind="ask",
            request=request,
            context_ids=[c.ref_id for _, c in sources],
            prompts=prompts,
            response=answer,
            latency_s=time.perf_counter() - started,
            llm=self.llm.name,
        )
        return answer

    def _answer(
        self,
        request: AskRequest,
        context: RetrievedContext,
        sources: list[tuple[ContextPassage, Citation]],
        prompts: list[str],
    ) -> AssistantAnswer:
        best = max((c.score or 0.0 for _, c in sources), default=0.0)
        if not sources or best < self.min_score:
            return self._refuse(request)
        prompt = render_prompt(
            PROMPTS,
            "assistant.md",
            process_id=request.process_id or "(chưa rõ)",
            sources="\n".join(f"[{i}] ({c.ref_id}) {p.text}" for i, (p, c) in enumerate(sources, start=1)),
            facts=self._facts(context),
            question=request.question,
        )
        label = strictest(p.classification for p, _ in sources)
        citations = [c for _, c in sources]
        for attempt in range(2):
            text_prompt = prompt if attempt == 0 else prompt + RETRY_NOTE.format(n=len(sources))
            prompts.append(text_prompt)
            text = self.llm.generate(text_prompt, classification=label, temperature=0.2).text
            used = _markers(text)
            if used and all(1 <= n <= len(citations) for n in used):
                scores = [citations[n - 1].score or 0.0 for n in sorted(used)]
                return AssistantAnswer(
                    answer=text.strip(),
                    citations=citations,
                    confidence=round(sum(scores) / len(scores), 3),
                    refused=False,
                )
        return self._refuse(request)

    def _allowed_sources(self, context: RetrievedContext) -> list[tuple[ContextPassage, Citation]]:
        passages = [
            ContextPassage(ref_id=c.ref_id, text=text, classification=passage_label(context, i))
            for i, (text, c) in enumerate(zip(context.passages, context.citations, strict=True))
        ]
        kept = {id(p) for p in filter_passages(passages, self.llm)}
        return [(p, c) for p, c in zip(passages, context.citations, strict=True) if id(p) in kept]

    def _facts(self, context: RetrievedContext) -> str:
        # Graph facts carry no label of their own: only a self-hosted LLM receives them.
        if self.llm.is_cloud or not context.graph_facts:
            return ""
        return "Thông tin quan hệ (tham khảo, không đánh số):\n" + "\n".join(
            f"- {fact}" for fact in context.graph_facts
        )

    def _refuse(self, request: AskRequest) -> AssistantAnswer:
        contact = None
        if self.experts is not None and request.process_id:
            contact = self.experts.top_contributor(request.process_id)
        return AssistantAnswer(answer=REFUSAL, citations=[], confidence=0.0, refused=True, suggested_contact=contact)


def _markers(text: str) -> set[int]:
    return {int(n) for n in _MARKER.findall(text)}
