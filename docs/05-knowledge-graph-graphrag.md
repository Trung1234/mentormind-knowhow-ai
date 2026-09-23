# 05 — Knowledge Graph & GraphRAG

**Owner:** Trung · **Tasks Excel:** S0-2, S1-5, S1-6, S2-3

## 1. Mục tiêu
Lưu tri thức đã duyệt dưới dạng đồ thị (quan hệ công đoạn – bước – linh kiện – lỗi – nguyên nhân – lô hàng) và cung cấp một retriever lai vector + graph để agent (spec 06) trả lời được cả câu hỏi mô tả lẫn câu hỏi quan hệ.

## 2. Graph schema (Neo4j 5)

**Nodes** (khóa duy nhất in đậm)
| Label | Thuộc tính |
|---|---|
| `Process` | **process_id**, name |
| `Step` | **profile_id**, step, step_order, hand_action, key_point, reason, reason_source, pass_criteria, confidence, version |
| `Exception` | **exception_id** (= profile_id + "#" + index), case, handling |
| `Part` | **part_number** |
| `Equipment` | **equipment_id** |
| `Expert` | **expert_id**, display_name |
| `Document` | **doc_id**, title, source_path |
| `VideoSegment` | **segment_id**, video_id, t_start, t_end |
| `Symptom` | **symptom_id** (= defect_code), name |
| `RootCause` | **cause_id**, description |
| `Lot` | **lot_id**, product_code |

**Relationships**
```
(Process)-[:HAS_STEP {order}]->(Step)
(Step)-[:NEXT]->(Step)
(Step)-[:HAS_EXCEPTION]->(Exception)
(Step)-[:USES_PART]->(Part)
(Step)-[:ON_EQUIPMENT]->(Equipment)
(Expert)-[:CONTRIBUTED]->(Step)
(Step)-[:EVIDENCED_BY]->(VideoSegment)
(Step)-[:REFERENCES]->(Document)
(Lot)-[:PROCESSED_AT {date, shift, operator_id}]->(Process)
(Lot)-[:HAS_DEFECT {date, qty}]->(Symptom)
(Symptom)-[:DETECTED_AT]->(Process)
(Symptom)-[:CAUSED_BY {confidence, source}]->(RootCause)
(RootCause)-[:PREVENTED_BY]->(Step)
```
File `src/knowhow/kg/schema.cypher` chứa toàn bộ `CREATE CONSTRAINT ... IF NOT EXISTS` cho các khóa trên.

## 3. Loader — `knowhow.kg.loader`
- **FR-01** `load_profiles(profiles)` chỉ nhận `status == "approved"`; profile khác → bỏ qua và đếm vào `skipped`.
- **FR-02** Dùng `MERGE` theo khóa; chạy lại không nhân đôi node/cạnh. Khi `version` mới hơn → cập nhật thuộc tính.
- **FR-03** `NEXT` được tính lại cho cả process sau mỗi lần nạp, theo `step_order`.
- **FR-04** `unload_profile(profile_id)` xóa `Step` và cạnh liên quan (dùng khi profile bị reject sau khi đã approved).
- **FR-05** `load_sigma(adapter)` nạp `Lot`, `PROCESSED_AT`, `HAS_DEFECT`, `Symptom`, `CAUSED_BY`, `PREVENTED_BY` từ Sigma adapter (spec 07).
- **FR-06** Profile approved cũng được đẩy vào Milvus như một chunk (`source_type="work_profile"`, text = step + hand_action + key_point + reason + exceptions) để tìm được bằng vector.
- CLI: `knowhow kg init` (chạy schema.cypher), `knowhow kg load-profiles`, `knowhow kg load-sigma`, `knowhow kg stats`.

## 4. Retriever — `knowhow.retrieval.hybrid`
```python
class Citation(BaseModel):
    source_type: Literal["work_profile", "document", "video_segment", "sigma"]
    ref_id: str
    snippet: str
    score: float | None = None

class RetrievedContext(BaseModel):
    query: str
    process_id: str | None
    passages: list[str]          # đoạn văn bản đưa vào prompt
    graph_facts: list[str]       # câu dạng "Bước X dùng linh kiện Y"
    citations: list[Citation]

class HybridRetriever:
    def retrieve(self, query: str, process_id: str | None = None, k: int = 8) -> RetrievedContext: ...
```
Thuật toán:
1. **Vector**: tìm top-k trong Milvus (hybrid dense+sparse), filter `process_id` nếu có.
2. **Graph expansion**: với hit `work_profile` → lấy `Step` + bước trước/sau (`NEXT`), `Exception`, `Part`, `Expert`, `VideoSegment`; với hit `document` → các `Step` có `REFERENCES` tới document đó.
3. **Relational intent**: một router (LLM, output JSON enum) chọn 0..1 template Cypher trong bảng dưới. **Không sinh Cypher tự do** (an toàn + ổn định).
4. Gộp, khử trùng, xếp hạng (vector score + bonus 0.1 cho node chạm bởi graph), cắt theo ngân sách 3.000 token.

| Template | Tham số | Ví dụ câu hỏi |
|---|---|---|
| `steps_of_process` | process_id | "Công đoạn PACK01 gồm những bước nào?" |
| `steps_using_part` | part_number | "Linh kiện A123 được thao tác ở bước nào?" |
| `where_symptom_occurred` | symptom text | "Lỗi móp góc từng xảy ra ở lô/công đoạn nào?" |
| `root_causes_of_symptom` | symptom text | "Nguyên nhân thường gặp của lỗi thiếu linh kiện?" |
| `prevention_steps` | symptom text | "Bước nào giúp tránh lỗi này?" |
| `lots_with_defect` | defect_code, date range | "Lô nào bị lỗi D-07 tuần trước?" |

Symptom text → `symptom_id` bằng full-text index trên `Symptom.name` (tạo trong schema.cypher).

## 5. Acceptance Criteria
- **AC-01** Nạp 5 profile (3 approved, 1 draft, 1 rejected) → graph có đúng 3 `Step`, `skipped = 2`.
- **AC-02** Nạp lại cùng dữ liệu → số node/cạnh không đổi.
- **AC-03** `NEXT` nối đúng thứ tự `step_order` 1→2→3.
- **AC-04** `unload_profile` → `Step` và các cạnh của nó biến mất, node `Part` dùng chung vẫn còn.
- **AC-05** Câu "Lỗi thiếu linh kiện từng xảy ra ở lô nào?" trên dữ liệu seed → router chọn `where_symptom_occurred`, kết quả chứa đúng các `lot_id` trong fixture.
- **AC-06** Mọi `passage` trong `RetrievedContext` có ít nhất một `Citation` tương ứng.
- **AC-07** Router nhận câu không liên quan quan hệ → không chọn template nào (chỉ vector + expansion).
- Test AC-01..04 chạy trên Neo4j thật (`@pytest.mark.integration`); AC-05..07 có bản unit với fake graph client.

## 6. Tasks
- [ ] T05-1 `schema.cypher` + `kg init`.
- [ ] T05-2 Loader profiles (AC-01..04) + đẩy chunk profile vào Milvus (FR-06).
- [ ] T05-3 Loader Sigma (FR-05) — cần spec 07 xong interface.
- [ ] T05-4 Vector search + graph expansion.
- [ ] T05-5 Router + 6 template Cypher (AC-05, AC-07).
- [ ] T05-6 Gộp/xếp hạng/ngân sách token + citation (AC-06).

## Changelog
- v1.0 (23/9): khởi tạo.
