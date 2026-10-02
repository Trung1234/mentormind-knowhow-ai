"""What the agents need from spec 05 (retrieval, graph) and spec 07 (Sigma), as Protocols.

The agents only depend on these shapes; the real ``HybridRetriever``, graph client and
``SigmaAdapter`` satisfy them structurally (no import, no inheritance), and tests hand in fakes.
"""

from __future__ import annotations

from typing import Any, Protocol

from mentormind.core.schemas import DefectRecord, LotRecord, RetrievedContext


class Retriever(Protocol):
    """spec 05 §4 ``HybridRetriever``.

    ``route=False`` skips the LLM router of relational intents: the RCA agent calls graph
    templates by name itself and must not trigger the router (spec 06 AC-08).
    """

    def retrieve(
        self, query: str, process_id: str | None = None, k: int = 8, *, route: bool = True
    ) -> RetrievedContext: ...


class GraphTemplates(Protocol):
    """spec 05 §4 Cypher templates, called by name (never free Cypher)."""

    def run(self, template: str, **params: Any) -> list[dict[str, Any]]:
        """Rows of ``template``. Row keys used by the RCA agent:

        * ``root_causes_of_symptom(symptom_id)`` -> ``cause_id``, ``description``, ``confidence``
        * ``where_symptom_occurred(symptom_id)`` -> ``lot_id``, ``process_id``
        * ``prevention_steps(symptom_id)`` -> ``profile_id``, ``step``
        """
        ...

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
