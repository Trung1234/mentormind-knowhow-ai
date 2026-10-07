"""spec 04 §5 — propose-reasons: only the expert's own words become a reason.

AC-08, AC-09 (T04-7) and AC-25..AC-27 (T04-18): the LLM points at the span of the expert's words
that says why; the span must be verbatim and not junk; the reason stored is the expert's sentence.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from mentormind.core.providers.llm.backends.fake import FakeLLM
from mentormind.core.schemas import ReasonAuditRecord
from mentormind.core.schemas.work_profile import WorkProfile, validate_against_contract
from mentormind.processing.vlm.passes.reasons import (
    MIN_EXCERPT_LETTERS,
    MIN_SPAN_LETTERS,
    QUOTE_THRESHOLD,
    REASON_SCHEMA,
    letter_count,
    propose_reasons,
    reasons_audit_path,
)

TRANSCRIPT = "giờ tôi xoay ngược linh kiện vì nếu không sẽ trầy mặt khi đóng nắp hộp"


def draft(transcript: str | None = TRANSCRIPT, number: int = 1) -> WorkProfile:
    return WorkProfile(
        schema_version="1.0",
        profile_id=f"WP-PACK01-{number:03d}",
        process_id="PACK01",
        step_order=number,
        step="Đặt linh kiện A vào ngăn trái",
        evidence={
            "video_id": "VID-TEST",
            "t_start": 1.0,
            "t_end": 3.0,
            "segment_ids": ["VID-TEST-S001"],
            "transcript_excerpt": transcript,
        },
        confidence=0.8,
        generated_by="vlm",
        data_classification="synthetic",
        status="draft",
        created_at=datetime(2026, 9, 28, tzinfo=UTC),
    )


def answer(span: str | None, has_reason: bool = True) -> dict[str, Any]:
    return {"has_reason": has_reason, "purpose_span": span}


def audit_lines(path: Path) -> list[ReasonAuditRecord]:
    return [ReasonAuditRecord.model_validate_json(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_ac_08_a_reason_the_expert_said_is_filled_in() -> None:
    llm = FakeLLM([answer("vì nếu không sẽ trầy mặt khi đóng nắp hộp")])
    [profile] = propose_reasons([draft()], llm)
    assert profile.reason == TRANSCRIPT  # the expert's sentence (one sentence here), never the AI's span
    assert (profile.reason_source, profile.status) == ("expert_verbal", "in_review")
    validate_against_contract(profile)
    [call] = llm.calls
    assert call.json_schema == REASON_SCHEMA and call.temperature == 0.0
    assert TRANSCRIPT in call.prompt and "purpose_span" in call.prompt


def test_ac_08_no_transcript_means_no_call_and_no_reason() -> None:
    llm = FakeLLM([answer("để tránh trầy")])
    [profile] = propose_reasons([draft(transcript=None)], llm)
    assert profile.reason is None and profile.status == "draft" and llm.calls == []


@pytest.mark.parametrize("said", [answer(None, has_reason=False), answer("trầy mặt", has_reason=False), answer(None)])
def test_ac_08_the_expert_giving_no_reason_leaves_the_draft_alone(said: dict[str, Any]) -> None:
    [profile] = propose_reasons([draft()], FakeLLM([said]))
    assert profile.reason is None and profile.status == "draft"


def test_ac_09_a_paraphrase_not_in_the_transcript_is_dropped() -> None:
    llm = FakeLLM([answer("Để bảo vệ bề mặt sản phẩm và đảm bảo chất lượng thẩm mỹ")])
    [profile] = propose_reasons([draft()], llm)
    assert profile.reason is None and profile.reason_source is None
    assert profile.status == "draft"


@pytest.mark.parametrize("excerpt", ["falling", "3", "หมด", "ok... ừ, à!"])
def test_ac_25_a_junk_excerpt_is_not_sent_and_gets_no_reason(excerpt: str, tmp_path: Path) -> None:
    llm = FakeLLM([answer(excerpt)])
    audit = tmp_path / "reasons_audit.jsonl"
    [profile] = propose_reasons([draft(transcript=excerpt)], llm, audit=audit)
    assert (profile.reason, profile.reason_source, profile.status) == (None, None, "draft")
    assert llm.calls == []  # nothing an LLM could quote: not asked
    [line] = audit_lines(audit)
    assert (line.decision, line.junk, line.has_reason, line.model) == ("rejected_junk", True, None, None)
    assert line.junk_why is not None and f"< {MIN_EXCERPT_LETTERS}" in line.junk_why


def test_ac_25_a_span_too_short_is_junk_even_when_verbatim(tmp_path: Path) -> None:
    audit = tmp_path / "reasons_audit.jsonl"
    [profile] = propose_reasons([draft()], FakeLLM([answer("vì nếu")]), audit=audit)
    assert profile.reason is None and profile.status == "draft"
    [line] = audit_lines(audit)
    assert (line.decision, line.junk, line.match_score) == ("rejected_junk", True, 100.0)
    assert line.junk_why is not None and f"< {MIN_SPAN_LETTERS}" in line.junk_why


def test_ac_25_letters_are_unicode_letters_without_spaces_digits_punctuation_or_marks() -> None:
    assert (MIN_SPAN_LETTERS, MIN_EXCERPT_LETTERS, QUOTE_THRESHOLD) == (6, 12, 85.0)
    assert letter_count("falling") == 7
    assert letter_count("3 , . !") == 0
    assert letter_count("để tránh cong pin") == 14  # a Vietnamese letter with its marks is one letter
    assert letter_count("เพื่อเพิ่มประสิทธิภาพ") == 15  # Thai vowel and tone marks are not letters


def test_ac_26_the_reason_is_the_expert_sentence_holding_the_span_not_the_span() -> None:
    excerpt = "Nhặt cốc lên nhé. Đặt cốc vào thùng, xếp nghiêng để cốc không bị nứt! Xong rồi."
    [profile] = propose_reasons([draft(transcript=excerpt)], FakeLLM([answer("Để cốc không bị nứt")]))
    assert profile.reason == "Đặt cốc vào thùng, xếp nghiêng để cốc không bị nứt!"
    assert (profile.reason_source, profile.status) == ("expert_verbal", "in_review")


def test_ac_26_an_excerpt_without_sentence_marks_is_one_sentence() -> None:
    excerpt = "เราต้องวางชิ้นงานให้ตรง เพื่อเพิ่มประสิทธิภาพ ของการผลิต"  # ASR Thai: no punctuation
    [profile] = propose_reasons([draft(transcript=excerpt)], FakeLLM([answer("เพื่อเพิ่มประสิทธิภาพ")]))
    assert profile.reason == excerpt


def test_ac_26_a_span_across_two_sentences_keeps_both_verbatim() -> None:
    excerpt = "Mở nắp hộp. Xếp nghiêng. Để cốc không bị nứt khi đóng. Xong."
    span = "Xếp nghiêng. Để cốc không bị nứt"
    [profile] = propose_reasons([draft(transcript=excerpt)], FakeLLM([answer(span)]))
    assert profile.reason == "Xếp nghiêng. Để cốc không bị nứt khi đóng."


def test_ac_27_every_examined_profile_gets_one_audit_line(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    profiles = [
        draft(number=1),
        draft(number=2),
        draft(number=3),
        draft(number=4),
        draft(transcript="falling", number=5),
        draft(transcript=None, number=6),  # nothing to examine: no line
    ]
    llm = FakeLLM(
        [
            answer("vì nếu không sẽ trầy mặt khi đóng nắp hộp"),
            answer("để bảo vệ bề mặt sản phẩm"),
            answer(None, has_reason=False),
            "không phải JSON",
        ]
    )
    audit = reasons_audit_path(tmp_path / "work", "VID-TEST")
    assert audit == tmp_path / "work" / "vlm" / "VID-TEST" / "reasons_audit.jsonl"
    with caplog.at_level(logging.INFO, logger="mentormind.processing.vlm.passes.reasons"):
        updated = propose_reasons(profiles, llm, audit=audit)
    lines = audit_lines(audit)
    assert [(line.profile_id, line.decision) for line in lines] == [
        ("WP-PACK01-001", "accepted"),
        ("WP-PACK01-002", "rejected_not_verbatim"),
        ("WP-PACK01-003", "no_reason"),
        ("WP-PACK01-004", "unreadable"),
        ("WP-PACK01-005", "rejected_junk"),
    ]
    accepted = lines[0]
    assert accepted.reason == updated[0].reason == TRANSCRIPT
    assert (accepted.has_reason, accepted.purpose_span) == (True, "vì nếu không sẽ trầy mặt khi đóng nắp hộp")
    assert accepted.match_score == 100.0 and accepted.junk is False and accepted.model == "fake-llm"
    assert (accepted.step, accepted.transcript_excerpt) == ("Đặt linh kiện A vào ngăn trái", TRANSCRIPT)
    assert lines[1].reason is None and lines[1].match_score is not None and lines[1].match_score < QUOTE_THRESHOLD
    raw = json.loads(audit.read_text(encoding="utf-8").splitlines()[0])
    assert set(raw) == {
        "profile_id", "step", "transcript_excerpt", "has_reason", "purpose_span", "match_score",
        "junk", "junk_why", "decision", "reason", "model", "timestamp",
    }  # fmt: skip
    assert "trầy mặt" in audit.read_text(encoding="utf-8")  # readable UTF-8, not \u escapes
    logged = [r.getMessage() for r in caplog.records if "propose-reasons" in r.getMessage()]
    assert len(logged) == 5 and "accepted" in logged[0] and "rejected_junk" in logged[4]


def test_ac_27_a_second_run_appends_to_the_audit(tmp_path: Path) -> None:
    audit = tmp_path / "vlm" / "VID-TEST" / "reasons_audit.jsonl"
    propose_reasons([draft()], FakeLLM([answer(None, has_reason=False)]), audit=audit)
    propose_reasons([draft()], FakeLLM([answer("vì nếu không sẽ trầy mặt")]), audit=audit)
    assert [line.decision for line in audit_lines(audit)] == ["no_reason", "accepted"]
