"""``propose-reasons`` — a reason only from the expert's own words (spec 04 §5, T04-7).

For each profile whose evidence carries a ``transcript_excerpt`` (what the expert said during
that step), a text LLM is asked to COPY the sentence where the expert says why. The answer is then
checked against the transcript: ``rapidfuzz.fuzz.partial_ratio(reason, excerpt) >= 85`` on
lowercased text. Anything below that is the LLM paraphrasing or inventing: it is dropped and the
profile is left as it was. This closes the indirect route around constitution art. 3.

A kept reason sets ``reason_source="expert_verbal"`` and moves the profile to ``in_review``.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import Any

from pydantic import ValidationError
from rapidfuzz import fuzz

from mentormind.core.providers.errors import InvalidJSONError
from mentormind.core.providers.llm import LLMProvider
from mentormind.core.providers.parsing import parse_json_object
from mentormind.core.schemas.work_profile import WorkProfile, validate_against_contract
from mentormind.processing.vlm.passes.prompting import render_prompt

log = logging.getLogger(__name__)

QUOTE_THRESHOLD = 85.0
REASON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"reason": {"type": ["string", "null"]}},
    "required": ["reason"],
}


def is_quoted(reason: str, transcript: str, threshold: float = QUOTE_THRESHOLD) -> bool:
    """True when ``reason`` is (nearly) verbatim inside ``transcript``."""
    return fuzz.partial_ratio(reason.lower().strip(), transcript.lower()) >= threshold


def propose_reasons(profiles: Sequence[WorkProfile], llm: LLMProvider) -> list[WorkProfile]:
    """Profiles with a verbatim expert reason filled in; the others unchanged (AC-08, AC-09)."""
    return [_propose(profile, llm) for profile in profiles]


def _propose(profile: WorkProfile, llm: LLMProvider) -> WorkProfile:
    transcript = profile.evidence.transcript_excerpt if profile.evidence else None
    if not transcript or profile.reason is not None:
        return profile
    prompt = render_prompt(
        "propose_reason.md",
        process_id=profile.process_id,
        step=profile.step,
        key_point=profile.key_point or "không có",
        transcript=transcript,
    )
    response = llm.generate(
        prompt,
        classification=profile.data_classification,
        json_schema=REASON_SCHEMA,
        temperature=0.0,
    )
    try:
        reason = parse_json_object(response.text).get("reason")
    except InvalidJSONError:
        log.info("propose-reasons: unreadable answer for %s", profile.profile_id)
        return profile
    if not isinstance(reason, str) or not reason.strip():
        return profile
    if not is_quoted(reason, transcript):
        log.info(
            "propose-reasons: %s — %r is not in the transcript (paraphrase), dropped",
            profile.profile_id,
            reason,
        )
        return profile
    data = profile.model_dump()
    data.update(reason=reason.strip(), reason_source="expert_verbal", status="in_review")
    try:
        updated = WorkProfile.model_validate(data)
        validate_against_contract(updated)
    except (ValidationError, ValueError) as exc:
        log.warning("propose-reasons: %s rejected by the contract: %s", profile.profile_id, exc)
        return profile
    return updated
