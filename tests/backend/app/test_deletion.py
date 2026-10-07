"""spec 08 §2 "Xoá dữ liệu", AC-19..AC-22 — deleting steps and whole videos.

No Neo4j, no PostgreSQL: the real ``KnowledgeGraphLoader`` runs on a fake graph that only tracks
``Step`` nodes and on an in-memory vector store; the profile store is SQLite in ``tmp_path``.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from mentormind.backend.app.deps import get_knowledge_loader, get_loader_opener, get_profile_store
from mentormind.backend.app.main import app
from mentormind.backend.app.routers import videos as videos_router
from mentormind.core.config import Settings
from mentormind.core.schemas import Evidence, WorkProfile
from mentormind.knowledge_base.kg.loader import KnowledgeGraphLoader
from mentormind.knowledge_base.store.profile_store import ProfileStore
from mentormind.knowledge_base.store.vector_store import MemoryVectorStore

VIDEO_A, VIDEO_B = "VID-aaaaaaaaaaaa", "VID-bbbbbbbbbbbb"
APPROVE = {"action": "approve", "reviewer": "expert_01"}


class StepGraph:
    """The ``Step`` nodes a Neo4j would hold after the loader's queries."""

    def __init__(self) -> None:
        self.steps: set[str] = set()

    def run(self, query: str, **params: Any) -> list[dict[str, Any]]:
        if "MERGE (s:Step" in query:
            self.steps.add(params["profile_id"])
        if "DETACH DELETE s" in query:
            self.steps.discard(params["profile_id"])
        return []


class FakeKnowledge:
    """Neo4j + pgvector behind ``get_loader_opener``; ``down`` makes opening them fail."""

    def __init__(self) -> None:
        self.graph = StepGraph()
        self.vectors = MemoryVectorStore()
        self.down = False
        self.opened = 0

    def loader(self) -> KnowledgeGraphLoader:
        return KnowledgeGraphLoader(self.graph, self.vectors)

    @contextmanager
    def open(self) -> Iterator[KnowledgeGraphLoader]:
        self.opened += 1
        if self.down:
            raise RuntimeError("Neo4j không phản hồi")
        yield self.loader()

    def chunk_of(self, profile_id: str) -> bool:
        return bool(self.vectors.search("", k=1, filters={"source_type": "work_profile", "ref_id": profile_id}))


def step(number: int, video_id: str = VIDEO_A) -> WorkProfile:
    return WorkProfile(
        schema_version="1.0",
        profile_id=f"WP-PACK01-{number:03d}",
        process_id="PACK01",
        step_order=number,
        step=f"Lấy linh kiện bước {number}",
        hand_action="Cầm linh kiện",
        evidence=Evidence(video_id=video_id, t_start=number, t_end=number + 1),
        confidence=0.9,
        generated_by="vlm",
        data_classification="synthetic",
        status="draft",
        created_at="2026-10-08T00:00:00Z",
    )


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(_env_file=None, work_dir=tmp_path / "work")


@pytest.fixture
def store(tmp_path: Path) -> ProfileStore:
    store = ProfileStore(db_path=tmp_path / "profiles.sqlite")
    for number in (1, 2, 3):
        store.save_profile(step(number))
    store.save_profile(step(4, VIDEO_B))
    return store


@pytest.fixture
def kg() -> FakeKnowledge:
    return FakeKnowledge()


@pytest.fixture
def client(
    store: ProfileStore, kg: FakeKnowledge, settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> Iterator[TestClient]:
    monkeypatch.setattr(videos_router, "get_settings", lambda: settings)
    app.dependency_overrides[get_profile_store] = lambda: store
    app.dependency_overrides[get_knowledge_loader] = kg.loader
    app.dependency_overrides[get_loader_opener] = lambda: kg.open
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _approve(client: TestClient, kg: FakeKnowledge, profile_id: str) -> None:
    assert client.post(f"/profiles/{profile_id}/review", json=APPROVE).status_code == 200
    assert profile_id in kg.graph.steps and kg.chunk_of(profile_id)


def _ids(client: TestClient) -> set[str]:
    return {p["profile_id"] for p in client.get("/profiles").json()}


def test_ac_19_deleting_a_draft_never_opens_the_graph(
    client: TestClient, store: ProfileStore, kg: FakeKnowledge
) -> None:
    kg.down = True  # Neo4j and pgvector are off: a draft is still deleted
    res = client.delete("/profiles/WP-PACK01-001")
    assert res.status_code == 200, res.text
    assert res.json() == {"deleted": ["WP-PACK01-001"], "unpublished": [], "failed": []}
    assert client.get("/profiles/WP-PACK01-001").status_code == 404
    assert "WP-PACK01-001" not in _ids(client) and kg.opened == 0


def test_ac_19_a_rejected_step_goes_with_its_review_history(
    client: TestClient, store: ProfileStore, kg: FakeKnowledge
) -> None:
    reject = {"action": "reject", "reviewer": "expert_01", "comment": "bịa bước"}
    assert client.post("/profiles/WP-PACK01-002/review", json=reject).status_code == 200
    kg.opened = 0
    assert client.delete("/profiles/WP-PACK01-002").status_code == 200
    assert store.get_profile("WP-PACK01-002") is None and store.last_review_action("WP-PACK01-002") is None
    assert kg.opened == 0


def test_ac_19_unknown_step_is_404(client: TestClient) -> None:
    res = client.delete("/profiles/WP-PACK01-999")
    assert res.status_code == 404 and "WP-PACK01-999" in res.json()["detail"]


def test_ac_20_an_approved_step_leaves_the_graph_and_the_vector_store(client: TestClient, kg: FakeKnowledge) -> None:
    _approve(client, kg, "WP-PACK01-001")
    res = client.delete("/profiles/WP-PACK01-001")
    assert res.status_code == 200, res.text
    assert res.json()["unpublished"] == ["WP-PACK01-001"] and res.json()["deleted"] == ["WP-PACK01-001"]
    assert kg.graph.steps == set() and not kg.chunk_of("WP-PACK01-001")
    assert client.get("/profiles/WP-PACK01-001").status_code == 404


def test_ac_20_an_edited_approved_step_is_still_in_the_graph_and_leaves_it(
    client: TestClient, kg: FakeKnowledge
) -> None:
    _approve(client, kg, "WP-PACK01-001")
    edited = client.patch("/profiles/WP-PACK01-001", json={"step": "Lấy linh kiện từ khay"}).json()
    assert edited["status"] == "in_review" and "WP-PACK01-001" in kg.graph.steps  # AC-01
    assert client.delete("/profiles/WP-PACK01-001").json()["unpublished"] == ["WP-PACK01-001"]
    assert kg.graph.steps == set() and not kg.chunk_of("WP-PACK01-001")


def test_ac_20_graph_down_keeps_the_approved_step_and_says_why(
    client: TestClient, store: ProfileStore, kg: FakeKnowledge
) -> None:
    _approve(client, kg, "WP-PACK01-001")
    kg.down = True
    res = client.delete("/profiles/WP-PACK01-001")
    assert res.status_code == 503
    assert "Neo4j không phản hồi" in res.json()["detail"] and "giữ nguyên" in res.json()["detail"]
    kept = store.get_profile("WP-PACK01-001")
    assert kept is not None and kept.status == "approved"
    assert kg.graph.steps == {"WP-PACK01-001"} and kg.chunk_of("WP-PACK01-001")


def test_ac_21_several_steps_are_deleted_together(client: TestClient, kg: FakeKnowledge) -> None:
    _approve(client, kg, "WP-PACK01-002")
    ids = ["WP-PACK01-001", "WP-PACK01-002", "WP-PACK01-003", "WP-PACK01-001"]  # a repeat counts once
    res = client.post("/profiles/delete", json={"profile_ids": ids})
    assert res.status_code == 200, res.text
    assert res.json() == {
        "deleted": ["WP-PACK01-001", "WP-PACK01-002", "WP-PACK01-003"],
        "unpublished": ["WP-PACK01-002"],
        "failed": [],
    }
    assert _ids(client) == {"WP-PACK01-004"} and kg.graph.steps == set()


def test_ac_21_an_unknown_id_deletes_nothing(client: TestClient) -> None:
    res = client.post("/profiles/delete", json={"profile_ids": ["WP-PACK01-001", "WP-NOPE-001"]})
    assert res.status_code == 404 and "WP-NOPE-001" in res.json()["detail"]
    assert "WP-PACK01-001" in _ids(client)
    assert client.post("/profiles/delete", json={"profile_ids": []}).status_code == 422


def test_ac_21_graph_down_still_deletes_drafts_and_reports_the_rest(
    client: TestClient, store: ProfileStore, kg: FakeKnowledge
) -> None:
    _approve(client, kg, "WP-PACK01-002")
    kg.down = True
    res = client.post("/profiles/delete", json={"profile_ids": ["WP-PACK01-001", "WP-PACK01-002"]})
    assert res.status_code == 200, res.text
    body = res.json()
    assert (body["deleted"], body["unpublished"]) == (["WP-PACK01-001"], [])
    [failure] = body["failed"]
    assert failure["profile_id"] == "WP-PACK01-002" and "Neo4j không phản hồi" in failure["error"]
    assert store.get_profile("WP-PACK01-001") is None and store.get_profile("WP-PACK01-002") is not None


def _video_files(settings: Settings, video_id: str) -> list[Path]:
    folder = settings.work_dir / "video" / video_id
    files = [
        folder / "source.mp4",
        folder / "video.json",
        folder / "segments.json",
        folder / "transcript.json",
        folder / "keyframes" / f"{video_id}-S001_k1.jpg",
        folder / "clips" / f"{video_id}-S001.mp4",
        settings.work_dir / "vlm" / video_id / "describe-fake" / "pass_a.json",
    ]
    for path in files:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"x")
    return files


def test_ac_22_a_video_goes_with_its_steps_and_files(client: TestClient, settings: Settings, kg: FakeKnowledge) -> None:
    files_a, files_b = _video_files(settings, VIDEO_A), _video_files(settings, VIDEO_B)
    _approve(client, kg, "WP-PACK01-002")
    res = client.delete(f"/videos/{VIDEO_A}")
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["video_id"] == VIDEO_A and body["files_removed"] == len(files_a)
    assert sorted(body["deleted"]) == ["WP-PACK01-001", "WP-PACK01-002", "WP-PACK01-003"]
    assert (body["unpublished"], body["failed"]) == (["WP-PACK01-002"], [])
    assert not (settings.work_dir / "video" / VIDEO_A).exists() and not (settings.work_dir / "vlm" / VIDEO_A).exists()
    assert kg.graph.steps == set()
    assert _ids(client) == {"WP-PACK01-004"} and all(f.exists() for f in files_b)  # the other video stays


def test_ac_22_unknown_video_is_404(client: TestClient, settings: Settings) -> None:
    assert client.delete("/videos/VID-cccccccccccc").status_code == 404
    assert client.delete("/videos/a.b").status_code == 404  # not a plain folder name
    _video_files(settings, "VID-dddddddddddd")  # files without steps can still be deleted
    assert client.delete("/videos/VID-dddddddddddd").json()["files_removed"] == 7


def test_ac_22_files_stay_while_an_approved_step_cannot_be_unloaded(
    client: TestClient, settings: Settings, store: ProfileStore, kg: FakeKnowledge
) -> None:
    files = _video_files(settings, VIDEO_A)
    _approve(client, kg, "WP-PACK01-002")
    kg.down = True
    res = client.delete(f"/videos/{VIDEO_A}")
    assert res.status_code == 200, res.text
    body = res.json()
    assert sorted(body["deleted"]) == ["WP-PACK01-001", "WP-PACK01-003"] and body["files_removed"] == 0
    assert [f["profile_id"] for f in body["failed"]] == ["WP-PACK01-002"]
    assert all(f.exists() for f in files) and store.get_profile("WP-PACK01-002") is not None
