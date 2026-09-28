# CLAUDE.md — Hướng dẫn cho Claude Code

Repo này phát triển theo **Spec-Driven Development**. Spec là nguồn sự thật; code là sản phẩm phái sinh của spec.

## Trước khi viết bất kỳ dòng code nào
1. Đọc `docs/constitution.md` (luật bất biến của dự án).
2. Đọc `docs/00-product-overview.md` (phạm vi MVP nộp ngày 12/10/2026).
3. Đọc đúng file spec của task được giao (ví dụ task `S1-3` → `docs/04-vlm-step-description.md`).
4. Đọc các contract liên quan trong `docs/contracts/`.

## Quy trình cho mỗi task
1. Tìm task ID trong mục **Tasks** của spec. Chỉ làm task đó.
2. Viết test từ **Acceptance Criteria** trước (mỗi `AC-xx` ít nhất một test, đặt tên `test_ac_xx_...`).
3. Viết code tối thiểu để test pass. Không thêm tính năng ngoài spec.
4. Chạy `make check` (ruff + mypy + pytest). Tất cả phải xanh.
5. Đánh dấu `[x]` cho task trong file spec và ghi 1 dòng vào mục **Changelog** của spec.

## Khi spec thiếu hoặc mâu thuẫn
- Không tự đoán rồi code. Dừng lại, liệt kê câu hỏi, đề xuất sửa spec dưới dạng diff.
- Contract trong `docs/contracts/` thắng mọi mô tả văn xuôi nếu hai bên mâu thuẫn.

## Lệnh thường dùng
```bash
uv sync                 # cài dependency
make up                 # docker compose: mentormind + vlm-server + PostgreSQL/pgvector + Neo4j (profile lite)
make dev-up / dev-shell # chỉ 2 container dev; VLM_SERVER_AUTOSTART=true để bật luôn Qwen3-VL
make check              # ruff + mypy + pytest
make demo               # chạy luồng end-to-end trên dữ liệu mẫu
uv run knowhow --help   # CLI chính
make vlm-server         # Qwen3-VL-8B tự host trên 1 GPU (submodule 3rdparty/vlm_server = vlm-engine)
uv run knowhow vlm ping # kiểm tra VLM đang cấu hình (provider: uv run knowhow vlm providers)
```
API key nằm trong `.secrets/secrets.env` (gitignored), hướng dẫn tại `.secrets/README.md`.

## Quy ước
- Python 3.11, quản lý bằng `uv`. Toàn bộ mã nguồn nằm trong package gốc `mentormind/` (`docs/architecture.md` §6): `mentormind/core/` (config, cli, schemas, guard), `capture/`, `processing/`, `knowledge_base/`, `agents/`, `evaluation/`, `backend/app/` (API), `frontend/`. Import luôn tuyệt đối từ gốc: `from mentormind.core.schemas import ...`. CLI vẫn tên `knowhow`.
- `tests/` phản chiếu cấu trúc `mentormind/`; hạ tầng ở `infra/`; dữ liệu ở `data/`; tài liệu ở `docs/`. Spec viết tên module bỏ tiền tố `mentormind.` (`core.schemas` = `mentormind.core.schemas`).
- Code, tên biến, docstring: tiếng Anh. Text hiển thị cho người dùng cuối: tiếng Việt.
- Mọi I/O dữ liệu đi qua Pydantic model trong `mentormind.core.schemas`.
- Không bao giờ commit dữ liệu trong `data/raw/` hoặc `data/factory/`.
