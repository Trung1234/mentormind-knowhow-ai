"""spec 04 T04-7 — propose-reasons: only the expert's own words become a reason (AC-08, AC-09)."""

from __future__ import annotations

from datetime import UTC, datetime

from mentormind.core.providers.llm.backends.fake import FakeLLM
from mentormind.core.schemas.work_profile import WorkProfile, validate_against_contract
from mentormind.processing.vlm.passes.reasons import propose_reasons

TRANSCRIPT = "giờ tôi xoay ngược linh kiện vì nếu không sẽ trầy mặt khi đóng nắp hộp"


def draft(transcript: str | None = TRANSCRIPT) -> WorkProfile:
    return WorkProfile(
        schema_version="1.0",
        profile_id="WP-PACK01-001",
        process_id="PACK01",
        step_order=1,
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


def test_ac_08_a_reason_the_expert_said_is_filled_in() -> None:
    llm = FakeLLM([{"reason": "vì nếu không sẽ trầy mặt khi đóng nắp hộp"}])
    [profile] = propose_reasons([draft()], llm)
    assert profile.reason == "vì nếu không sẽ trầy mặt khi đóng nắp hộp"
    assert (profile.reason_source, profile.status) == ("expert_verbal", "in_review")
    validate_against_contract(profile)


def test_ac_08_no_transcript_means_no_call_and_no_reason() -> None:
    llm = FakeLLM([{"reason": "để tránh trầy"}])
    [profile] = propose_reasons([draft(transcript=None)], llm)
    assert profile.reason is None and profile.status == "draft" and llm.calls == []


def test_ac_09_a_paraphrase_not_in_the_transcript_is_dropped() -> None:
    llm = FakeLLM([{"reason": "Để bảo vệ bề mặt sản phẩm và đảm bảo chất lượng thẩm mỹ"}])
    [profile] = propose_reasons([draft()], llm)
    assert profile.reason is None and profile.reason_source is None
    assert profile.status == "draft"


def test_the_expert_giving_no_reason_leaves_the_draft_alone() -> None:
    [profile] = propose_reasons([draft()], FakeLLM([{"reason": None}]))
    assert profile.reason is None and profile.status == "draft"
