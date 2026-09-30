# 02 — Document Ingest & OCR

**Owner:** Việt Hoàng · **Tasks Excel:** S0-5, S1-1, S2-5

## 1. Mục tiêu
Biến bản vẽ kỹ thuật, SOP cũ, file Excel/Word thành các `DocumentChunk` có cấu trúc, rồi index vào PostgreSQL/pgvector để retriever (spec 05) dùng được.

## 2. Công cụ
| Việc | Công cụ | Ghi chú |
|---|---|---|
| PDF/DOCX/XLSX/PPTX có text layer | mmore `process` (CPU image) | đường chính |
| PDF scan, bản vẽ có chú thích | Docling (OCR bật) | fallback 1 |
| Scan chất lượng thấp | Surya OCR | fallback 2, extra `ingest-ocr` |
| Embed | bge-m3 (`KNOWHOW_EMBED_MODEL`, local) | dense 1024 chiều |
| Index vào pgvector | `knowledge_base.store.vector_store` (spec 01 FR-05c) | hybrid dense + full-text |

Tất cả chạy local. Không gọi OCR cloud.

## 3. Data model — `core.schemas.document.DocumentChunk`
```python
class ChunkKind(StrEnum):
    TEXT = "text"
    TABLE = "table"
    FIGURE_CAPTION = "figure_caption"
    DRAWING_NOTE = "drawing_note"


class DocumentChunk(BaseModel):
    chunk_id: str  # f"{doc_id}#p{page}-{index}"
    source_type: Literal["document"] = (
        "document"  # khớp Citation.source_type (spec 05), dùng làm cột filter trong bảng vector
    )
    doc_id: str  # "DOC-" + sha256(file bytes)[:12]
    source_path: str
    title: str | None
    page: int | None
    kind: ChunkKind
    text: str  # markdown; bảng giữ dạng markdown table
    process_ids: list[str] = []  # công đoạn liên quan nếu nhận ra (VD "PACK01")
    part_numbers: list[str] = []
    data_classification: DataClassification
    extractor: Literal["mmore", "docling", "surya"]
    metadata: dict[str, Any] = {}
```

## 4. Functional Requirements
- **FR-01** `knowhow ingest run --input <dir|file> --classification <public|synthetic|factory_confidential> --out data/work/chunks/` xử lý mọi file hỗ trợ, ghi JSONL mỗi dòng một `DocumentChunk`.
- **FR-02** Chọn extractor: thử mmore; nếu text trích được < 50 ký tự/trang trung bình → coi là scan → Docling OCR; nếu Docling lỗi → Surya.
- **FR-03** Bảng được giữ nguyên cấu trúc dạng markdown table, mỗi bảng là 1 chunk `kind=table`.
- **FR-04** Chunk văn bản: 300–800 token, không cắt ngang bảng, overlap 50 token.
- **FR-05** Nhận diện `process_ids` bằng regex cấu hình được (`KNOWHOW_PROCESS_ID_REGEX`, mặc định `\b[A-Z]{3,5}\d{2}\b`) và `part_numbers` bằng regex riêng.
- **FR-06** Idempotent: cùng file (cùng hash) chạy lại → cùng `doc_id`, cùng `chunk_id`, không nhân đôi.
- **FR-07** `knowhow ingest index --chunks data/work/chunks/` embed chunk và upsert vào bảng `KNOWHOW_VECTOR_TABLE` qua `VectorStore` (không dùng mmore index — mmore index chỉ hỗ trợ Milvus). Metadata (`source_type="document"`, `doc_id`, `kind`, `process_ids`, `data_classification`) lưu thành cột filter được. Bảng dùng chung với chunk `work_profile` của spec 05, phân biệt bằng `source_type`; upsert theo `chunk_id` nên chạy lại không nhân đôi.
- **FR-08** Log một dòng tóm tắt mỗi file: extractor dùng, số trang, số chunk, thời gian.

## 5. Acceptance Criteria
- **AC-01** 3 file mẫu trong `data/samples/docs/` (1 PDF text, 1 PDF scan bản vẽ, 1 XLSX) → tất cả ra chunk, không file nào 0 chunk.
- **AC-02** Bảng trong XLSX mẫu → chunk `kind=table` giữ đủ số hàng/cột.
- **AC-03** PDF scan → `extractor ∈ {docling, surya}`.
- **AC-04** Chạy `ingest run` 2 lần → số dòng JSONL không đổi, `chunk_id` trùng khớp.
- **AC-05** Chunk mang đúng `data_classification` được truyền vào CLI.
- **AC-06** Sau `ingest index`, `VectorStore.search` với filter `kind = "table"` trả về đúng các chunk bảng. (test integration, đánh dấu `@pytest.mark.integration`, chỉ chạy khi `make up`)

## 6. Tasks
- [ ] T02-1 Model `DocumentChunk` + test.
- [ ] T02-2 Adapter mmore process (subprocess hoặc Python API) → `DocumentChunk`.
- [ ] T02-3 Fallback Docling / Surya + logic chọn extractor (AC-03).
- [ ] T02-4 Chunker (FR-04) + regex nhận diện (FR-05).
- [ ] T02-5 CLI `ingest run` + idempotency (AC-04).
- [ ] T02-6 CLI `ingest index` qua `VectorStore` (AC-06).

## Changelog
- v1.0 (23/9): khởi tạo.
- v1.1 (23/9): thêm field `source_type` tường minh vào `DocumentChunk` (trước chỉ nằm trong metadata Milvus).
- v1.2 (27/9): index vào PostgreSQL/pgvector qua `VectorStore` thay cho Milvus/mmore index (FR-07, AC-06, T02-6).
- v1.3 (27/9): đường dẫn module theo layout mới (bỏ `knowhow.`/`src/knowhow/`, xem spec 01 v1.3).
