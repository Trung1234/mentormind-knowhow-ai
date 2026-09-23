# 09 — Evaluation (Usefulness Report)

**Owner:** Đạt (golden set, khung đo, báo cáo) · Phúc (chạy Ragas, code) · **Tasks Excel:** S1-9, S2-7, S2-8, S3-2

## 1. Mục tiêu
Sinh tự động số liệu cho Deliverable #4 từ 3 nguồn: chất lượng trích xuất của VLM, chất lượng trả lời của agent, và (sau 12/10) hiệu quả nghiệp vụ.

## 2. Golden set — `data/golden_set/qa.jsonl`
Mỗi dòng:
```json
{"qid": "Q001", "process_id": "PACK01", "type": "how|why|exception|relational|out_of_scope",
 "question": "Vì sao phải đặt linh kiện A nghiêng?",
 "ground_truth": "Để tránh trầy bề mặt khi đóng nắp.",
 "expected_citations": ["WP-PACK01-003"],
 "author": "Đạt", "created_at": "2026-09-30"}
```
`expected_citations` là danh sách `Citation.ref_id` (spec 05) thuộc bất kỳ `source_type` nào: `WP-...` (profile), `DOC-...#...` (chunk tài liệu), `VID-...-Sxxx` (segment), `lot_id`/`defect_code` (sigma). Câu `relational` nên có citation sigma hoặc document.

Phân bố tối thiểu 30 câu: how 10, why 6, exception 5, relational 5, out_of_scope 4 (câu mà trợ lý **phải từ chối**).

Nhãn bước chuẩn cho fps sweep: `data/golden_set/steps/<video_stem>.json` (xem spec 04 mục 6).

## 3. Ba nhóm chỉ số

**A. Trích xuất VLM** (từ `review_events`, spec 08)
- Tỷ lệ profile approve không cần sửa / approve sau khi sửa / reject.
- Phân bố `error_tags` (bỏ sót, bịa, sai thứ tự...).
- Kết quả fps sweep (spec 04): recall, precision, order_accuracy theo fps.

**B. Chất lượng trả lời** (Ragas trên golden set, bỏ nhóm `out_of_scope`)
| Chỉ số | Ngưỡng MVP |
|---|---|
| faithfulness | ≥ 0.85 |
| answer_relevancy | ≥ 0.80 |
| context_precision | ≥ 0.70 |
| context_recall | ≥ 0.70 |
Thêm hai chỉ số tự tính:
- `refusal_accuracy`: tỷ lệ câu `out_of_scope` bị từ chối đúng + tỷ lệ câu trong phạm vi **không** bị từ chối.
- `citation_hit_rate`: tỷ lệ câu có ít nhất 1 citation nằm trong `expected_citations`.

**C. Nghiệp vụ** (khung cho giai đoạn pilot, ngoài phạm vi 12/10)
- Thời gian thợ mới hoàn thành công đoạn lần đầu, tỷ lệ lỗi D-01..D-06, thời gian điều tra 1 lot lỗi — so với baseline.
- Báo cáo 12/10 chỉ trình bày thiết kế thí nghiệm A/B, không bịa số.

## 4. Functional Requirements
- **FR-01** `knowhow eval ragas --golden data/golden_set/qa.jsonl --out data/work/eval/` chạy Work Assistant trên từng câu, tính nhóm B, xuất `ragas_results.csv` (1 dòng/câu) và `summary.json`.
- **FR-02** Judge LLM cho Ragas lấy từ `get_llm_provider` (config riêng `KNOWHOW_EVAL_LLM_*` được phép khác model của agent). Khuyến nghị: test/CI dùng FakeLLM (AC-02); benchmark cho báo cáo 12/10 dùng judge mạnh (VD GPT-4o-mini hoặc Qwen2.5-72B qua API) vì model ~8B chấm Ragas không ổn định. Được phép vì golden set 12/10 chỉ gồm dữ liệu `public`/`synthetic`; DataGuard vẫn chặn nếu có `factory_confidential`.
- **FR-03** `knowhow eval review-stats` tính nhóm A từ profile store.
- **FR-04** `knowhow eval report` gộp A + B (+ sweep CSV nếu có) thành `data/work/eval/usefulness_report.md`: bảng chỉ số, so ngưỡng (đạt/không đạt), 5 câu trả lời tệ nhất kèm lý do, bảng "Profile cần xem lại" (các `profile_id` trong citation thực tế và `expected_citations` của những câu dưới ngưỡng, kèm `process_id` và số câu liên quan — đầu vào cho vòng lặp sửa profile ở spec 08), phần "Hạn chế" và "Thiết kế thí nghiệm pilot" (nhóm C).
- **FR-05** Mọi lần chạy ghi `run_id`, thời điểm, model, commit hash vào `summary.json` để so sánh giữa các lần.

## 5. Acceptance Criteria
- **AC-01** `qa.jsonl` sai schema (thiếu `ground_truth`) → báo lỗi dòng cụ thể, không chạy.
- **AC-02** Với FakeLLM + golden set fixture 5 câu → `ragas_results.csv` có 4 dòng (1 câu out_of_scope tách riêng), `summary.json` có đủ 4 chỉ số Ragas + 2 chỉ số tự tính.
- **AC-03** `refusal_accuracy` tính đúng trên fixture cố định (kết quả kỳ vọng ghi trong test).
- **AC-04** `review-stats` trên fixture 10 review event ra đúng tỷ lệ và phân bố error_tags.
- **AC-05** `report` sinh markdown có bảng chỉ số với cột "Đạt ngưỡng" = ✅/❌ đúng theo ngưỡng mục 3.
- **AC-06** Fixture có 2 câu dưới ngưỡng cùng trích `WP-PACK01-003` → bảng "Profile cần xem lại" có dòng `WP-PACK01-003` với số câu = 2.

## 6. Tasks
- [ ] T09-1 Schema golden set + validator (AC-01) — Đạt viết nội dung, Phúc viết validator.
- [ ] T09-2 Runner Ragas + chỉ số tự tính (AC-02, AC-03).
- [ ] T09-3 `review-stats` (AC-04).
- [ ] T09-4 `report` (AC-05, AC-06).

## Changelog
- v1.0 (23/9): khởi tạo.
- v1.1 (23/9): làm rõ `expected_citations` nhận mọi `ref_id`; khuyến nghị judge LLM; FR-04 thêm bảng "Profile cần xem lại" (AC-06).
