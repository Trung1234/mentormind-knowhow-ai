"""The agents behind the REST routers of spec 08 (``/assistant/ask``, ``/rca/investigate``).

The routers call ``mentormind.agents.supervisor.ask`` and ``mentormind.agents.rca.investigate``
with the API models of ``core.schemas.api`` and fall back to their demo answer on ``ImportError``.
This module translates between those models and the agents' own (spec 06 §3, §4):

* ``KNOWHOW_API_AGENTS=mock`` (default) raises ``AgentsOffline`` (an ``ImportError``), so the
  routers keep their demo answers;
* ``live`` runs the agents: an unknown lot is a 404, a missing component or LLM a 503.
"""

from __future__ import annotations

from collections.abc import Callable
from functools import lru_cache
from typing import TypeVar

from pydantic import ValidationError

from mentormind.agents.adapters.factory import AgentWiringError, build_rca_agent, build_work_assistant
from mentormind.agents.rca import RcaAgent
from mentormind.agents.work_assistant import WorkAssistant
from mentormind.core.config import get_settings
from mentormind.core.guard import ConfidentialDataError
from mentormind.core.providers.errors import ProviderError
from mentormind.core.schemas import agents as spec06
from mentormind.core.schemas import api

T = TypeVar("T")


class AgentsOffline(ImportError):
    """``KNOWHOW_API_AGENTS=mock``: the router answers with its demo data."""


def ask(request: api.AskRequest) -> api.AssistantAnswer:
    answer = _call(lambda: _assistant().ask(to_ask(request)))
    return from_answer(answer)


def investigate(request: api.RcaRequest) -> api.RcaReport:
    from fastapi import HTTPException, status

    from mentormind.knowledge_base.sigma.adapter import LotNotFound

    try:
        spec_request = to_rca(request)
    except ValidationError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cần cung cấp lot_id hoặc mô tả triệu chứng lỗi.") from exc
    try:
        report = _call(lambda: _rca_agent().investigate(spec_request))
    except LotNotFound as exc:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, f"Không tìm thấy lô sản xuất với lot_id: {request.lot_id}"
        ) from exc
    return from_report(report)


def to_ask(request: api.AskRequest) -> spec06.AskRequest:
    return spec06.AskRequest(question=request.question, process_id=request.process_id or None)


def from_answer(answer: spec06.AssistantAnswer) -> api.AssistantAnswer:
    return api.AssistantAnswer(
        answer=answer.answer,
        refused=answer.refused,
        suggested_expert=answer.suggested_contact,
        citations=answer.citations,
    )


def to_rca(request: api.RcaRequest) -> spec06.RcaRequest:
    return spec06.RcaRequest(lot_id=request.lot_id, symptom_text=request.symptom)


def from_report(report: spec06.RcaReport) -> api.RcaReport:
    return api.RcaReport(
        lot_id=report.lot_id,
        symptom=report.symptom,
        hypotheses=[
            api.Hypothesis(
                hypothesis=h.cause,
                likelihood=h.likelihood,
                evidence_refs=[c.ref_id for c in h.evidence],
            )
            for h in report.hypotheses
        ],
        five_whys=[
            api.WhyStep(order=i, question=w.why, answer=w.answer, verified=w.verified)
            for i, w in enumerate(report.five_why, start=1)
        ],
        related_lots=report.related_lots,
        preventive_actions=report.prevention_steps,
        disclaimer=report.disclaimer,
    )


def _call(run: Callable[[], T]) -> T:
    from fastapi import HTTPException, status

    if get_settings().api_agents != "live":
        raise AgentsOffline("KNOWHOW_API_AGENTS=mock")
    try:
        return run()
    except (AgentWiringError, ProviderError, ConfidentialDataError) as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, f"Agent chưa sẵn sàng: {exc}") from exc


@lru_cache(maxsize=1)
def _assistant() -> WorkAssistant:
    return build_work_assistant(get_settings())


@lru_cache(maxsize=1)
def _rca_agent() -> RcaAgent:
    return build_rca_agent(get_settings())
