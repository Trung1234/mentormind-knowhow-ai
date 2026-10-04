"""``knowhow eval ragas`` (spec 09 FR-01, FR-02)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from mentormind.core.config import Settings
from mentormind.core.schemas.common import DataClassification

EVAL_DIR = Path("data/work/eval")


def ragas_cmd(
    golden: Annotated[Path, typer.Option(exists=True, dir_okay=False, help="qa.jsonl.")] = Path(
        "data/golden_set/qa.jsonl"
    ),
    out: Annotated[Path, typer.Option(help="Thư mục kết quả.")] = EVAL_DIR,
    classification: Annotated[
        DataClassification,
        typer.Option(help="Nhãn dữ liệu đưa cho judge; mặc định coi là dữ liệu nhà máy."),
    ] = DataClassification.FACTORY_CONFIDENTIAL,
) -> None:
    from mentormind.agents.adapters.factory import AgentWiringError, build_work_assistant
    from mentormind.core.config import get_settings
    from mentormind.core.guard import ConfidentialDataError
    from mentormind.core.providers.errors import ProviderError
    from mentormind.core.providers.llm import get_llm_provider
    from mentormind.evaluation.golden import GoldenSetError, check_distribution, load_golden
    from mentormind.evaluation.ragas import JudgeConfigError, build_judge, run_golden
    from mentormind.knowledge_base.store.embedding import BgeM3Embedder
    from mentormind.knowledge_base.store.vector_store import VectorStoreError

    settings = get_settings()
    try:
        questions = load_golden(golden)
        for missing in check_distribution(questions):
            typer.secho(f"Cảnh báo golden set: {missing}", fg=typer.colors.YELLOW, err=True)
        assistant = build_work_assistant(settings)
        judge_llm = get_llm_provider(_judge_settings(settings))
        judge = build_judge(settings.eval_judge, judge_llm, BgeM3Embedder(settings.embed_model))
        summary = run_golden(
            questions,
            assistant,
            judge,
            out_dir=out,
            classification=classification,
            golden_path=golden,
            assistant_llm=f"{assistant.llm.name}:{assistant.llm.model}",
        )
    except (
        GoldenSetError,
        AgentWiringError,
        JudgeConfigError,
        ProviderError,
        ConfidentialDataError,
        VectorStoreError,
    ) as exc:
        typer.secho(f"Lỗi: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1) from exc
    typer.echo(json.dumps(summary.metrics, ensure_ascii=False, indent=2))
    typer.echo(f"Kết quả: {out}/ragas_results.csv, {out}/summary.json")


def _judge_settings(settings: Settings) -> Settings:
    """``KNOWHOW_EVAL_LLM_*`` override the agent's ``KNOWHOW_LLM_*`` for the judge (FR-02)."""
    update = {
        "llm_provider": settings.eval_llm_provider or settings.llm_provider,
        "llm_base_url": settings.eval_llm_base_url or settings.llm_base_url,
        "llm_model": settings.eval_llm_model or settings.llm_model,
    }
    return settings.model_copy(update=update)
