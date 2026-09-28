
from fastapi import APIRouter, Query

from mentormind.core.schemas import LotRecord

router = APIRouter(prefix="/sigma", tags=["sigma"])

# Mock lots from sample data for Demo & Testing
SAMPLE_LOTS: list[LotRecord] = [
    LotRecord(
        lot_id="LOT-2026-001",
        process_id="PACK01",
        part_number="DN-BOX-440",
        produced_at="2026-09-25T08:30:00Z",
        defect_type="Rách mép carton",
        status="NG",
    ),
    LotRecord(
        lot_id="LOT-2026-002",
        process_id="PACK01",
        part_number="DN-BOX-440",
        produced_at="2026-09-26T09:15:00Z",
        defect_type="Nắp hộp lệch mép >2mm",
        status="NG",
    ),
    LotRecord(
        lot_id="LOT-2026-003",
        process_id="PACK01",
        part_number="DN-BOX-550",
        produced_at="2026-09-27T14:00:00Z",
        defect_type=None,
        status="OK",
    ),
]


@router.get("/lots", response_model=list[LotRecord])
def get_lots(
    process_id: str | None = Query(default=None, description="Mã công đoạn"),
) -> list[LotRecord]:
    if process_id:
        return [lot for lot in SAMPLE_LOTS if lot.process_id == process_id]
    return SAMPLE_LOTS
