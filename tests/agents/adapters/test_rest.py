"""The agents behind spec 08's routers: demo answers by default, the agents with ``live``."""

from __future__ import annotations

import json
from typing import Any

import pytest
from fastapi import HTTPException

from mentormind.agents.adapters import rest
from mentormind.agents.adapters.factory import AgentWiringError
from mentormind.agents.rca import RcaAgent
from mentormind.agents.work_assistant import WorkAssistant
from mentormind.backend.app.routers import assistant as assistant_router
from mentormind.backend.app.routers import rca as rca_router
from mentormind.core.config import Settings
from mentormind.core.providers.llm.backends.fake import FakeLLM
from mentormind.core.schemas import AskRequest, DataClassification, RcaRequest
from tests.agents.fakes import (
    REASON_PROFILE,
    FakeEmbedder,
    FakeExperts,
    FakeGraph,
    FakeRetriever,
    FakeSigma,
    context,
    reply,
)
from tests.agents.rca.test_agent import D03, GRAPH_ROWS, LOT, WHY

SYNTHETIC = DataClassification.SYNTHETIC


def live(monkeypatch: pytest.MonkeyPatch, **agents: Any) -> None:
    monkeypatch.setattr(rest, "get_settings", lambda: Settings(api_agents="live"))
    for name, agent in agents.items():
        monkeypatch.setattr(rest, name, lambda agent=agent: agent)


def rca_agent(llm: FakeLLM) -> RcaAgent:
    return RcaAgent(
        llm,
        FakeGraph(GRAPH_ROWS, {"trầy": "D-03"}),
        FakeRetriever(context((*REASON_PROFILE, 0.8, SYNTHETIC))),
        FakeSigma([LOT], [D03]),
        sigma_classification=SYNTHETIC,
    )


def test_by_default_the_routers_keep_their_demo_answers(monkeypatch: pytest.MonkeyPatch) -> None:
    assert Settings.model_fields["api_agents"].default == "mock"
    monkeypatch.setattr(rest, "get_settings", lambda: Settings(api_agents="mock"))
    report = rca_router.investigate(RcaRequest(lot_id="LOT-2026-001"))
    assert len(report.five_whys) == 5  # the router's demo report
    answer = assistant_router.ask_assistant(AskRequest(process_id="PACK01", question="Cách xếp?"))
    assert answer.refused is False and answer.citations


def test_live_ask_answers_with_the_work_assistant(monkeypatch: pytest.MonkeyPatch) -> None:
    assistant = WorkAssistant(
        FakeRetriever(context((*REASON_PROFILE, 0.8, SYNTHETIC))),
        FakeLLM([reply("Đặt nghiêng để tránh trầy bề mặt [1].", [1])]),
        embedder=FakeEmbedder(),
    )
    live(monkeypatch, _assistant=assistant)
    answer = assistant_router.ask_assistant(AskRequest(process_id="PACK01", question="Vì sao đặt nghiêng?"))
    assert answer.answer.startswith("Đặt nghiêng") and not answer.refused
    assert [c.ref_id for c in answer.citations] == ["WP-PACK01-003"]


def test_live_refusal_names_the_expert(monkeypatch: pytest.MonkeyPatch) -> None:
    assistant = WorkAssistant(
        FakeRetriever(context()), FakeLLM([]), embedder=FakeEmbedder(), experts=FakeExperts({"PACK01": "Anh Tuấn"})
    )
    live(monkeypatch, _assistant=assistant)
    answer = assistant_router.ask_assistant(AskRequest(process_id="PACK01", question="Ai làm?"))
    assert answer.refused and answer.suggested_expert == "Anh Tuấn" and answer.citations == []


def test_live_rca_report_in_the_api_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    llm = FakeLLM([
        json.dumps(
            {"hypotheses": [{"cause": "Đặt nằm ngang", "likelihood": "high", "evidence_ids": [2]}],
             "five_why": WHY},
            ensure_ascii=False,
        )
    ])  # fmt: skip
    live(monkeypatch, _rca_agent=rca_agent(llm))
    report = rca_router.investigate(RcaRequest(lot_id=LOT.lot_id))
    [h] = report.hypotheses
    assert h.hypothesis == "Đặt nằm ngang" and h.evidence_refs == ["defect_catalog.csv#D-03"]
    assert [w.order for w in report.five_whys] == [1, 2, 3]
    assert report.related_lots == ["L-2026-0921-01"] and report.preventive_actions == ["WP-PACK01-003"]


def test_ac_06_live_unknown_lot_is_404(monkeypatch: pytest.MonkeyPatch) -> None:
    live(monkeypatch, _rca_agent=rca_agent(FakeLLM([])))
    with pytest.raises(HTTPException) as exc:
        rca_router.investigate(RcaRequest(lot_id="KHONG-TON-TAI"))
    assert exc.value.status_code == 404


def test_live_without_lot_or_symptom_is_400(monkeypatch: pytest.MonkeyPatch) -> None:
    live(monkeypatch)
    with pytest.raises(HTTPException) as exc:
        rca_router.investigate(RcaRequest())
    assert exc.value.status_code == 400


def test_live_with_a_missing_component_is_503(monkeypatch: pytest.MonkeyPatch) -> None:
    def missing() -> WorkAssistant:
        raise AgentWiringError("Thiếu thư viện của spec 05 (neo4j).")

    monkeypatch.setattr(rest, "get_settings", lambda: Settings(api_agents="live"))
    monkeypatch.setattr(rest, "_assistant", missing)
    with pytest.raises(HTTPException) as exc:
        assistant_router.ask_assistant(AskRequest(process_id="PACK01", question="Vì sao?"))
    assert exc.value.status_code == 503
