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
| `POST /ingest/documents` | multipart `files`, `classification` (bắt buộc) | `{job_id}` | chạy spec 02 run + index, xem dưới bảng |
| `POST /videos` | multipart `file`, `process_id`, `classification` (bắt buộc) | `VideoAsset` | lưu `data/work/video/<video_id>/`, xem dưới bảng |
| `POST /videos/{video_id}/process` | `{method?, fps?}` | `{job_id}` | segment → transcribe → describe → propose-reasons, xem dưới bảng |
| `GET /videos/{video_id}/segments` | — | `list[Segment]` (spec 03 §3) | đọc `data/work/video/<video_id>/segments.json`; trang 1 lấy clip + keyframe từ đây |
| `GET /jobs/{job_id}` | — | `{status, result, error}` | `queued/running/done/failed` |
| `GET /profiles` | `process_id?`, `status?` | `list[WorkProfile]` | |
| `GET /profiles/{id}` | — | `WorkProfile` + lịch sử review | |
| `PATCH /profiles/{id}` | các trường sửa được | `WorkProfile` | không cho sửa `profile_id`, `generated_by`, `created_at` |
| `POST /profiles/{id}/review` | `{action: approve\|reject, reviewer, comment?, error_tags[]}` | `WorkProfile` | approve → `kg.load_profiles`; reject sau khi đã approved → `kg.unload_profile` |
| `POST /assistant/ask` | `AskRequest` | `AssistantAnswer` | spec 06 |
| `POST /rca/investigate` | `RcaRequest` | `RcaReport` | 404 khi `LotNotFound` |
| `GET /sigma/lots` | `process_id?` | `list[LotRecord]` | đọc Sigma adapter (spec 07, `KNOWHOW_SIGMA_ADAPTER`) — cùng nguồn với RCA Agent; cho dropdown UI |
| `GET /media/{relpath}` | — | file | chỉ phục vụ file dưới `data/work/` và `data/samples/`; chặn `..` |

`POST /ingest/documents`:
- `classification` bắt buộc, không có mặc định (spec 02 FR-01b); thiếu hoặc ngoài enum → 422, không lưu tệp, không tạo job.
- Tệp lưu ở `data/work/docs/<job_id>/<tên tệp>`: chỉ giữ phần tên, bỏ mọi thành phần thư mục (`../`, `/`, `\`). Tên rỗng, `.`, `..` hoặc hai tệp trùng tên trong một lần gửi → 422.
- Job chạy `ingest run` trên các tệp đó, ghi chunk vào `data/work/chunks/` như CLI (nên `knowhow ingest index` vẫn thấy), rồi chỉ index các `<doc_id>.jsonl` của lần tải này. Một tệp lỗi không dừng các tệp khác.
- `result` = `{classification, files: [{name, doc_id, extractor, pages, chunks, skipped, error}], chunks_indexed}` (`core.schemas.DocumentIngestResult`). Không tệp nào ra chunk (mọi tệp lỗi hoặc không hỗ trợ) hoặc bước index lỗi → `failed`, `error` nêu lý do, `result` vẫn kèm các tệp đã xét.
- Tài liệu không qua bước duyệt: chunk vào kho tìm kiếm ngay với nhãn đã chọn (spec 02); chỉ WorkProfile cần chuyên gia duyệt (constitution Điều 3).

`POST /videos` và `POST /videos/{video_id}/process`:
- `classification` bắt buộc như tài liệu; đuôi ngoài `.mp4 .mov .mkv .webm .avi .m4v` → 422. `video_id` = `VID-` + sha256[:12] của nội dung (spec 03 §3, trùng id mà `knowhow vlm describe` dùng). Tệp lưu ở `data/work/video/<video_id>/source<đuôi>`, kèm `video.json` = `VideoAsset` của spec 03 §3 (`duration_s`, `fps` đọc bằng OpenCV, `has_audio` bằng ffprobe, `process_id`, `data_classification`) để bước xử lý biết nhãn và công đoạn; tải lại cùng nội dung thì ghi đè `video.json`.
- `process`: `video_id` chưa tải lên (không có `video.json`) → 404. `method` ∈ {`hand_activity` (mặc định), `scene`, `fixed_window`}, giá trị khác → 422. Job chạy `VideoCapturePipeline` của spec 03 (FR-09: cắt theo `method`, thiếu thư viện/model thì rơi xuống cách sau theo spec 03 FR-03; keyframe + clip; transcribe nếu `has_audio`; ghi `segments.json`, `transcript.json`).
- Rồi `DescribePipeline` đủ lượt A, B, C với VLM/LLM cấu hình trong `.env` (DataGuard kiểm trước lời gọi đầu tiên) → profile `draft` vào profile store như `knowhow vlm describe`; mỗi bước mang `transcript_excerpt` của riêng nó (spec 04 §3). Bước có excerpt → `propose-reasons` (LLM, hậu kiểm khớp excerpt); không có transcript thì `reason` để trống, chuyên gia nhập ở trang 1.
- `result.progress = {stage, done, total}`, `stage` ∈ `cut` (cắt + keyframe + clip, đếm theo đoạn), `transcribe` (ASR, theo giây audio), `describe` (lượt gọi VLM của lượt A và B), `merge` (lượt C), `reasons` (theo bước có excerpt). Xong → `result` = `{video_id, process_id, method, method_used, segments, profiles: [profile_id], failed_segments, transcript_lines, steps_with_excerpt, reasons_filled, progress}`. Lỗi → `failed` + message.

Job chạy bằng `BackgroundTasks` (MVP, một process). Lỗi trong job → `status=failed`, `error` có message, không làm sập server. Job chết theo process: API khởi động lại khi job còn `queued`/`running` thì job đó không bao giờ xong, nên `GET /jobs/{id}` trả nó `failed` kèm thông báo khởi động lại (job tạo trước lúc process API hiện tại khởi động).

## 3. UI — `ui/streamlit_app.py` (tablet, tiếng Việt)
Cấu hình: `layout="wide"`, cỡ chữ ≥ 16px, nút bấm lớn; UI chỉ gọi REST API, không import trực tiếp module nghiệp vụ.

**Trang 1 — "Duyệt thao tác"**
- Bộ lọc process + trạng thái (mặc định `draft` và `in_review`) + video (các `evidence.video_id` trong danh sách); các bước của một video xếp theo `t_start`.
- Mỗi profile: 3 keyframe (ảnh thật từ `evidence.keyframes`, qua `/media`), trình phát clip đúng `t_start–t_end` (clip của đoạn chứa bước, lấy từ `GET /videos/{video_id}/segments`), các trường sửa được (step, hand_action, key_point, exceptions, pass_criteria).
- Ô "Lời chuyên gia (transcript)" hiện `evidence.transcript_excerpt` của riêng bước đó (spec 04 §3: mỗi câu thuộc một bước); chưa có thì ghi rõ và nhắc chuyên gia tự nhập lý do.
- Ô `reason` + chọn `reason_source` (bắt buộc chọn khi có nhập reason).
- Multi-select `error_tags` (bỏ sót / bịa bước / sai thứ tự / sai vật / sai thao tác / khác).
- Nút **Duyệt** / **Từ chối** (từ chối bắt buộc nhập lý do).

**Trang 2 — "Hỏi trợ lý"**
- Chọn công đoạn, ô câu hỏi, câu trả lời với marker [n]; bấm citation → hiện keyframe/clip hoặc đoạn tài liệu. API điền cho UI: mọi citation có `excerpt` (đoạn trích, lấy từ `snippet` của agent); citation `work_profile` có `title` (tên bước), `t_start`/`t_end` và `keyframe_url` (`/media/...`) lấy từ profile.
- Khi `refused` → hiện thông điệp từ chối + tên chuyên gia gợi ý.

**Trang 3 — "Truy nguyên lỗi"**
- Chọn lot (từ `/sigma/lots`) hoặc nhập triệu chứng → bảng giả thuyết (màu theo likelihood), bảng 5-Why (cột "Đã xác minh"), danh sách lô liên quan, bước phòng ngừa, disclaimer. Dropdown có lựa chọn "không chọn lot" để chỉ gửi triệu chứng.

**Trang 4 — "Tải dữ liệu"** (video thao tác + tài liệu)
- Video: chọn tệp video, mã công đoạn (mặc định `PACK01`), cách cắt (Theo nhịp tay — mặc định / Theo cảnh / Cố định 10 giây) và nhãn dữ liệu (không chọn sẵn) → `POST /videos` → `POST /videos/{id}/process` → tiến độ theo giai đoạn của `result.progress` (Cắt đoạn → Nhận dạng lời nói → VLM mô tả → Gộp bước → Đề xuất lý do). Xong → cách cắt thực dùng, số câu transcript, số bước có lời chuyên gia / có lý do đề xuất. Job id được nhớ trong trình duyệt nên tải lại trang vẫn theo dõi tiếp. Xong → danh sách các bước (profile của video, theo thời gian, kèm keyframe) + nút **Duyệt các bước này** mở trang 1 lọc theo video.
- Tài liệu: chọn một hoặc nhiều tệp `.pdf .docx .xlsx .pptx` và nhãn dữ liệu (Công khai / Dữ liệu tổng hợp / Mật – dữ liệu nhà máy). Không chọn sẵn nhãn: nút **Tải lên & xử lý** bị vô hiệu tới khi có ít nhất một tệp và đã chọn nhãn.
- Gửi `POST /ingest/documents`, rồi hỏi `GET /jobs/{id}` mỗi ~2 giây tới khi `done`/`failed`; hiện trạng thái Đang chờ / Đang xử lý / Hoàn tất / Lỗi.
- Xong → bảng từng tệp (tên, `doc_id`, extractor, số trang, số chunk, bỏ qua/lỗi) và tổng số chunk đã index. Lỗi hiện bằng tiếng Việt, không có stack trace.

## 4. `make demo` — `scripts/demo.sh`
1. `make up` và chờ healthy → `knowhow kg init` → `knowhow sigma gen-mock` → `knowhow kg load-sigma --classification synthetic`.
2. `knowhow ingest run data/samples/docs --classification synthetic` → `knowhow ingest index`.
3. Với mỗi video trong `data/samples/video/`: segment → describe.
   - `KNOWHOW_DEMO_OFFLINE=1` (mặc định khi không có API key) → dùng `FakeVLM`/`FakeLLM` với fixture, chạy được không cần mạng.
4. Áp kết quả duyệt mẫu `data/samples/review_decisions.json` (mô phỏng chuyên gia) → approve/reject qua API.
5. In 3 câu hỏi mẫu + 1 RCA mẫu ra terminal, rồi in URL UI.

## 5. Functional Requirements
- **FR-01** Profile store như mục 1.
- **FR-02** Toàn bộ endpoint mục 2, có OpenAPI docs tại `/docs`.
- **FR-03** UI 4 trang như mục 3.
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
- **AC-09** `POST /ingest/documents` với một tệp hỗ trợ và `classification` → job `done`; `result.files` có `doc_id`, `pages`, `chunks` của tệp; các chunk mang đúng nhãn đã chọn và đã được upsert vào vector store (chỉ chunk của lần tải này).
- **AC-10** Tên tệp có thành phần đường dẫn (VD `../../evil.pdf`) → tệp được lưu dưới `data/work/docs/<job_id>/` chỉ theo tên gốc (`evil.pdf`), không ghi ra ngoài thư mục đó.
- **AC-11** Thiếu `classification` hoặc giá trị ngoài enum → 422, không lưu tệp, không tạo job (không còn mặc định `synthetic`).
- **AC-12** Mọi tệp lỗi hoặc không hỗ trợ, hoặc bước index raise → `GET /jobs/{id}` trả `failed` + message; server vẫn phục vụ request khác.
- **AC-13** `POST /videos` → `video_id` = `VID-` + sha256[:12] của nội dung; tệp và `video.json` nằm dưới `data/work/video/<video_id>/`; thiếu `classification` hoặc đuôi không phải video → 422, không lưu tệp.
- **AC-14** `POST /videos/{id}/process` (VLM/LLM giả) → job `done`, `result.profiles` là các profile `draft` của video và `GET /profiles` trả chúng; `GET /videos/{id}/segments` trả các đoạn của lần chạy; `method` khác `fixed_window` → 422; video chưa tải lên → 404; pipeline raise → `failed` + message.
- **AC-15** `GET /sigma/lots` trả đúng các lot của Sigma adapter (CSV mock), và `/rca/investigate` với bất kỳ lot nào trong đó không trả 404 (ở cả chế độ `mock` lẫn `live`).
- **AC-16** `POST /assistant/ask` (live): citation có `excerpt` khi agent có `snippet`; citation `work_profile` của một profile có trong store mang `title` = tên bước, `t_start`/`t_end` của bước và `keyframe_url` dạng `/media/...` khi profile có keyframe.
- **AC-17** Job còn `running` từ trước khi API khởi động lại → `GET /jobs/{id}` trả `failed` + thông báo khởi động lại; job tạo sau khi khởi động vẫn `running`.
- **AC-18** `POST /videos/{id}/process` (bộ cắt, ASR, VLM, LLM giả): `method=hand_activity` khi thiếu MediaPipe → job `done`, `result.method_used="scene"`; `method` ngoài 3 giá trị → 422; video có audio → `transcript_lines` > 0, mỗi bước chỉ trích câu của nó, `steps_with_excerpt` và `reasons_filled` đúng; `progress.stage` đi qua `cut` → `transcribe` → `describe`.

## 7. Tasks
- [ ] T08-1 Profile store + test.
- [ ] T08-2 API ingest/videos/jobs.
- [ ] T08-3 API profiles + review + nối KG loader (AC-01..03).
- [ ] T08-4 API assistant/rca/sigma/media (AC-04, AC-06).
- [ ] T08-5 Streamlit 3 trang (AC-08).
- [ ] T08-6 `scripts/demo.sh` + fixture offline (AC-07) — phối hợp Trung (S2-3). Khung đã có (preflight + luồng §4); còn thiếu các lệnh của spec 02/03/05/06/07, `data/samples/review_decisions.json` và fixture FakeVLM qua env.
- [x] T08-7 Tải tài liệu: `POST /ingest/documents` chạy thật spec 02 run + index (thay kết quả giả), `classification` bắt buộc, tên tệp chỉ giữ phần tên; trang 4 "Tải tài liệu" (AC-09..AC-12).
- [x] T08-8 Luồng UI đầy đủ: tải video → job xử lý thật (cắt `fixed_window` tạm thay spec 03, keyframe, describe A–C, propose-reasons khi có transcript) → trang 1 có keyframe/clip/transcript và lọc theo video → trợ lý có trích dẫn đủ thông tin, RCA lấy lot từ Sigma adapter; job dở dang khi API khởi động lại → `failed` (AC-13..AC-17).
- [x] T08-9 Nối spec 03 vào luồng UI: `method` cắt, transcribe khi có audio, transcript theo bước, tiến độ theo giai đoạn (AC-18).

## Changelog
- v1.0 (23/9): khởi tạo.
- v1.1 (27/9): `/health` báo `postgres` thay cho `milvus`.
- v1.2 (27/9): đường dẫn module theo layout mới (bỏ `knowhow.`/`src/knowhow/`, xem spec 01 v1.3).
- v1.3 (29/9, review): cấu hình API (`app_name`, `cors_origins`) nằm trong `core.config.Settings` (spec 01 FR-03); khung `scripts/demo.sh` (T08-6 chưa xong).
- v1.4 (02/10, review): review hoàn tác thất bại khôi phục graph theo bản đang lưu (profile đã approved được nạp lại, không bị gỡ khỏi graph); test AC-01 kiểm graph giữ bản cũ tới khi approve lại; demo nạp Sigma mock bằng `--classification synthetic` (spec 05 FR-05).
- v1.5 (06/10, Phúc): `POST /ingest/documents` chạy thật spec 02 (`ingest run` rồi chỉ index các `<doc_id>.jsonl` của lần tải, qua `capture.ingest.index.index_files`; `ingest index` không đổi) thay cho kết quả giả; `classification` bắt buộc như spec 02 FR-01b (bỏ mặc định `synthetic` vốn có thể dán nhầm nhãn cho dữ liệu nhà máy); tên tệp chỉ giữ phần tên (trước đó `../../x.pdf` hay `/x.pdf` ghi ra ngoài `data/work/docs/`). Thêm trang 4 "Tải tài liệu" (FR-03 thành 4 trang), AC-09..AC-12, task T08-7. Trang 4 làm trong UI React (`mentormind/frontend/`) như 3 trang kia; mục 3 và T08-5 vẫn ghi Streamlit, chưa sửa.
- v1.6 (06/10, Phúc): luồng UI đầy đủ (T08-8). `POST /videos` giữ video theo `video_id` = `VID-`+sha256[:12] nội dung (trùng id của `knowhow vlm describe`) kèm `video.json` (`VideoAsset` spec 03), `classification` bắt buộc; `POST /videos/{id}/process` chạy thật thay kết quả giả (cắt `fixed_window` 10 s của spec 04 FR-05 cho tới khi có spec 03, `DescribePipeline` A–C, lưu nháp vào profile store, `propose-reasons` khi có transcript, `result.progress`); thêm `GET /videos/{id}/segments`. `GET /sigma/lots` đọc Sigma adapter thay 3 lot viết cứng (`LOT-2026-*` không có trong Sigma nên RCA live luôn 404). Citation của `/assistant/ask` có `excerpt`, và `title`/thời điểm/`keyframe_url` cho bước thao tác. Trang 4 thành "Tải dữ liệu" (video + tài liệu); trang 1 có keyframe, clip, transcript, lọc video; trang 3 cho phép không chọn lot. Job dở dang khi API khởi động lại (vd. `make start` lần nữa) → `GET /jobs/{id}` trả `failed` thay vì treo `running`. AC-13..AC-17. Tài liệu không qua bước duyệt (ghi rõ ở §2).
- v1.7 (06/10, Phúc): nối spec 03 vào luồng UI (T08-9): `POST /videos/{id}/process` nhận `method` (`hand_activity` mặc định, `scene`, `fixed_window`; thiếu thư viện thì rơi xuống và `result.method_used` báo cách thực dùng), chạy `VideoCapturePipeline` (cắt + keyframe + clip + transcribe nếu có audio), transcript theo từng bước (spec 04 §3), `propose-reasons` cho bước có excerpt; `result.progress` có `stage` (`cut` → `transcribe` → `describe` → `merge` → `reasons`); trang 4 chọn cách cắt và hiện từng giai đoạn; trang 1 ghi transcript là lời về chính bước đó và đánh dấu lý do AI trích. AC-18.
