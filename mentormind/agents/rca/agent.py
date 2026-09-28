"""RCA Agent (spec 06 §4, T06-3): a lot or a symptom in, cause hypotheses and a 5-Why draft out.

1. A lot -> Sigma ``get_lot`` + ``get_defects`` (``LotNotFound`` goes through); the lot's
   ``defect_code`` IS the ``symptom_id`` (deterministic). A symptom text -> spec 05's matcher.
2. Graph templates called BY NAME (``root_causes_of_symptom``, ``where_symptom_occurred``,
   ``prevention_steps``); the LLM router of spec 05 is never involved (AC-08).
3. The retriever, router off, adds related steps and exceptions.
4. The LLM writes the report as JSON over numbered evidence (``prompts/rca.md``); the code then
   decides what the evidence supports: a hypothesis without evidence is ``low``, a why-level
   without evidence is ``verified=False``, 3..5 levels, at most 3 hypotheses sorted by likelihood.
   An unreadable answer (twice) falls back to the graph's own root causes.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from mentormind.agents.ports import GraphTemplates, Retriever, SigmaSource
from mentormind.agents.prompting import render_prompt
from mentormind.agents.rca.report import DISCLAIMER, RCA_SCHEMA, LlmReport, five_why, hypotheses
from mentormind.agents.trace import TraceLog
from mentormind.core.providers.errors import InvalidJSONError
from mentormind.core.providers.llm import LLMProvider, strictest
from mentormind.core.providers.llm.context import ContextPassage, filter_passages
from mentormind.core.providers.parsing import parse_json_object
from mentormind.core.schemas import (
    Citation,
    DataClassification,
    DefectRecord,
    LotRecord,
    RcaReport,
    RcaRequest,
)

PROMPTS = Path(__file__).resolve().parent / "prompts"
TEMPLATES = ("root_causes_of_symptom", "where_symptom_occurred", "prevention_steps")


class RcaAgent:
    def __init__(
        self,
        llm: LLMProvider,
        graph: GraphTemplates,
        retriever: Retriever,
        sigma: SigmaSource | None = None,
        *,
        sigma_classification: DataClassification = DataClassification.FACTORY_CONFIDENTIAL,
        trace: TraceLog | None = None,
    ) -> None:
        self.llm = llm
        self.graph = graph
        self.retriever = retriever
        self.sigma = sigma
        #: Label of Sigma and graph facts; real Sigma data is factory data (fail closed).
        self.sigma_classification = sigma_classification
        self.trace = trace or TraceLog(None)

    def investigate(self, request: RcaRequest) -> RcaReport:
        """Hypotheses + 5-Why for a lot or a symptom (spec 06 FR-02). Raises ``LotNotFound``."""
        started = time.perf_counter()
        lot, defects, symptom, process_id, symptom_ids = self._symptoms(request)
        rows = {
            name: [row for sid in symptom_ids for row in self.graph.run(name, symptom_id=sid)]
            for name in TEMPLATES
        }
        query = f"Lỗi {symptom} ở công đoạn {process_id or ''}: bước thao tác, ngoại lệ, phòng ngừa"
        context = self.retriever.retrieve(query, process_id, route=False)
        evidence, labels = self._evidence(lot, defects, rows, context)
        prompt = render_prompt(
            PROMPTS,
            "rca.md",
            symptom=symptom,
            process_id=process_id or "(chưa rõ)",
            lot_line=_lot_line(lot),
            evidence="\n".join(
                f"[{i}] ({c.ref_id}) {c.snippet}" for i, c in enumerate(evidence, 1)
            ),
        )
        prompts: list[str] = []
        parsed = self._ask(prompt, strictest(labels), prompts)
        report = RcaReport(
            lot_id=lot.lot_id if lot else None,
            symptom=symptom,
            hypotheses=hypotheses(parsed, evidence, rows),
            five_why=five_why(parsed, evidence, symptom),
            related_lots=sorted(
                {r["lot_id"] for r in rows["where_symptom_occurred"] if r.get("lot_id")}
                - ({lot.lot_id} if lot else set())
            ),
            prevention_steps=list(
                dict.fromkeys(
                    r["profile_id"] for r in rows["prevention_steps"] if r.get("profile_id")
                )
            ),
            disclaimer=DISCLAIMER,
        )
        self.trace.write(
            kind="rca",
            request=request,
            context_ids=[c.ref_id for c in evidence],
            prompts=prompts,
            response=report,
            latency_s=time.perf_counter() - started,
            llm=self.llm.name,
        )
        return report

    def _symptoms(
        self, request: RcaRequest
    ) -> tuple[LotRecord | None, list[DefectRecord], str, str | None, list[str]]:
        if request.lot_id:
            if self.sigma is None:
                raise ValueError("RCA theo lot cần Sigma adapter (spec 07).")
            lot = self.sigma.get_lot(request.lot_id)
            defects = self.sigma.get_defects(request.lot_id)
            codes = list(dict.fromkeys(d.defect_code for d in defects))
            symptom = (
                "; ".join(dict.fromkeys(d.description for d in defects)) or "không ghi nhận lỗi"
            )
            return lot, defects, symptom, lot.process_id, codes
        text = request.symptom_text or ""
        matched = self.graph.match_symptom(text)
        return None, [], text, request.process_id, [matched] if matched else []

    def _evidence(
        self,
        lot: LotRecord | None,
        defects: list[DefectRecord],
        rows: dict[str, list[dict[str, Any]]],
        context: Any,
    ) -> tuple[list[Citation], list[DataClassification]]:
        sigma: list[Citation] = [
            Citation(
                source_type="sigma",
                ref_id=d.defect_id,
                snippet=_defect_line(d, lot),
            )
            for d in defects
        ]
        sigma += [
            Citation(
                source_type="sigma",
                ref_id=r["cause_id"],
                snippet=f"Nguyên nhân đã biết: {r.get('description', '')}",
                score=r.get("confidence"),
            )
            for r in rows["root_causes_of_symptom"]
            if r.get("cause_id")
        ]
        sigma += [
            Citation(
                source_type="work_profile",
                ref_id=r["profile_id"],
                snippet=f"Bước phòng ngừa: {r.get('step', '')}",
            )
            for r in rows["prevention_steps"]
            if r.get("profile_id")
        ]
        passages = [
            ContextPassage(ref_id=c.ref_id, text=text, classification=context.label_of(i))
            for i, (text, c) in enumerate(zip(context.passages, context.citations, strict=True))
        ]
        kept = filter_passages(passages, self.llm)
        retrieved = [
            Citation(source_type="work_profile", ref_id=p.ref_id, snippet=p.text) for p in kept
        ]
        labels = [self.sigma_classification] * len(sigma) + [p.classification for p in kept]
        return sigma + retrieved, labels or [self.sigma_classification]

    def _ask(self, prompt: str, label: DataClassification, prompts: list[str]) -> LlmReport | None:
        for attempt in range(2):
            text_prompt = prompt if attempt == 0 else prompt + "\n\nLƯU Ý: chỉ trả về JSON hợp lệ."
            prompts.append(text_prompt)
            response = self.llm.generate(
                text_prompt, classification=label, json_schema=RCA_SCHEMA, temperature=0.2
            )
            try:
                return LlmReport.model_validate(parse_json_object(response.text))
            except (InvalidJSONError, ValidationError):
                continue
        return None


def _lot_line(lot: LotRecord | None) -> str:
    if lot is None:
        return ""
    return (
        f"Lot {lot.lot_id}: sản phẩm {lot.product_code}, ngày {lot.date}, ca {lot.shift}, "
        f"người vận hành {lot.operator_id}, {lot.qty} cái."
    )


def _defect_line(defect: DefectRecord, lot: LotRecord | None) -> str:
    where = f"{lot.date}, ca {lot.shift}, người vận hành {lot.operator_id}" if lot else "?"
    return (
        f"Lot {defect.lot_id} ({where}): {defect.defect_code} {defect.description}, "
        f"{defect.qty} cái"
    )
