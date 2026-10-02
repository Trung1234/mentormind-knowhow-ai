"""Graph publication and evidence based retrieval without a database service."""

import os
import uuid
from contextlib import contextmanager
from typing import cast

import pytest

from mentormind.core.config import Settings
from mentormind.core.providers.errors import InvalidJSONError
from mentormind.core.schemas import Evidence, ReviewInfo, WorkProfile
from mentormind.core.schemas.vector import VectorChunk
from mentormind.knowledge_base.kg.client import Neo4jGraph
from mentormind.knowledge_base.kg.loader import KnowledgeGraphLoader
from mentormind.knowledge_base.retrieval.hybrid import (
    TEMPLATES,
    HybridRetriever,
    Template,
    get_hybrid_retriever,
)
from mentormind.knowledge_base.sigma.adapter import CsvSigmaAdapter
from mentormind.knowledge_base.store.vector_store import MemoryVectorStore


class RecordingGraph:
    def __init__(self):
        self.calls = []
        self.version = None
        self.rows = {}

    def run(self, query, **params):
        self.calls.append((query, params))
        if "RETURN s.version AS version" in query:
            return [] if self.version is None else [{"version": self.version}]
        for key, rows in self.rows.items():
            if key in query:
                return rows
        return []


def profile(number=1, status="approved", version=1):
    return WorkProfile(
        schema_version="1.0",
        profile_id=f"WP-PACK01-{number:03d}", process_id="PACK01", step_order=number,
        step=f"Kiểm tra linh kiện bước {number}", hand_action="Cầm linh kiện",
        reason="Tránh trầy" if status == "approved" else None,
        reason_source="expert_verbal" if status == "approved" else None,
        evidence=Evidence(video_id="VID-1", t_start=2, t_end=4, segment_ids=["VID-1#s1"]),
        confidence=0.9, generated_by="human", data_classification="synthetic", status=status,
        review=ReviewInfo(reviewer="EXP-1", reviewed_at="2026-09-28T00:00:00Z") if status == "approved" else None,
        created_at="2026-09-28T00:00:00Z", version=version,
    )


def test_loader_publishes_only_approved_and_explicit_segment_ids():
    graph, vectors = RecordingGraph(), MemoryVectorStore()
    loader = KnowledgeGraphLoader(graph, vectors)
    result = loader.load_profiles([profile(), profile(2, "draft"), profile(3, "rejected")])
    assert result.loaded == 1 and result.skipped == 2
    assert [h.chunk.ref_id for h in vectors.search("Kiểm tra", filters={"source_type": "work_profile"})] == [
        "WP-PACK01-001"
    ]
    assert any("EVIDENCED_BY" in q and p.get("segment_ids") == ["VID-1#s1"] for q, p in graph.calls)
    assert any("EVIDENCED_BY" in q and "r.profile_t_start" in q and "v.t_start" not in q
               for q, _ in graph.calls)
    assert any("NEXT" in q for q, _ in graph.calls)


def test_stale_version_cannot_replace_published_profile():
    graph, vectors = RecordingGraph(), MemoryVectorStore()
    graph.version = 3
    result = KnowledgeGraphLoader(graph, vectors).load_profiles([profile(version=2)])
    assert result.stale == 1
    assert vectors.search("Kiểm tra") == []


def test_failed_vector_write_rolls_back_graph_publication():
    class TransactionalGraph(RecordingGraph):
        def __init__(self):
            super().__init__()
            self.steps = set()

        @contextmanager
        def transaction(self):
            before = self.steps.copy()
            try:
                yield
            except Exception:
                self.steps = before
                raise

        def run(self, query, **params):
            if "MERGE (s:Step" in query:
                self.steps.add(params["profile_id"])
            return super().run(query, **params)

    class FailingVectors(MemoryVectorStore):
        def upsert(self, chunks):
            raise RuntimeError("vector unavailable")

    graph = TransactionalGraph()
    with pytest.raises(RuntimeError, match="vector unavailable"):
        KnowledgeGraphLoader(graph, FailingVectors()).load_profiles([profile()])
    assert graph.steps == set()


def test_failed_graph_commit_removes_new_vector_chunk():
    class CommitFailGraph(RecordingGraph):
        @contextmanager
        def transaction(self):
            yield
            raise RuntimeError("commit failed")

    vectors = MemoryVectorStore()
    with pytest.raises(RuntimeError, match="commit failed"):
        KnowledgeGraphLoader(CommitFailGraph(), vectors).load_profiles([profile()])
    assert vectors.search("Kiểm tra") == []


def test_unload_removes_only_step_and_its_chunk():
    graph, vectors = RecordingGraph(), MemoryVectorStore()
    loader = KnowledgeGraphLoader(graph, vectors)
    loader.load_profiles([profile()])
    loader.unload_profile("WP-PACK01-001")
    assert vectors.search("Kiểm tra") == []
    assert any("DETACH DELETE s" in q for q, _ in graph.calls)
    assert not any("DELETE p" in q for q, _ in graph.calls)


def test_retrieval_keeps_passage_and_citation_together_and_filters_process():
    graph, vectors = RecordingGraph(), MemoryVectorStore()
    KnowledgeGraphLoader(graph, vectors).load_profiles([profile()])
    graph.rows["MATCH (s:Step {profile_id: $profile_id})"] = [
        {"fact": "Bước 1 dùng linh kiện A123", "source_type": "work_profile", "ref_id": "WP-PACK01-001"}
    ]
    result = HybridRetriever(vectors, graph).retrieve("linh kiện", process_id="PACK01")
    assert result.passages and result.graph_facts
    assert len(result.passages) == len(result.citations) == len(result.classifications)
    assert any(c.ref_id == "WP-PACK01-001" for c in result.citations)
    assert HybridRetriever(vectors, graph).retrieve("linh kiện", process_id="PACK02").passages == []


def test_bad_router_output_falls_back_to_vector():
    graph, vectors = RecordingGraph(), MemoryVectorStore()
    KnowledgeGraphLoader(graph, vectors).load_profiles([profile()])

    class BadRouter:
        def generate_json(self, *args, **kwargs):
            return {"template": "MATCH (n) DETACH DELETE n"}

    result = HybridRetriever(vectors, graph, router=BadRouter()).retrieve("Kiểm tra")
    assert result.passages and all("DETACH DELETE n" not in q for q, _ in graph.calls)

    class InvalidJsonRouter:
        def generate_json(self, *args, **kwargs):
            raise InvalidJSONError("invalid", raw_text="not json")

    assert HybridRetriever(vectors, graph, router=InvalidJsonRouter()).retrieve("Kiểm tra").passages


def test_two_document_chunks_keep_distinct_passages_and_citations():
    vectors = MemoryVectorStore()
    vectors.upsert([
        VectorChunk(chunk_id="DOC-1#1", source_type="document", ref_id="DOC-1",
                    text="Kiểm tra góc vát", data_classification="synthetic"),
        VectorChunk(chunk_id="DOC-1#2", source_type="document", ref_id="DOC-1",
                    text="Kiểm tra bề mặt", data_classification="synthetic"),
    ])
    context = HybridRetriever(vectors, RecordingGraph()).retrieve("Kiểm tra", k=2)
    assert len(context.passages) == len(context.citations) == 2
    assert set(context.passages) == {"Kiểm tra góc vát", "Kiểm tra bề mặt"}


def test_accentless_symptom_lookup_and_template_is_parameterized():
    graph, vectors = RecordingGraph(), MemoryVectorStore()
    graph.rows["MATCH (s:Symptom) RETURN"] = [{"symptom_id": "D-01", "name": "Thiếu linh kiện trong hộp"}]
    graph.rows["HAS_DEFECT"] = [{"fact": "Lô LOT-1 có lỗi thiếu linh kiện", "source_type": "sigma", "ref_id": "LOT-1"}]

    class Router:
        def generate_json(self, *args, **kwargs):
            return {"template": "where_symptom_occurred", "symptom_text": "thieu linh kien"}

    result = HybridRetriever(vectors, graph, router=Router()).retrieve("thieu linh kien")
    assert any("LOT-1" in fact for fact in result.graph_facts)
    assert any(p.get("symptom_id") == "D-01" for _, p in graph.calls)


def test_root_cause_citation_identifies_catalog_row():
    assert "defect_catalog.csv#" in TEMPLATES["root_causes_of_symptom"]


def test_sigma_csv_loads_lot_defect_and_prevention_without_unapproved_step(tmp_path):
    (tmp_path / "lots.csv").write_text(
        "lot_id,product_code,process_id,date,shift,operator_id,qty\n"
        "LOT-1,P1,PACK01,2026-09-28,A,O1,10\n", encoding="utf-8",
    )
    (tmp_path / "defects.csv").write_text(
        "defect_id,lot_id,process_id,defect_code,description,qty,detected_at\n"
        "DEF-1,LOT-1,PACK01,D-01,Thiếu linh kiện,2,2026-09-28T08:00:00\n", encoding="utf-8",
    )
    (tmp_path / "defect_catalog.csv").write_text(
        "defect_code,symptom_name,known_root_cause_id,known_root_cause,prevention_profile_id\n"
        "D-01,Thiếu linh kiện,RC-01,Bỏ sót,WP-PACK01-005\n", encoding="utf-8",
    )
    graph = RecordingGraph()
    assert KnowledgeGraphLoader(graph, MemoryVectorStore()).load_sigma(CsvSigmaAdapter(tmp_path)) == 1
    assert any("HAS_DEFECT" in q and p.get("symptom_id") == "D-01" for q, p in graph.calls)
    assert any("PREVENTED_BY" in q and p.get("profile_id") == "WP-PACK01-005" for q, p in graph.calls)


def test_committed_sigma_fixture_is_case_and_time_linkable():
    from pathlib import Path

    adapter = CsvSigmaAdapter(Path(__file__).resolve().parents[2] / "data" / "mock_sigma")
    lots = {lot.lot_id: lot for lot in adapter.list_lots()}
    codes = {item.defect_code for item in adapter.defect_catalog()}
    defects = adapter.list_defects()
    assert len(lots) == 6 and len(codes) == 6 and len(defects) == 6
    for defect in defects:
        lot = lots[defect.lot_id]
        assert defect.defect_code in codes
        assert defect.process_id == lot.process_id
        assert defect.detected_at.date() == lot.date
        assert 6 <= defect.detected_at.hour < 14


def test_retriever_factory_needs_no_cloud_key_for_offline_retrieval():
    settings = Settings(_env_file=None, vector_backend="memory", llm_provider="qwen_api",
                        llm_api_key=None)
    retriever = get_hybrid_retriever(settings)
    assert retriever.router is None
    retriever.graph.close()


@pytest.mark.integration
def test_neo4j_profile_lifecycle_and_all_six_templates(tmp_path):
    uri = os.getenv("KNOWHOW_TEST_NEO4J_URI")
    if not uri:
        pytest.skip("Set KNOWHOW_TEST_NEO4J_URI to run against a disposable Neo4j 5 instance")
    token = "IT" + uuid.uuid4().hex[:8].upper()
    settings = Settings(_env_file=None, neo4j_uri=uri,
                        neo4j_password=os.getenv("KNOWHOW_TEST_NEO4J_PASSWORD", "change-me"))
    graph = Neo4jGraph(settings)
    try:
        graph.init()
        vectors = MemoryVectorStore()
        loader = KnowledgeGraphLoader(graph, vectors)
        profiles = [
            profile(i).model_copy(update={"profile_id": f"WP-{token}-{i:03d}",
                                          "process_id": token,
                                          "part_numbers": [f"{token}-PART"] if i == 2 else [],
                                          "evidence": Evidence(video_id=f"{token}-VID", t_start=i,
                                                               t_end=i + 1,
                                                               segment_ids=[f"{token}-VID#s{i}"])})
            for i in (1, 2, 3)
        ]
        other = [profile(i, status).model_copy(update={"profile_id": f"WP-{token}-{i:03d}",
                                                "process_id": token})
                 for i, status in ((4, "draft"), (5, "rejected"))]
        result = loader.load_profiles(profiles + other)
        assert (result.loaded, result.skipped) == (3, 2)
        assert loader.stats()["Step"] >= 3
        assert loader.load_profiles(profiles).loaded == 3
        assert len(graph.run("MATCH (p:Process {process_id: $pid})-[:HAS_STEP]->(s:Step) "
                             "RETURN s.profile_id AS id", pid=token)) == 3
        edges = graph.run("MATCH (a:Step)-[:NEXT]->(b:Step) "
                          "WHERE a.profile_id STARTS WITH $prefix "
                          "RETURN a.step_order AS a, b.step_order AS b", prefix=f"WP-{token}")
        assert [(row["a"], row["b"]) for row in edges] == [(1, 2), (2, 3)]

        (tmp_path / "lots.csv").write_text(
            "lot_id,product_code,process_id,date,shift,operator_id,qty\n"
            f"{token}-LOT,P1,{token},2026-09-28,A,O1,10\n", encoding="utf-8")
        (tmp_path / "defects.csv").write_text(
            "defect_id,lot_id,process_id,defect_code,description,qty,detected_at\n"
            f"{token}-DEF,{token}-LOT,{token},{token}-D01,Lỗi,1,2026-09-28T08:00:00\n",
            encoding="utf-8")
        (tmp_path / "defect_catalog.csv").write_text(
            "defect_code,symptom_name,known_root_cause_id,known_root_cause,prevention_profile_id\n"
            f"{token}-D01,Thiếu linh kiện,{token}-RC,Bỏ sót,WP-{token}-002\n", encoding="utf-8")
        loader.load_sigma(CsvSigmaAdapter(tmp_path))
        retriever = HybridRetriever(vectors, graph)
        expected = {
            "steps_of_process": (dict(process_id=token), "WP-"),
            "steps_using_part": (dict(part_number=f"{token}-PART", process_id=token), "WP-"),
            "where_symptom_occurred": (dict(symptom_id=f"{token}-D01", process_id=token), "-LOT"),
            "root_causes_of_symptom": (dict(symptom_id=f"{token}-D01", process_id=token), "Bỏ sót"),
            "prevention_steps": (dict(symptom_id=f"{token}-D01", process_id=token), "WP-"),
            "lots_with_defect": (dict(symptom_id=f"{token}-D01", process_id=token,
                                      date_from="2026-09-28", date_to="2026-09-28"), "-LOT"),
        }
        for name, (params, fragment) in expected.items():
            rows = retriever.run_template(cast(Template, name), **params)
            assert rows and any(fragment in row["fact"] or fragment in row["ref_id"] for row in rows)

        loader.unload_profile(f"WP-{token}-002")
        assert retriever.run_template("steps_using_part", part_number=f"{token}-PART") == []
        assert graph.run("MATCH (p:Part {part_number: $number}) RETURN p.part_number AS number",
                         number=f"{token}-PART")
    finally:
        for label, key in (
            ("Process", "process_id"), ("Step", "profile_id"), ("Exception", "exception_id"),
            ("Part", "part_number"), ("VideoSegment", "segment_id"), ("Symptom", "symptom_id"),
            ("RootCause", "cause_id"), ("Lot", "lot_id"),
        ):
            graph.run(f"MATCH (n:{label}) WHERE n.{key} CONTAINS $token DETACH DELETE n", token=token)
        graph.close()
