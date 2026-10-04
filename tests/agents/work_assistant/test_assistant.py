"""spec 06 T06-2 — Work Assistant: grounded answers or an honest refusal (AC-01..AC-04)."""

from __future__ import annotations

from pathlib import Path

import pytest

from mentormind.agents.trace import TraceLog
from mentormind.agents.work_assistant import REFUSAL, WorkAssistant
from mentormind.core.guard import GuardPolicy
from mentormind.core.providers.llm.backends.fake import FakeLLM
from mentormind.core.schemas import DataClassification
from mentormind.core.schemas.agents import AskRequest
from mentormind.knowledge_base.retrieval.hybrid import RetrievedContext
from tests.agents.fakes import REASON_PROFILE, FakeExperts, FakeRetriever, context

SYN = DataClassification.SYNTHETIC
SECRET = DataClassification.FACTORY_CONFIDENTIAL
ASK = AskRequest(question="Vì sao phải đặt linh kiện A nghiêng?", process_id="PACK01")
TWO = context(
    (*REASON_PROFILE, 0.82, SYN),
    ("WP-PACK01-004", "Bước: Đậy nắp hộp. Thao tác: ấn đều hai góc.", 0.61, SYN),
)


def assistant(llm: FakeLLM, result: RetrievedContext, tmp_path: Path) -> WorkAssistant:
    return WorkAssistant(
        FakeRetriever(result),
        llm,
        experts=FakeExperts({"PACK01": "Nguyễn Văn A"}),
        trace=TraceLog(tmp_path / "traces"),
    )


def test_ac_01_no_context_means_refusal_with_the_expert_to_ask(tmp_path: Path) -> None:
    llm = FakeLLM(["không được gọi"])
    empty = RetrievedContext(
        query="q", process_id="PACK01", passages=[], graph_facts=[], citations=[], classifications=[]
    )
    answer = assistant(llm, empty, tmp_path).ask(ASK)
    assert answer.refused and answer.answer == REFUSAL
    assert answer.suggested_contact == "Nguyễn Văn A"
    assert llm.calls == []


def test_ac_01_a_weak_best_score_is_a_refusal_too(tmp_path: Path) -> None:
    weak = context(("WP-PACK01-009", "Bước: Lau bàn.", 0.2, SYN))
    answer = assistant(FakeLLM(["x [1]"]), weak, tmp_path).ask(ASK)
    assert answer.refused


def test_ac_02_a_marker_without_citation_is_retried_then_refused(tmp_path: Path) -> None:
    llm = FakeLLM(["Đặt nghiêng để tránh trầy [3].", "Vẫn sai [3]."])
    answer = assistant(llm, TWO, tmp_path).ask(ASK)
    assert len(llm.calls) == 2 and answer.refused
    assert answer.suggested_contact == "Nguyễn Văn A"


def test_ac_02_an_answer_without_markers_gets_one_retry(tmp_path: Path) -> None:
    llm = FakeLLM(["Đặt nghiêng để tránh trầy.", "Đặt nghiêng để tránh trầy bề mặt [1]."])
    answer = assistant(llm, TWO, tmp_path).ask(ASK)
    assert len(llm.calls) == 2 and not answer.refused


def test_ac_03_the_reason_is_answered_with_the_right_profile(tmp_path: Path) -> None:
    llm = FakeLLM(["Đặt nghiêng để tránh trầy bề mặt khi đóng nắp hộp [1]."])
    answer = assistant(llm, TWO, tmp_path).ask(ASK)
    assert not answer.refused
    assert "tránh trầy bề mặt khi đóng nắp hộp" in answer.answer
    assert answer.citations[0].ref_id == "WP-PACK01-003"
    assert answer.confidence == 0.82  # mean score of the citations actually used
    assert "Lý do: tránh trầy bề mặt" in llm.calls[0].prompt  # the reason reached the prompt


def test_ac_04_a_cloud_llm_never_sees_a_confidential_passage(tmp_path: Path) -> None:
    mixed = context(
        (*REASON_PROFILE, 0.82, SYN),
        ("WP-LINE3-004", "Bước: Chỉnh lực kẹp 12 N ở trạm 3.", 0.9, SECRET),
    )
    llm = FakeLLM(["Đặt nghiêng để tránh trầy [1]."], name="qwen_api", is_cloud=True)
    llm.guard_policy = GuardPolicy(audit_dir=None)
    answer = assistant(llm, mixed, tmp_path).ask(ASK)
    sent = llm.calls[0].prompt
    assert "Chỉnh lực kẹp" not in sent and "WP-LINE3-004" not in sent
    assert [c.ref_id for c in answer.citations] == ["WP-PACK01-003"]


def test_passages_without_a_label_are_treated_as_confidential(tmp_path: Path) -> None:
    unlabelled = TWO.model_copy(update={"classifications": []})
    llm = FakeLLM(["x [1]"], name="qwen_api", is_cloud=True)
    llm.guard_policy = GuardPolicy(audit_dir=None)
    answer = assistant(llm, unlabelled, tmp_path).ask(ASK)
    assert answer.refused and llm.calls == []  # nothing is left to send to the cloud


def test_every_call_leaves_a_trace(tmp_path: Path) -> None:
    llm = FakeLLM(["Đặt nghiêng để tránh trầy [1]."])
    assistant(llm, TWO, tmp_path).ask(ASK)
    [line] = (tmp_path / "traces").glob("ask-*.jsonl")
    record = line.read_text(encoding="utf-8")
    assert '"WP-PACK01-003"' in record and '"sha256:' in record and '"refused": false' in record


@pytest.fixture(autouse=True)
def _isolated_cwd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
