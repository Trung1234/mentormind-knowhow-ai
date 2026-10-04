"""spec 04 T04-3 — pass A: valid drafts (AC-01), no reason (AC-02), repair + failures (AC-06)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from PIL import Image

from mentormind.core.guard import SupportsCloudFlag
from mentormind.core.providers.vlm.backends.fake import FakeVLM
from mentormind.core.schemas.common import DataClassification
from mentormind.core.schemas.video import Segment
from mentormind.core.schemas.work_profile import validate_against_contract
from mentormind.processing.vlm.frames import SampledFrames
from mentormind.processing.vlm.passes import describe_segments, to_work_profiles


def segments(n: int = 3) -> list[Segment]:
    return [
        Segment(
            segment_id=f"VID-TEST-S{i:03d}",
            video_id="VID-TEST",
            index=i,
            t_start=10.0 * (i - 1),
            t_end=10.0 * i,
            method="fixed_window",
            motion_score=None,
            keyframes=[f"kf_{i}.jpg"],
            clip_path=f"clip_{i}.mp4",
            data_classification=DataClassification.SYNTHETIC,
        )
        for i in range(1, n + 1)
    ]


def fake_sampler(
    segment: Segment,
    destination: SupportsCloudFlag,
    *,
    out_dir: Path,
    default_fps: float,
    max_frames: int,
) -> SampledFrames:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for i in range(3):
        path = out_dir / f"f{i}.jpg"
        Image.new("RGB", (32, 18), (i * 60, 90, 120)).save(path)
        paths.append(path)
    return SampledFrames(paths=paths, timestamps=[0.0, 1.0, 2.0], fps=default_fps)


def step(name: str, start: float, end: float, **extra: Any) -> dict[str, Any]:
    return {
        "step": name,
        "hand_action": "tay phải",
        "objects": ["cốc"],
        "key_point_observed": None,
        "t_start_rel": start,
        "t_end_rel": end,
        "confidence": 0.8,
        **extra,
    }


def run(vlm: FakeVLM, tmp_path: Path) -> Any:
    return describe_segments(
        segments(),
        vlm,
        process_id="PACK01",
        work_dir=tmp_path,
        default_fps=4.0,
        max_frames=48,
        sampler=fake_sampler,
    )


def test_ac_01_three_segments_become_valid_drafts_numbered_from_one(tmp_path: Path) -> None:
    vlm = FakeVLM(
        [
            {"steps": [step("Nhặt cốc", 0, 2), step("Đặt cốc vào thùng", 2, 5)]},
            {"steps": [step("Đậy nắp đỏ", 1, 4)]},
            {"steps": [step("Dồn cốc thành hàng", 0, 3)]},
        ]
    )
    result = run(vlm, tmp_path)
    profiles = to_work_profiles(result, segments=segments(), process_id="PACK01", provider=vlm, model=vlm.model)
    assert [p.step_order for p in profiles] == [1, 2, 3, 4]
    assert profiles[0].profile_id == "WP-PACK01-001"
    for profile in profiles:
        validate_against_contract(profile)
        assert (profile.status, profile.generated_by) == ("draft", "vlm")
    second = profiles[2]
    assert (second.evidence.t_start, second.evidence.t_end) == (11.0, 14.0)
    assert second.evidence.segment_ids == ["VID-TEST-S002"]
    assert second.model_info is not None and second.model_info.fps == 4.0
    assert (tmp_path / "pass_a" / "VID-TEST-S001.json").is_file()  # FR-06 raw answer kept


def test_ac_02_reason_from_the_model_is_dropped(tmp_path: Path) -> None:
    sneaky = step("Đặt cốc vào thùng", 0, 3, reason="để tránh trầy", reason_source="expert_verbal")
    vlm = FakeVLM([{"steps": [sneaky]}])
    result = run(vlm, tmp_path)
    profiles = to_work_profiles(result, segments=segments(), process_id="PACK01", provider=vlm, model=vlm.model)
    assert profiles and all(p.reason is None and p.reason_source is None for p in profiles)


def test_ac_06_twice_invalid_json_is_logged_and_others_continue(tmp_path: Path) -> None:
    ok = {"steps": [step("Nhặt cốc", 0, 2)]}
    vlm = FakeVLM([ok, "xin lỗi, tôi không chắc", '{"steps": [{"step": 1}]}', ok])
    result = run(vlm, tmp_path)
    assert [s.segment_id for s in result.steps] == ["VID-TEST-S001", "VID-TEST-S003"]
    failed = json.loads((tmp_path / "failed_segments.json").read_text())
    assert [f["segment_id"] for f in failed] == ["VID-TEST-S002"]
    assert "LƯU Ý" in vlm.calls[2].prompt  # the retry used the repair prompt
    assert len(vlm.calls) == 4


def test_repair_prompt_recovers_a_segment(tmp_path: Path) -> None:
    ok = {"steps": [step("Nhặt cốc", 0, 2)]}
    vlm = FakeVLM([ok, "không phải JSON", ok, ok])
    result = run(vlm, tmp_path)
    assert len(result.steps) == 3 and result.failed == []
    assert not (tmp_path / "failed_segments.json").exists()


def test_relative_times_are_clamped_to_the_segment(tmp_path: Path) -> None:
    vlm = FakeVLM([{"steps": [step("Nhặt cốc", 8, 25)]}])
    result = run(vlm, tmp_path)
    assert (result.steps[0].t_start, result.steps[0].t_end) == (8.0, 10.0)


@pytest.fixture(autouse=True)
def _isolated_cwd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)


def test_objects_given_as_one_string_become_a_list(tmp_path: Path) -> None:
    """DashScope's json_object mode returned "objects": "linh kiện, hộp" on the LASI video."""
    vlm = FakeVLM([{"steps": [step("Đặt linh kiện vào hộp", 0, 2, objects="linh kiện, hộp")]}])
    result = run(vlm, tmp_path)
    assert result.failed == [] and result.steps[0].objects == ["linh kiện", "hộp"]


@pytest.mark.parametrize(
    ("said", "actor"),
    [
        ("human", "human"),
        ("robot", "robot"),
        ("machine", "machine"),
        ("công nhân", "human"),
        ("kỹ sư", "human"),
        ("worker", "human"),
        ("robot SCARA", "robot"),
        ("máy dựng thùng", "machine"),
        ("không rõ", None),
        (None, None),
    ],
)
def test_ac_18_pass_a_reads_who_performs_the_step(said: str | None, actor: str | None, tmp_path: Path) -> None:
    vlm = FakeVLM([{"steps": [step("Đặt cốc vào thùng", 0, 2, actor=said)]}])
    result = run(vlm, tmp_path)
    assert result.failed == [] and result.steps[0].actor == actor
    profiles = to_work_profiles(result, segments=segments(), process_id="PACK01", provider=vlm, model=vlm.model)
    for profile in profiles:  # the fake repeats its answer for each of the 3 segments
        assert profile.actor == actor
        validate_against_contract(profile)


def test_ac_18_pass_a_asks_for_the_actor() -> None:
    from mentormind.processing.vlm.passes.describe import PASS_A_SCHEMA
    from mentormind.processing.vlm.passes.prompting import render_prompt

    item = PASS_A_SCHEMA["properties"]["steps"]["items"]
    assert item["properties"]["actor"]["enum"] == ["human", "robot", "machine", None]
    assert "actor" in item["required"]
    prompt = render_prompt("pass_a_describe.md", process_id="PACK01", duration="10.0", fps="4", timestamps="0.0")
    assert '"actor"' in prompt and "human" in prompt and "robot" in prompt


def test_ac_20_an_english_answer_is_asked_again_in_vietnamese(tmp_path: Path) -> None:
    # LASI sweep 2026-10-04: the Q4 model on Ollama answered 63-83% of the step names in English.
    english = {"scene": "x", "steps": [step("Pick product", 0, 1, hand_action="right hand picks it")]}
    vietnamese = {"scene": "x", "steps": [step("Nhặt sản phẩm", 0, 1)]}
    vlm = FakeVLM([english, vietnamese, {"steps": []}, {"steps": []}])
    result = run(vlm, tmp_path)
    assert [s.step for s in result.steps] == ["Nhặt sản phẩm"]
    assert "tiếng Việt" in vlm.calls[1].prompt and "steps[0].step" in vlm.calls[1].prompt
    assert len(vlm.calls) == 4  # one repair, for the first segment only


def test_ac_20_an_english_answer_is_kept_when_the_repair_fails(tmp_path: Path) -> None:
    english = {"scene": "x", "steps": [step("Pick product", 0, 1)]}
    vlm = FakeVLM([english, "không phải JSON", {"steps": []}, {"steps": []}])
    result = run(vlm, tmp_path)
    assert [s.step for s in result.steps] == ["Pick product"] and result.failed == []


def test_ac_20_pass_a_asks_for_vietnamese() -> None:
    from mentormind.processing.vlm.passes.prompting import render_prompt

    prompt = render_prompt("pass_a_describe.md", process_id="PACK01", duration="10.0", fps="4", timestamps="0.0")
    assert "TIẾNG VIỆT" in prompt
