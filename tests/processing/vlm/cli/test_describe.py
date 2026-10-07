"""spec 04 FR-05 — ``knowhow vlm describe`` and ``knowhow vlm propose-reasons``."""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

import pytest
from typer.testing import CliRunner

from mentormind.core.config import get_settings
from mentormind.core.providers.llm.backends.fake import FakeLLM
from mentormind.core.schemas.common import DataClassification
from mentormind.processing.vlm.cli import app
from mentormind.processing.vlm.cli import describe as describe_cli
from mentormind.processing.vlm.pipeline import read_profiles, write_profiles
from tests.processing.vlm.passes.test_describe import segments
from tests.processing.vlm.passes.test_reasons import TRANSCRIPT, draft

runner = CliRunner()


@pytest.fixture(autouse=True)
def _hermetic(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.chdir(tmp_path)
    for name, value in {
        "KNOWHOW_VLM_PROVIDER": "fake",
        "KNOWHOW_LLM_PROVIDER": "fake",
        "KNOWHOW_GUARD_AUDIT_DIR": str(tmp_path / "audit"),
        "KNOWHOW_PROFILE_SINK": "file",
        "DASHSCOPE_API_KEY": "sk-test",
    }.items():
        monkeypatch.setenv(name, value)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def write_segments(tmp_path: Path, label: DataClassification) -> Path:
    path = tmp_path / "segments.json"
    rows = [s.model_copy(update={"data_classification": label}) for s in segments(2)]
    path.write_text(json.dumps([s.model_dump(mode="json") for s in rows]), encoding="utf-8")
    return path


def test_exactly_one_input_is_required() -> None:
    result = runner.invoke(app, ["describe"])
    assert result.exit_code == 1 and "đúng một nguồn" in result.output


def test_a_video_id_without_segments_points_to_video_option() -> None:
    result = runner.invoke(app, ["describe", "VID-NOPE"])
    assert result.exit_code == 1
    assert "segments.json" in result.output and "--video" in result.output


def test_factory_data_with_a_cloud_llm_is_refused_before_any_vlm_call(tmp_path: Path) -> None:
    path = write_segments(tmp_path, DataClassification.FACTORY_CONFIDENTIAL)
    result = runner.invoke(app, ["describe", "--segments", str(path), "--llm-provider", "qwen_api"])
    assert result.exit_code == 1
    assert "KNOWHOW_LLM_PROVIDER=local_openai" in result.output
    assert not (tmp_path / "data" / "work" / "vlm").exists()  # nothing sampled, nothing sent


def test_propose_reasons_needs_a_described_video() -> None:
    result = runner.invoke(app, ["propose-reasons", "VID-NOPE"])
    assert result.exit_code == 1 and "describe" in result.output


def test_propose_reasons_without_transcript_changes_nothing(tmp_path: Path) -> None:
    store = tmp_path / "data" / "work" / "vlm" / "VID-TEST" / "profiles.json"
    write_profiles([draft(transcript=None)], store)
    result = runner.invoke(app, ["propose-reasons", "VID-TEST"])
    assert result.exit_code == 0 and "spec 03" in result.output


def test_ac_27_propose_reasons_writes_its_audit_next_to_the_video_profiles(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    folder = tmp_path / "data" / "work" / "vlm" / "VID-TEST"
    write_profiles([draft()], folder / "profiles.json")
    llm = FakeLLM([{"has_reason": True, "purpose_span": "vì nếu không sẽ trầy mặt"}])
    monkeypatch.setattr(describe_cli, "_llm", lambda settings: llm)
    result = runner.invoke(app, ["propose-reasons", "VID-TEST"])
    assert result.exit_code == 0, result.output
    assert "reasons_audit.jsonl" in result.output
    [profile] = read_profiles(folder / "profiles.json")
    assert (profile.reason, profile.status) == (TRANSCRIPT, "in_review")
    [line] = (folder / "reasons_audit.jsonl").read_text(encoding="utf-8").splitlines()
    assert json.loads(line)["decision"] == "accepted"
