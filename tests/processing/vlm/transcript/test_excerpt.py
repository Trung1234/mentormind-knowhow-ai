"""spec 04 §3 — a step's ``transcript_excerpt`` from spec 03's transcript and alignment (assumed)."""

from __future__ import annotations

import pytest

from mentormind.processing.vlm.transcript import align, excerpt_for
from tests.processing.vlm.passes.test_describe import segments
from tests.processing.vlm.transcript.fakes import install_spec03, line

SAID = [line("rồi đóng nắp.", 12, 14), line("Đặt nghiêng để không trầy,", 3, 5)]


def test_without_spec_03_there_is_no_excerpt_and_no_error() -> None:
    assert align(segments(2), SAID) is None
    assert excerpt_for(["VID-TEST-S001"], None) is None


def test_without_a_transcript_there_is_no_excerpt(monkeypatch: pytest.MonkeyPatch) -> None:
    install_spec03(monkeypatch)
    assert align(segments(2), []) is None


def test_the_excerpt_of_a_merged_step_joins_its_segments_in_time_order(monkeypatch: pytest.MonkeyPatch) -> None:
    install_spec03(monkeypatch)
    aligned = align(segments(2), SAID)
    assert excerpt_for(["VID-TEST-S002", "VID-TEST-S001"], aligned) == "Đặt nghiêng để không trầy, rồi đóng nắp."
    assert excerpt_for(["VID-TEST-S003"], aligned) is None  # the expert said nothing there
