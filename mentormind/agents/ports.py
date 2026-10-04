"""What the agents need from spec 05 (retrieval, graph) and spec 07 (Sigma), as Protocols.

The agents only depend on these shapes; the real ``HybridRetriever`` (spec 05) and
``CsvSigmaAdapter`` (spec 07) satisfy them structurally, and tests hand in fakes.
"""

from __future__ import annotations

from typing import Any, Protocol

from mentormind.core.providers.llm import strictest
from mentormind.core.schemas import DataClassification
from mentormind.knowledge_base.retrieval.hybrid import RetrievedContext, Template
from mentormind.knowledge_base.sigma.adapter import DefectRecord, LotRecord


class Retriever(Protocol):
    """spec 05 §4 ``HybridRetriever.retrieve``."""

    def retrieve(self, query: str, process_id: str | None = None, k: int = 8) -> RetrievedContext: ...


class GraphTemplates(Protocol):
    """spec 05 §4 Cypher templates, called by name (never free Cypher).

    Every row has ``fact``, ``source_type``, ``ref_id`` and ``data_classification`` (one label or
    the labels of every node the fact is built from). ``ref_id`` is the lot id for
    ``where_symptom_occurred`` and the ``profile_id`` for ``prevention_steps``.
    """

    def run_template(self, template: Template, **params: Any) -> list[dict[str, Any]]: ...

    def match_symptom(self, text: str) -> str | None:
        """``symptom_id`` for free text (spec 05 §4 symptom matching), ``None`` if nothing fits."""
        ...


class ExpertDirectory(Protocol):
    def top_contributor(self, process_id: str) -> str | None:
        """``display_name`` of the expert with the most ``CONTRIBUTED`` steps in the process."""
        ...


class SigmaSource(Protocol):
    """The part of spec 07 ``SigmaAdapter`` the RCA agent reads."""

    def get_lot(self, lot_id: str) -> LotRecord:
        """Raises ``LotNotFound`` for an unknown lot."""
        ...

    def get_defects(self, lot_id: str) -> list[DefectRecord]: ...


def passage_label(context: RetrievedContext, index: int) -> DataClassification:
    """Label of ``context.passages[index]``; a missing label is factory data (fail closed)."""
    if index < len(context.classifications):
        return context.classifications[index]
    return DataClassification.FACTORY_CONFIDENTIAL


def row_label(row: dict[str, Any]) -> DataClassification:
    """Strictest label of a graph row; a missing label is factory data (fail closed)."""
    value = row.get("data_classification")
    labels = value if isinstance(value, list) else [value]
    return strictest(
        DataClassification(label) if label else DataClassification.FACTORY_CONFIDENTIAL for label in labels or [None]
    )
