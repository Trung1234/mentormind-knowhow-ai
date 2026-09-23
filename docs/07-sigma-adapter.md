# 07 — Sigma Adapter (MES) & Mock Data

**Owner:** Vinh · **Tasks Excel:** S1-7

## 1. Mục tiêu
Tách logic nghiệp vụ khỏi hệ thống Sigma thật (chưa rõ API). MVP chạy trên CSV mock; khi có Sigma thật chỉ cần viết thêm một adapter.

## 2. Interface — `knowhow.sigma.adapter`
```python
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
    defect_code: str        # map sang Symptom.symptom_id
    description: str
    qty: int
    detected_at: datetime

class DefectCatalogEntry(BaseModel):
    defect_code: str
    symptom_name: str
    known_root_cause_id: str | None
    known_root_cause: str | None
    prevention_profile_id: str | None

class SigmaAdapter(Protocol):
    def get_lot(self, lot_id: str) -> LotRecord: ...              # raise LotNotFound
    def list_lots(self, process_id: str | None = None,
                  date_from: date | None = None, date_to: date | None = None) -> list[LotRecord]: ...
    def get_defects(self, lot_id: str) -> list[DefectRecord]: ...
    def list_defects(self, defect_code: str | None = None) -> list[DefectRecord]: ...
    def defect_catalog(self) -> list[DefectCatalogEntry]: ...
```
Factory `get_sigma_adapter(settings)` theo `KNOWHOW_SIGMA_ADAPTER` ∈ {`csv`} (sau này thêm `api`, `db`).

## 3. Mock data — `data/mock_sigma/` (commit vào repo, `data_classification=synthetic`)
| File | Cột | Quy mô |
|---|---|---|
| `lots.csv` | lot_id, product_code, process_id, date, shift, operator_id, qty | 50 lot, 20/9–10/10/2026, process `PACK01`, `PACK02` |
| `defects.csv` | defect_id, lot_id, process_id, defect_code, description, qty, detected_at | ~15 dòng |
| `defect_catalog.csv` | defect_code, symptom_name, known_root_cause_id, known_root_cause, prevention_profile_id | 6 mã |

Danh mục lỗi gợi ý (Đạt duyệt lại cho sát công đoạn đóng hộp):
| defect_code | symptom_name | known_root_cause |
|---|---|---|
| D-01 | Thiếu linh kiện trong hộp | Bỏ sót bước đếm cuối trước khi đóng nắp |
| D-02 | Sai vị trí ngăn | Nhầm hướng khay chia ngăn |
| D-03 | Trầy bề mặt linh kiện | Đặt linh kiện nằm ngang thay vì nghiêng |
| D-04 | Móp góc hộp | Ấn nắp khi linh kiện chưa vào hết ngăn |
| D-05 | Sai nhãn lô | Dán nhãn trước khi kiểm đếm |
| D-06 | Lẫn linh kiện khác mã | Để khay linh kiện khác mã chung bàn |

Script `scripts/gen_mock_sigma.py` sinh dữ liệu với seed cố định (42) để kết quả test ổn định.

## 4. Functional Requirements
- **FR-01** `CsvSigmaAdapter` đọc 3 file bằng pandas, validate từng dòng bằng Pydantic; dòng lỗi → log + bỏ qua, không crash.
- **FR-02** `get_lot` không tìm thấy → `LotNotFound(lot_id)`.
- **FR-03** CLI: `knowhow sigma lots [--process PACK01]`, `knowhow sigma defects --lot <id>`, `knowhow sigma gen-mock`.
- **FR-04** Adapter chỉ đọc (read-only). Không có hàm ghi.

## 5. Acceptance Criteria
- **AC-01** `gen-mock` với seed 42 chạy 2 lần → file giống hệt nhau (so hash).
- **AC-02** `list_lots(process_id="PACK01")` chỉ trả lot của PACK01.
- **AC-03** `get_lot("KHONG-TON-TAI")` raise `LotNotFound`.
- **AC-04** CSV có 1 dòng sai định dạng ngày → dòng đó bị bỏ qua, các dòng khác vẫn đọc được, có log cảnh báo.
- **AC-05** Mọi `defect_code` trong `defects.csv` đều có trong `defect_catalog.csv`.

## 6. Tasks
- [ ] T07-1 Models + Protocol + `LotNotFound`.
- [ ] T07-2 `gen_mock_sigma.py` (AC-01, AC-05).
- [ ] T07-3 `CsvSigmaAdapter` (AC-02..04) + CLI.

## Changelog
- v1.0 (23/9): khởi tạo.
