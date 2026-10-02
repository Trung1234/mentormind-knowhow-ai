"""Sigma (MES) records as spec 07 §2 defines them, shared by the adapter and the RCA agent.

``LotNotFound`` is raised by ``SigmaAdapter.get_lot`` for an unknown lot (spec 07 FR-02); the RCA
agent lets it through so the API answers 404 (spec 06 §4, spec 08 AC-06).
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel


class LotNotFound(LookupError):
    """No lot with this id in Sigma."""

    def __init__(self, lot_id: str) -> None:
        super().__init__(f"Không tìm thấy lot {lot_id!r} trong Sigma.")
        self.lot_id = lot_id


class LotRecord(BaseModel):
    lot_id: str
    product_code: str
    process_id: str
    date: date
    shift: Literal["A", "B", "C"]
    operator_id: str
    qty: int


class DefectRecord(BaseModel):
    defect_id: str
    lot_id: str
    process_id: str
    #: Maps to ``Symptom.symptom_id`` in the graph (spec 05).
    defect_code: str
    description: str
    qty: int
    detected_at: datetime


class DefectCatalogEntry(BaseModel):
    defect_code: str
    symptom_name: str
    known_root_cause_id: str | None
    known_root_cause: str | None
    prevention_profile_id: str | None
