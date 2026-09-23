# CLAUDE.md — Hướng dẫn cho Claude Code

Repo này phát triển theo **Spec-Driven Development**. Spec là nguồn sự thật; code là sản phẩm phái sinh của spec.

## Trước khi viết bất kỳ dòng code nào
1. Đọc `specs/constitution.md` (luật bất biến của dự án).
2. Đọc `specs/00-product-overview.md` (phạm vi MVP nộp ngày 12/10/2026).
3. Đọc đúng file spec của task được giao (ví dụ task `S1-3` → `specs/04-vlm-step-description.md`).
4. Đọc các contract liên quan trong `specs/contracts/`.

## Quy trình cho mỗi task
1. Tìm task ID trong mục **Tasks** của spec. Chỉ làm task đó.
2. Viết test từ **Acceptance Criteria** trước (mỗi `AC-xx` ít nhất một test, đặt tên `test_ac_xx_...`).
3. Viết code tối thiểu để test pass. Không thêm tính năng ngoài spec.
4. Chạy `make check` (ruff + mypy + pytest). Tất cả phải xanh.
5. Đánh dấu `[x]` cho task trong file spec và ghi 1 dòng vào mục **Changelog** của spec.

## Khi spec thiếu hoặc mâu thuẫn
- Không tự đoán rồi code. Dừng lại, liệt kê câu hỏi, đề xuất sửa spec dưới dạng diff.
- Contract trong `specs/contracts/` thắng mọi mô tả văn xuôi nếu hai bên mâu thuẫn.

## Lệnh thường dùng
```bash
uv sync                 # cài dependency
make up                 # docker compose: Neo4j + Milvus
make check              # ruff + mypy + pytest
make demo               # chạy luồng end-to-end trên dữ liệu mẫu
uv run knowhow --help   # CLI chính
```

## Quy ước
- Python 3.11, package `knowhow` trong `src/knowhow/`, quản lý bằng `uv`.
- Code, tên biến, docstring: tiếng Anh. Text hiển thị cho người dùng cuối: tiếng Việt.
- Mọi I/O dữ liệu đi qua Pydantic model trong `knowhow.schemas`.
- Không bao giờ commit dữ liệu trong `data/raw/` hoặc `data/factory/`.
