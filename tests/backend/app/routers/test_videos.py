"""spec 08 §2, AC-13..AC-15 — video upload + processing, and the Sigma lots behind the RCA page.

No ffmpeg, no VLM server: clips are small synthetic videos (``tests.processing.vlm.video_fakes``),
the VLM/LLM are the scripted fakes of the pipeline tests. ``TestClient`` runs the background job
before ``post`` returns, so the job is finished when it is read back.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from mentormind.agents.adapters.factory import _sigma
from mentormind.backend.app.deps import get_profile_store
from mentormind.backend.app.main import app
from mentormind.backend.app.routers import sigma as sigma_router
from mentormind.backend.app.routers import videos as videos_router
from mentormind.core.config import Settings
from mentormind.core.providers import llm as llm_providers
from mentormind.core.providers import vlm as vlm_providers
from mentormind.core.providers.llm.backends.fake import FakeLLM
from mentormind.core.providers.vlm.backends.fake import FakeVLM
from mentormind.core.schemas import VideoAsset
from mentormind.knowledge_base.sigma.adapter import CsvSigmaAdapter
from mentormind.knowledge_base.store.profile_store import ProfileStore
from tests.processing.vlm.test_pipeline import RUN_1, RUN_2
from tests.processing.vlm.video_fakes import fake_ffmpeg, synthetic_video

MERGE = {
    "steps": [
        {"step": "Nhặt cốc từ khay", "source_ids": ["s1"]},
        {"step": "Đặt cốc vào thùng carton", "source_ids": ["s2", "s3"]},
    ]
}


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        _env_file=None,
        work_dir=tmp_path / "work",
        profile_db=tmp_path / "profiles.sqlite",
        profile_sink="store",
        guard_audit_dir=tmp_path / "audit",
    )


@pytest.fixture
def store(settings: Settings) -> ProfileStore:
    return ProfileStore(db_path=str(settings.profile_db))


@pytest.fixture
def client(settings: Settings, store: ProfileStore, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    fake_ffmpeg(monkeypatch)
    monkeypatch.setattr(videos_router, "get_settings", lambda: settings)
    monkeypatch.setattr(vlm_providers, "get_vlm_provider", lambda s=None: FakeVLM([*RUN_1, *RUN_2]))
    monkeypatch.setattr(llm_providers, "get_llm_provider", lambda s=None: FakeLLM([MERGE]))
    app.dependency_overrides[get_profile_store] = lambda: store
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _upload(client: TestClient, video: Path, *, classification: str | None = "synthetic", name: str = "") -> Any:
    data = {"process_id": "PACK01"} | ({} if classification is None else {"classification": classification})
    files = {"file": (name or video.name, video.read_bytes(), "video/mp4")}
    return client.post("/videos", files=files, data=data)


def test_ac_13_upload_keeps_the_video_under_its_content_id(
    client: TestClient, settings: Settings, tmp_path: Path
) -> None:
    video = synthetic_video(tmp_path / "pack.mp4", 20)
    res = _upload(client, video)
    assert res.status_code == 200, res.text
    asset = VideoAsset.model_validate(res.json())
    assert asset.video_id == "VID-" + hashlib.sha256(video.read_bytes()).hexdigest()[:12]
    assert (asset.process_id, asset.data_classification, asset.duration_s) == ("PACK01", "synthetic", 20.0)
    folder = settings.work_dir / "video" / asset.video_id
    assert (folder / "source.mp4").read_bytes() == video.read_bytes()
    assert VideoAsset.model_validate_json((folder / "video.json").read_text(encoding="utf-8")) == asset


@pytest.mark.parametrize(
    ("classification", "name"), [(None, "pack.mp4"), ("secret", "pack.mp4"), ("synthetic", "notes.txt")]
)
def test_ac_13_no_label_or_no_video_is_refused_and_nothing_is_kept(
    client: TestClient, settings: Settings, tmp_path: Path, classification: str | None, name: str
) -> None:
    res = _upload(client, synthetic_video(tmp_path / "pack.mp4", 4), classification=classification, name=name)
    assert res.status_code == 422
    videos = settings.work_dir / "video"
    assert not videos.exists() or not list(videos.glob("VID-*"))


def test_ac_14_processing_saves_drafts_segments_and_progress(
    client: TestClient, settings: Settings, tmp_path: Path
) -> None:
    video_id = _upload(client, synthetic_video(tmp_path / "pack.mp4", 20)).json()["video_id"]
    job_id = client.post(f"/videos/{video_id}/process", json={}).json()["job_id"]
    job = client.get(f"/jobs/{job_id}").json()
    assert job["status"] == "done", job
    result = job["result"]
    assert (result["video_id"], result["segments"]) == (video_id, 2)
    assert result["progress"] == {"done": 4, "total": 4}  # passes A and B, one call per segment each
    drafts = {p["profile_id"]: p for p in client.get("/profiles", params={"process_id": "PACK01"}).json()}
    assert result["profiles"] and set(result["profiles"]) <= set(drafts)
    for profile_id in result["profiles"]:
        profile = drafts[profile_id]
        assert profile["status"] == "draft" and profile["reason"] is None
        assert profile["evidence"]["video_id"] == video_id and profile["evidence"]["keyframes"]
    segments = client.get(f"/videos/{video_id}/segments").json()
    assert [s["segment_id"] for s in segments] == [f"{video_id}-S001", f"{video_id}-S002"]
    assert all(len(s["keyframes"]) == 3 for s in segments)


def test_ac_14_unknown_video_or_method_is_refused(client: TestClient, tmp_path: Path) -> None:
    assert client.post("/videos/VID-000000000000/process", json={}).status_code == 404
    assert client.post("/videos/..%2F..%2Fetc/process", json={}).status_code == 404
    assert client.get("/videos/VID-000000000000/segments").status_code == 404
    video_id = _upload(client, synthetic_video(tmp_path / "pack.mp4", 4)).json()["video_id"]
    res = client.post(f"/videos/{video_id}/process", json={"method": "scene"})
    assert res.status_code == 422 and "spec 03" in res.json()["detail"]


def test_ac_14_a_failing_pipeline_ends_the_job_failed(
    client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def broken(settings: Any = None) -> FakeVLM:
        raise RuntimeError("VLM server không phản hồi")

    monkeypatch.setattr(vlm_providers, "get_vlm_provider", broken)
    video_id = _upload(client, synthetic_video(tmp_path / "pack.mp4", 4)).json()["video_id"]
    job = client.get(f"/jobs/{client.post(f'/videos/{video_id}/process', json={}).json()['job_id']}").json()
    assert job["status"] == "failed" and "không phản hồi" in job["error"]
    assert client.get("/health").status_code == 200  # the server keeps serving


def test_ac_15_the_lots_are_the_sigma_adapters_and_rca_finds_each(client: TestClient) -> None:
    lots = client.get("/sigma/lots").json()
    expected = CsvSigmaAdapter(Settings(_env_file=None).sigma_csv_dir).list_lots()
    assert [lot["lot_id"] for lot in lots] == [lot.lot_id for lot in expected]
    flagged = {d.lot_id for d in CsvSigmaAdapter(Settings(_env_file=None).sigma_csv_dir).list_defects()}
    assert {lot["lot_id"] for lot in lots if lot["status"] == "NG"} == flagged
    live_sigma = _sigma(Settings(_env_file=None))  # what the live RCA Agent reads
    for lot in lots:
        assert live_sigma.get_lot(lot["lot_id"]).lot_id == lot["lot_id"]
        assert client.post("/rca/investigate", json={"lot_id": lot["lot_id"]}).status_code == 200  # mock mode


def test_ac_15_lots_filter_by_process(client: TestClient) -> None:
    assert client.get("/sigma/lots", params={"process_id": "NOPE"}).json() == []
    assert {lot["process_id"] for lot in client.get("/sigma/lots", params={"process_id": "PACK01"}).json()} == {
        "PACK01"
    }


def test_sigma_lots_need_the_csv_adapter(monkeypatch: pytest.MonkeyPatch, client: TestClient) -> None:
    monkeypatch.setattr(sigma_router, "get_settings", lambda: Settings(_env_file=None, sigma_adapter="sigma_api"))
    res = client.get("/sigma/lots")
    assert res.status_code == 503 and "spec 07" in json.dumps(res.json(), ensure_ascii=False)


def test_ac_17_a_job_left_running_by_a_restart_ends_failed(client: TestClient, store: ProfileStore) -> None:
    from mentormind.backend.app.routers import jobs as jobs_router
    from mentormind.core.schemas import JobStatus

    store.create_job("job-vid-before", "video_process")
    store.update_job("job-vid-before", JobStatus.RUNNING, result={"progress": {"done": 3, "total": 40}})
    with sqlite3.connect(store.db_path) as conn:  # created by the previous API process
        conn.execute("UPDATE jobs SET created_at = ? WHERE job_id = ?", ("2000-01-01T00:00:00+00:00", "job-vid-before"))
    store.create_job("job-vid-now", "video_process")
    store.update_job("job-vid-now", JobStatus.RUNNING)
    assert jobs_router.STARTED_AT > "2000-01-01"

    stale = client.get("/jobs/job-vid-before").json()
    assert stale["status"] == "failed" and "khởi động lại" in stale["error"]
    assert stale["result"] == {"progress": {"done": 3, "total": 40}}  # what it got done is kept
    assert client.get("/jobs/job-vid-now").json()["status"] == "running"
