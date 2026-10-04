"""spec 09 §5b — ``KNOWHOW_EVAL_JUDGE`` picks the judge; both score the same answers alike."""

from __future__ import annotations

import pytest

from mentormind.core.config import Settings
from mentormind.core.schemas import DataClassification
from mentormind.evaluation.ragas import JUDGES, JudgeConfigError, JudgeSample, build_judge
from mentormind.evaluation.ragas.judges import factory
from tests.evaluation.fakes import SameVectorEmbedder, ScriptedJudge

SAMPLE = JudgeSample("Vì sao đặt nghiêng?", "Để tránh trầy [1].", ["Đặt nghiêng tránh trầy."], "Tránh trầy bề mặt.")


@pytest.mark.parametrize("name", sorted(JUDGES))
def test_each_judge_gives_the_same_scores_for_the_same_judge_answers(name: str) -> None:
    judge = build_judge(name, ScriptedJudge(), SameVectorEmbedder())
    assert judge.kind == name
    [scores] = judge.score([SAMPLE], DataClassification.SYNTHETIC)
    assert scores == {"faithfulness": 0.75, "answer_relevancy": 1.0, "context_precision": 1.0, "context_recall": 1.0}


def test_the_ragas_package_is_the_default_judge() -> None:
    assert Settings(_env_file=None).eval_judge == "ragas"


def test_an_unknown_judge_is_refused() -> None:
    with pytest.raises(JudgeConfigError, match="ragas, builtin"):
        build_judge("gpt", ScriptedJudge(), SameVectorEmbedder())


def test_the_ragas_judge_without_the_eval_extra_says_how_to_fix_it(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(factory, "find_spec", lambda name: None)
    with pytest.raises(JudgeConfigError, match="--extra eval"):
        build_judge("ragas", ScriptedJudge(), SameVectorEmbedder())
