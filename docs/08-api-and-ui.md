# 08 — API, Profile Store & UI

**Owner:** Vinh · **Tasks Excel:** S1-8, S2-4, S3-3 · luồng end-to-end S2-3 (Trung)

## 1. Profile store — `knowledge_base.store.profile_store`
SQLite tại `KNOWHOW_PROFILE_DB`.
```sql
CREATE TABLE profiles (
  profile_id TEXT PRIMARY KEY, process_id TEXT NOT NULL, status TEXT NOT NULL,
  version INTEGER NOT NULL, data_json TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE review_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT, profile_id TEXT NOT NULL, action TEXT NOT NULL,
  reviewer TEXT NOT NULL, comment TEXT, error_tags TEXT, created_at TEXT NOT NULL);
CREATE TABLE jobs (
  job_id TEXT PRIMARY KEY, kind TEXT, status TEXT, result_json TEXT, error TEXT,
  created_at TEXT, finished_at TEXT);
```
- Mọi lần ghi validate bằng `validate_against_contract`.
- Sửa nội dung profile → `version += 1`, `status = "in_review"`.

## 2. REST API (FastAPI) — `backend.app.main:app`
| Method & path | Body / query | Trả về | Ghi chú |
|---|---|---|---|
| `GET /health` | — | `{status, neo4j, postgres}` | |
| `POST /ingest/documents` | multipart files, `classification` | `{job_id}` | chạy spec 02 run + index |
| `POST /videos` | multipart file, `process_id`, `classification` | `VideoAsset` | lưu `data/work/video/` |
| `POST /videos/{video_id}/process` | `{method?, fps?}` | `{job_id}` | segment → transcribe → describe → propose-reasons |
| `GET /jobs/{job_id}` | — | `{status, result, error}` | `queued/running/done/failed` |
| `GET /profiles` | `process_id?`, `status?` | `list[WorkProfile]` | |
| `GET /profiles/{id}` | — | `WorkProfile` + lịch sử review | |
| `PATCH /profiles/{id}` | các trường sửa được | `WorkProfile` | không cho sửa `profile_id`, `generated_by`, `created_at` |
| `POST /profiles/{id}/review` | `{action: approve\|reject, reviewer, comment?, error_tags[]}` | `WorkProfile` | approve → `kg.load_profiles`; reject sau khi đã approved → `kg.unload_profile` |
| `POST /assistant/ask` | `AskRequest` | `AssistantAnswer` | spec 06 |
| `POST /rca/investigate` | `RcaRequest` | `RcaReport` | 404 khi `LotNotFound` |
| `GET /sigma/lots` | `process_id?` | `list[LotRecord]` | cho dropdown UI |
| `GET /media/{relpath}` | — | file | chỉ phục vụ file dưới `data/work/` và `data/samples/`; chặn `..` |

Job chạy bằng `BackgroundTasks` (MVP, một process). Lỗi trong job → `status=failed`, `error` có message, không làm sập server.

## 3. UI — `ui/streamlit_app.py` (tablet, tiếng Việt)
Cấu hình: `layout="wide"`, cỡ chữ ≥ 16px, nút bấm lớn; UI chỉ gọi REST API, không import trực tiếp module nghiệp vụ.

**Trang 1 — "Duyệt thao tác"**
- Bộ lọc process + trạng thái (mặc định `draft` và `in_review`).
- Mỗi profile: 3 keyframe, trình phát clip đúng `t_start–t_end`, các trường sửa được (step, hand_action, key_point, exceptions, pass_criteria).
- Ô `reason` + chọn `reason_source` (bắt buộc chọn khi có nhập reason).
- Multi-select `error_tags` (bỏ sót / bịa bước / sai thứ tự / sai vật / sai thao tác / khác).
- Nút **Duyệt** / **Từ chối** (từ chối bắt buộc nhập lý do).

**Trang 2 — "Hỏi trợ lý"**
- Chọn công đoạn, ô câu hỏi, câu trả lời với marker [n]; bấm citation → hiện keyframe/clip hoặc đoạn tài liệu.
- Khi `refused` → hiện thông điệp từ chối + tên chuyên gia gợi ý.

**Trang 3 — "Truy nguyên lỗi"**
- Chọn lot (từ `/sigma/lots`) hoặc nhập triệu chứng → bảng giả thuyết (màu theo likelihood), bảng 5-Why (cột "Đã xác minh"), danh sách lô liên quan, bước phòng ngừa, disclaimer.

## 4. `make demo` — `scripts/demo.sh`
1. `make up` và chờ healthy → `knowhow kg init` → `knowhow sigma gen-mock` → `knowhow kg load-sigma`.
2. `knowhow ingest run data/samples/docs --classification synthetic` → `knowhow ingest index`.
3. Với mỗi video trong `data/samples/video/`: segment → describe.
   - `KNOWHOW_DEMO_OFFLINE=1` (mặc định khi không có API key) → dùng `FakeVLM`/`FakeLLM` với fixture, chạy được không cần mạng.
4. Áp kết quả duyệt mẫu `data/samples/review_decisions.json` (mô phỏng chuyên gia) → approve/reject qua API.
5. In 3 câu hỏi mẫu + 1 RCA mẫu ra terminal, rồi in URL UI.

## 5. Functional Requirements
- **FR-01** Profile store như mục 1.
- **FR-02** Toàn bộ endpoint mục 2, có OpenAPI docs tại `/docs`.
- **FR-03** UI 3 trang như mục 3.
- **FR-04** `make demo` như mục 4, tổng thời gian ≤ 10 phút ở chế độ offline.
- **FR-05** CORS chỉ cho origin của Streamlit; không có auth ở MVP (ghi rõ trong README).

## 6. Acceptance Criteria
- **AC-01** `PATCH` một profile approved → `version` tăng, `status` về `in_review`, node trong graph vẫn giữ bản cũ cho tới khi approve lại.
- **AC-02** `review approve` → `GET /profiles/{id}` trả `approved` và `kg stats` tăng 1 Step.
- **AC-03** `review reject` không kèm comment → 422.
- **AC-04** `GET /media/../../etc/passwd` → 400/404, không trả file.
- **AC-05** Job lỗi (VLM raise) → `GET /jobs/{id}` trả `failed` + message; server vẫn phục vụ request khác.
- **AC-06** `/rca/investigate` với lot không tồn tại → 404.
- **AC-07** `KNOWHOW_DEMO_OFFLINE=1 make demo` chạy xong trên máy sạch, exit code 0.
- **AC-08** UI: nhập `reason` mà không chọn `reason_source` → nút Duyệt bị vô hiệu, có thông báo.

## 7. Tasks
- [ ] T08-1 Profile store + test.
- [ ] T08-2 API ingest/videos/jobs.
- [ ] T08-3 API profiles + review + nối KG loader (AC-01..03).
- [ ] T08-4 API assistant/rca/sigma/media (AC-04, AC-06).
- [ ] T08-5 Streamlit 3 trang (AC-08).
- [ ] T08-6 `scripts/demo.sh` + fixture offline (AC-07) — phối hợp Trung (S2-3). Khung đã có (preflight + luồng §4); còn thiếu các lệnh của spec 02/03/05/06/07, `data/samples/review_decisions.json` và fixture FakeVLM qua env.

## Changelog
- v1.0 (23/9): khởi tạo.
- v1.1 (27/9): `/health` báo `postgres` thay cho `milvus`.
- v1.2 (27/9): đường dẫn module theo layout mới (bỏ `knowhow.`/`src/knowhow/`, xem spec 01 v1.3).
- v1.3 (29/9, review): cấu hình API (`app_name`, `cors_origins`) nằm trong `core.config.Settings` (spec 01 FR-03); khung `scripts/demo.sh` (T08-6 chưa xong).
