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
├── specs/                      # spec-driven: nguồn sự thật
├── src/knowhow/
│   ├── __init__.py
│   ├── config.py               # Settings (pydantic-settings)
│   ├── cli.py                  # Typer app gốc, gắn sub-command từng module
│   ├── schemas/                # Pydantic models sinh từ specs/contracts
│   │   ├── work_profile.py
│   │   └── common.py           # DataClassification, Citation, ...
│   ├── guard/data_guard.py     # Constitution Điều 2
│   ├── ingest/                 # spec 02 — Việt Hoàng
│   ├── video/                  # spec 03 — Việt Hoàng
│   ├── vlm/                    # spec 04 — Phúc
│   ├── kg/                     # spec 05 — Trung
│   ├── retrieval/              # spec 05 — Trung
│   ├── agents/                 # spec 06 — Phúc
│   ├── sigma/                  # spec 07 — Vinh
│   ├── api/                    # spec 08 — Vinh
│   ├── store/profile_store.py  # lưu WorkProfile (SQLite) — Vinh
│   └── eval/                   # spec 09 — Phúc
├── ui/streamlit_app.py         # spec 08 — Vinh
├── data/
│   ├── samples/                # dữ liệu public/synthetic nhỏ, được commit
│   ├── mock_sigma/             # CSV mock, được commit
│   ├── golden_set/             # spec 09, được commit
│   └── work/                   # output trung gian, KHÔNG commit
├── scripts/demo.sh
└── tests/                      # tests/<module>/test_*.py
```

## 3. Functional Requirements
- **FR-01** `pyproject.toml` dùng `uv`, Python `>=3.11,<3.13`, package `knowhow` ở `src/`, entry point `knowhow = "knowhow.cli:app"`.
- **FR-02** Dependency nhóm theo extra: `ingest`, `video`, `vlm`, `kg`, `api`, `ui`, `eval`, `dev`. `uv sync --all-extras` cài đủ.
- **FR-03** `config.py` định nghĩa `Settings` đọc từ env với prefix `KNOWHOW_`; mọi module lấy config qua `get_settings()` (cache).
- **FR-04** `Makefile` có target: `up`, `down`, `check` (ruff check + ruff format --check + mypy + pytest), `test`, `demo`, `fmt`.
- **FR-05** `docker-compose.yml`: `neo4j:5` (APOC bật, port 7474/7687, volume), `milvus-standalone` v2.4 + `etcd` + `minio` theo compose chính thức của Milvus. Healthcheck cho neo4j và milvus.
- **FR-05b** Giới hạn tài nguyên để chạy được trên máy dev: Neo4j đặt `NEO4J_server_memory_heap_max__size=1G`, `NEO4J_server_memory_pagecache_size=512M`; mọi service trong compose có `mem_limit` (neo4j 2g, milvus 4g, etcd 512m, minio 512m).
- **FR-05c** Dev/CI được phép dùng Milvus Lite bằng cách đặt `KNOWHOW_MILVUS_URI=./data/work/milvus.db` (chỉ đổi config — Constitution Điều 5). Nếu Milvus Lite không hỗ trợ hybrid dense+sparse mà spec 05 cần, Milvus Lite chỉ dùng cho unit test, demo vẫn chạy `milvus-standalone`.
- **FR-06** `.gitignore` chặn: `data/raw/`, `data/factory/`, `data/work/`, `.env`, `*.mp4|*.mov|*.wav|*.mp3` **trừ** `data/samples/**`.
- **FR-07** GitHub Actions `ci.yml`: trên push/PR chạy `uv sync --all-extras` + `make check`. Test không cần docker (dùng fake).
- **FR-08** `schemas/work_profile.py` là Pydantic v2 model tương đương 1-1 với `specs/contracts/work_profile.schema.json`, kèm hàm `validate_against_contract(obj) -> None` dùng `jsonschema` để kiểm tra chéo.
- **FR-09** `guard/data_guard.py`: `DataGuard.check(classification, provider)` raise `ConfidentialDataError` khi `classification == factory_confidential` và `provider.is_cloud`.

## 4. Biến môi trường (`.env.example`)
```
KNOWHOW_NEO4J_URI=bolt://localhost:7687
KNOWHOW_NEO4J_USER=neo4j
KNOWHOW_NEO4J_PASSWORD=change-me
KNOWHOW_MILVUS_URI=http://localhost:19530
KNOWHOW_MILVUS_COLLECTION=knowhow_chunks
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
- **AC-02** `make up` → trong 120s, healthcheck Neo4j và Milvus đều healthy.
- **AC-03** `uv run knowhow --help` liệt kê sub-command: `ingest`, `video`, `vlm`, `kg`, `agent`, `sigma`, `eval`.
- **AC-04** Một WorkProfile mẫu hợp lệ pass cả Pydantic lẫn `validate_against_contract`; một profile VLM `draft` có `reason` khác null bị cả hai từ chối.
- **AC-05** `DataGuard.check("factory_confidential", cloud_provider)` raise; với `local_provider` không raise.
- **AC-06** `git add data/raw/x.mp4` bị `.gitignore` bỏ qua; `data/samples/demo.mp4` thì không.
- **AC-07** `docker compose config` cho thấy mọi service có `mem_limit`; tổng ≤ 7.5 GB.
- **AC-08** `Settings` với `KNOWHOW_MILVUS_URI` là đường dẫn file `.db` → vector store client khởi tạo được mà không cần docker.

## 6. Tasks
- [ ] T01-1 Tạo `pyproject.toml`, `Makefile`, `.gitignore`, `.env.example`, `CLAUDE.md`, `README.md`.
- [ ] T01-2 `config.py`, `cli.py` với sub-command rỗng cho từng module.
- [ ] T01-3 `schemas/` + `validate_against_contract` + test AC-04.
- [ ] T01-4 `guard/data_guard.py` + test AC-05.
- [ ] T01-5 `docker-compose.yml` + healthcheck + giới hạn bộ nhớ (Vinh) (AC-02, AC-07).
- [ ] T01-7 Hỗ trợ Milvus Lite qua config; kiểm chứng hybrid search trên Milvus Lite và ghi kết quả vào Changelog (AC-08).
- [ ] T01-6 CI workflow.

## Changelog
- v1.0 (23/9): khởi tạo.
- v1.1 (24/9): FR-05b giới hạn bộ nhớ Neo4j/Milvus; FR-05c Milvus Lite cho dev/CI; thêm `KNOWHOW_VLM_MAX_FRAMES` (AC-07, AC-08, T01-7).
