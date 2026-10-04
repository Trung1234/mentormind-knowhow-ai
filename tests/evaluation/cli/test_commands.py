"""spec 09 — ``knowhow eval ragas | review-stats | report``."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from mentormind.agents import factory
from mentormind.core.cli import app
from mentormind.core.schemas import DataClassification
from mentormind.evaluation.golden import load_golden
from mentormind.evaluation.ragas import LlmJudge, run_golden
from tests.evaluation.fakes import ScriptedJudge
from tests.evaluation.ragas.test_runner import FIXTURE, assistant

runner = CliRunner()


def test_report_is_written_from_a_ragas_run(tmp_path: Path) -> None:
    run_golden(
        load_golden(FIXTURE),
        assistant(),
        LlmJudge(ScriptedJudge()),
        out_dir=tmp_path,
        classification=DataClassification.SYNTHETIC,
        golden_path=FIXTURE,
    )
    result = runner.invoke(app, ["eval", "report", "--run", str(tmp_path)])
    assert result.exit_code == 0, result.output
    report = (tmp_path / "usefulness_report.md").read_text(encoding="utf-8")
    assert "| faithfulness | 0.75 | 0.85 | ❌ |" in report


def test_ragas_stops_when_the_assistant_cannot_be_wired(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def missing(settings: object) -> None:
        raise factory.AgentWiringError("Thiếu thư viện của spec 05 (neo4j): uv sync --extra kg.")

    monkeypatch.setattr(factory, "build_work_assistant", missing)
    result = runner.invoke(app, ["eval", "ragas", "--golden", str(FIXTURE), "--out", str(tmp_path)])
    assert result.exit_code == 1 and "spec 05" in result.output


def test_a_broken_golden_set_stops_before_anything_runs(tmp_path: Path) -> None:
    bad = tmp_path / "qa.jsonl"
    bad.write_text('{"qid": "Q001"}\n', encoding="utf-8")
    result = runner.invoke(app, ["eval", "ragas", "--golden", str(bad), "--out", str(tmp_path)])
    assert result.exit_code == 1 and "dòng 1" in result.output


def test_review_stats_needs_the_store(tmp_path: Path) -> None:
    result = runner.invoke(app, ["eval", "review-stats", "--db", str(tmp_path / "none.sqlite")])
    assert result.exit_code == 1 and "spec 08" in result.output


@pytest.fixture(autouse=True)
def _isolated_cwd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
