# 01 — Repo Scaffold & Tooling

**Owner:** Trung (structure) · Vinh (docker-compose) · **Tasks Excel:** S0-1, S0-4, S3-1

## 1. Mục tiêu
Một khung repo mà cả 5 người code song song không giẫm chân nhau, và Claude Code sinh module mới vào đúng chỗ.

## 2. Cấu trúc thư mục (bắt buộc)
```
mentormind-knowhow-ai/
├── CLAUDE.md
├── README.md
├── Makefile
├── pyproject.toml
├── .env.example
├── .gitignore
├── docker-compose.yml
├── mentormind/                 # TOÀN BỘ mã nguồn ứng dụng — Python package `mentormind`
│   ├── __init__.py
│   ├── core/                   # dùng chung, mọi module import — Trung
│   │   ├── config.py           # Settings (pydantic-settings)
│   │   ├── cli.py              # Typer app gốc, gắn sub-command từng module
│   │   ├── schemas/            # Pydantic models sinh từ docs/contracts
│   │   │   ├── work_profile.py
│   │   │   └── common.py       # DataClassification, Citation, ...
│   │   └── guard/data_guard.py # Constitution Điều 2
│   ├── capture/                # Việt Hoàng
│   │   ├── ingest/             # spec 02
│   │   └── video/              # spec 03
│   ├── processing/             # Phúc
│   │   └── vlm/                # spec 04
│   ├── knowledge_base/
│   │   ├── kg/                 # spec 05 — Trung
│   │   ├── retrieval/          # spec 05 — Trung
│   │   ├── sigma/              # spec 07 — Vinh
│   │   └── store/              # Vinh
│   │       ├── profile_store.py    # lưu WorkProfile (SQLite)
│   │       └── vector_store.py     # VectorStore: pgvector | memory (FR-05c)
│   ├── agents/                 # spec 06 — Phúc
│   ├── evaluation/             # spec 09 — Phúc
│   ├── backend/app/            # spec 08 — FastAPI, `mentormind.backend.app.main:app` — Vinh
│   ├── ui/streamlit_app.py     # spec 08 — Vinh
│   └── frontend/               # UI tablet tại trạm (Vite/React, không phải Python)
├── tests/                      # pytest, phản chiếu mentormind/: tests/<module>/.../test_*.py
├── infra/
│   ├── postgres/init.sql       # CREATE EXTENSION vector, unaccent
│   └── docker/                 # Dockerfile môi trường chạy
├── docs/                       # spec-driven: nguồn sự thật
│   └── contracts/              # JSON Schema — thắng mọi mô tả văn xuôi
├── data/                       # KHÔNG phải code
│   ├── samples/                # dữ liệu public/synthetic nhỏ, được commit
│   ├── mock_sigma/             # CSV mock, được commit
│   ├── golden_set/             # spec 09, được commit
│   └── work/                   # output trung gian, KHÔNG commit
└── scripts/demo.sh
```

> **Quy ước tên module trong các spec:** mọi đường dẫn module viết tắt, bỏ tiền tố package gốc — `core.schemas` nghĩa là `mentormind.core.schemas`, `processing.vlm.providers` là `mentormind.processing.vlm.providers`; đường dẫn file `core/guard/data_guard.py` là `mentormind/core/guard/data_guard.py`. Tên CLI (`knowhow`) và prefix biến môi trường (`KNOWHOW_`) không đổi.

## 3. Functional Requirements
- **FR-01** `pyproject.toml` ở gốc repo dùng `uv`, Python `>=3.11,<3.13`. Mã nguồn nằm trong **một package gốc `mentormind/`** (tách khỏi `tests/`, `infra/`, `docs/`, `data/`); các module `core`, `capture`, `processing`, `knowledge_base`, `agents`, `evaluation`, `backend` là sub-package của nó, import dạng `mentormind.core...`. Build config chỉ đóng gói `mentormind` (trừ `mentormind/frontend`). Entry point `knowhow = "mentormind.core.cli:app"`. `backend/` không có `requirements.txt` riêng — dependency của API nằm trong extra `api`.
- **FR-02** Dependency nhóm theo extra: `ingest`, `video`, `vlm`, `kg`, `api`, `ui`, `eval`, `dev`. `uv sync --all-extras` cài đủ.
- **FR-03** `config.py` định nghĩa `Settings` đọc từ env với prefix `KNOWHOW_`; mọi module lấy config qua `get_settings()` (cache).
- **FR-04** `Makefile` có target: `up`, `down`, `check` (ruff check + ruff format --check + mypy + pytest), `test`, `demo`, `fmt`.
- **FR-05** `docker-compose.yml`: `neo4j:5` (APOC bật, port 7474/7687, volume) và `pgvector/pgvector:pg16` (port 5432, volume, init script `infra/postgres/init.sql` chạy `CREATE EXTENSION IF NOT EXISTS vector; CREATE EXTENSION IF NOT EXISTS unaccent;`). Healthcheck cho neo4j và postgres (`pg_isready`).
- **FR-05b** Giới hạn tài nguyên để chạy được trên máy dev: Neo4j đặt `NEO4J_server_memory_heap_max__size=1G`, `NEO4J_server_memory_pagecache_size=512M`; mọi service trong compose có `mem_limit` (neo4j 2g, postgres 1g).
- **FR-05c** Vector store đứng sau interface `knowledge_base.store.vector_store.VectorStore` (`upsert(chunks)`, `search(query, k, filters) -> list[VectorHit]`, `delete(ids)`). Hai implementation chọn bằng `KNOWHOW_VECTOR_BACKEND`: `pgvector` (mặc định, cần `make up`) và `memory` (in-process, cosine + BM25 đơn giản, dùng cho unit test/CI không docker) — chỉ đổi config, Constitution Điều 5.
- **FR-06** `.gitignore` chặn: `data/raw/`, `data/factory/`, `data/work/`, `.env`, `*.mp4|*.mov|*.wav|*.mp3` **trừ** `data/samples/**`.
- **FR-07** GitHub Actions `ci.yml`: trên push/PR chạy `uv sync --all-extras` + `make check`. Test không cần docker (dùng fake).
- **FR-08** `core/schemas/work_profile.py` là Pydantic v2 model tương đương 1-1 với `docs/contracts/work_profile.schema.json`, kèm hàm `validate_against_contract(obj) -> None` dùng `jsonschema` để kiểm tra chéo.
- **FR-09** `core/guard/data_guard.py`: `DataGuard.check(classification, provider)` raise `ConfidentialDataError` khi `classification == factory_confidential` và `provider.is_cloud`.

## 4. Biến môi trường (`.env.example`)
```
KNOWHOW_NEO4J_URI=bolt://localhost:7687
KNOWHOW_NEO4J_USER=neo4j
KNOWHOW_NEO4J_PASSWORD=change-me
KNOWHOW_VECTOR_BACKEND=pgvector        # pgvector | memory
KNOWHOW_PG_DSN=postgresql://knowhow:change-me@localhost:5432/knowhow
KNOWHOW_VECTOR_TABLE=knowhow_chunks
KNOWHOW_EMBED_DIM=1024                 # bge-m3 dense
KNOWHOW_VLM_PROVIDER=qwen_api          # qwen_api | gemini | local_openai | fake
KNOWHOW_VLM_BASE_URL=https://dashscope-intl.aliyuncs.com/compatible-mode/v1
KNOWHOW_VLM_MODEL=qwen3-vl-plus
KNOWHOW_VLM_API_KEY=
KNOWHOW_VLM_FPS=4
KNOWHOW_VLM_MAX_FRAMES=48
KNOWHOW_LLM_PROVIDER=qwen_api
KNOWHOW_LLM_MODEL=qwen-plus
KNOWHOW_EMBED_MODEL=BAAI/bge-m3
KNOWHOW_PROFILE_DB=data/work/profiles.sqlite
KNOWHOW_SIGMA_ADAPTER=csv
KNOWHOW_SIGMA_CSV_DIR=data/mock_sigma
```
> Tên model/URL cloud là giá trị mặc định cho giai đoạn demo; kiểm tra lại tên model hiện hành của nhà cung cấp trước khi chạy.

## 5. Acceptance Criteria
- **AC-01** Clone mới → `uv sync --all-extras && make check` pass, không cần mạng tới dịch vụ ngoài.
- **AC-02** `make up` → trong 120s, healthcheck Neo4j và Postgres đều healthy; `SELECT extname FROM pg_extension` có `vector` và `unaccent`.
- **AC-03** `uv run knowhow --help` liệt kê sub-command: `ingest`, `video`, `vlm`, `kg`, `agent`, `sigma`, `eval`.
- **AC-04** Một WorkProfile mẫu hợp lệ pass cả Pydantic lẫn `validate_against_contract`; một profile VLM `draft` có `reason` khác null bị cả hai từ chối.
- **AC-05** `DataGuard.check("factory_confidential", cloud_provider)` raise; với `local_provider` không raise.
- **AC-06** `git add data/raw/x.mp4` bị `.gitignore` bỏ qua; `data/samples/demo.mp4` thì không.
- **AC-07** `docker compose config` cho thấy mọi service có `mem_limit`; tổng ≤ 4 GB.
- **AC-08** `Settings` với `KNOWHOW_VECTOR_BACKEND=memory` → `get_vector_store()` trả store dùng được (upsert + search) mà không cần docker.

## 6. Tasks
- [ ] T01-1 Tạo `pyproject.toml`, `Makefile`, `.gitignore`, `.env.example`, `CLAUDE.md`, `README.md`.
- [ ] T01-2 `core/config.py`, `core/cli.py` với sub-command rỗng cho từng module.
- [ ] T01-3 `core/schemas/` + `validate_against_contract` + test AC-04.
- [ ] T01-4 `core/guard/data_guard.py` + test AC-05.
- [ ] T01-5 `docker-compose.yml` + healthcheck + giới hạn bộ nhớ (Vinh) (AC-02, AC-07).
- [ ] T01-7 Interface `VectorStore` + backend `memory` + factory `get_vector_store()` theo config (AC-08).
- [ ] T01-6 CI workflow.

## Changelog
- v1.0 (23/9): khởi tạo.
- v1.1 (24/9): FR-05b giới hạn bộ nhớ Neo4j/Milvus; FR-05c Milvus Lite cho dev/CI; thêm `KNOWHOW_VLM_MAX_FRAMES` (AC-07, AC-08, T01-7).
- v1.2 (27/9): đổi Milvus → PostgreSQL 16 + pgvector (FR-05, FR-05b, env); FR-05c thay Milvus Lite bằng interface `VectorStore` + backend `memory`; AC-02, AC-07 (≤ 4 GB), AC-08, T01-7 cập nhật theo.
- v1.3 (27/9): bỏ `src/knowhow/`, dùng layout theo architecture §6 (`core/`, `capture/`, `processing/`, `knowledge_base/`, `agents/`, `evaluation/`, `backend/app/`); `specs/` → `docs/`; entry point `core.cli:app` (FR-01, FR-05c, FR-08, FR-09).
- v1.4 (28/9, Phúc): tách code khỏi test/hạ tầng/tài liệu — toàn bộ mã nguồn vào package gốc `mentormind/` (gồm `backend/`, `frontend/`), `tests/`, `infra/`, `docs/`, `data/` ở gốc; spec giữ tên module viết tắt (bỏ tiền tố `mentormind.`); entry point `mentormind.core.cli:app` (§2, FR-01).
