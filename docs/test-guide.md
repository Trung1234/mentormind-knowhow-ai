# Hướng dẫn kiểm thử — Mentor Mind MVP

**Vai trò soạn:** Senior Tester · **Owner:** Trung · **Áp dụng cho:** bản nộp 12/10/2026 ·
**Phiên bản:** 1.0 (04/10/2026, `main` @ `da08a2e`)

Liên quan: [constitution](constitution.md) · [PRD §12](PRD.md) · [BRD §14](BRD.md) · spec 01–09 ·
[10-work-left.md](10-work-left.md) (hạng mục còn thiếu).

## 1. Mục đích và phạm vi

Tài liệu này cho cả đội biết **kiểm gì, kiểm bằng cách nào, khi nào được phép nộp**. Nó không thay thế
Acceptance Criteria trong spec. Nó gom các AC lại thành chiến lược, thêm test case thủ công/E2E cho những
gì pytest không phủ được, và đặt tiêu chí ra cho bản nộp.

- **Trong phạm vi:** luồng PACK01 từ dữ liệu thô đến câu trả lời có citation, RCA trên Sigma mock, báo cáo
  evaluation, bảo vệ dữ liệu, UI tablet.
- **Ngoài phạm vi:** Sigma thật, camera AI, dữ liệu `factory_confidential` thật, SSO, tải/hiệu năng ở quy
  mô production (BRD §8.2).

## 2. Nguyên tắc kiểm thử

1. **Thứ tự nguồn sự thật khi phán đúng/sai:** constitution > contract trong `docs/contracts/` > AC của spec
   > văn xuôi của PRD/BRD/architecture. Hai nguồn mâu thuẫn thì ghi lỗi tài liệu, không tự chọn.
2. **Mỗi AC có ít nhất một test tự động** tên `test_ac_xx_...` (constitution Điều 6). AC chỉ kiểm được bằng
   tay (GPU, UI, máy sạch) phải có test case ở §7 và có kết quả được ghi lại.
3. **Test tự động không gọi mạng thật.** Dùng `FakeVLM`, `FakeLLM`, `RecordingHttp`.
4. **Dữ liệu test chỉ là `public` hoặc `synthetic`.** Không đưa dữ liệu nhà máy vào test, issue hay ảnh chụp.
5. **Không dùng output của model làm ground truth của chính model đó** (PRD §7).
6. **Bốn quy tắc không thương lượng.** Mọi vi phạm là lỗi S1, chặn việc nộp:
   - dữ liệu `factory_confidential` không bao giờ tới provider cloud;
   - `reason` chỉ đến từ lời chuyên gia, VLM không tự điền;
   - chỉ profile `approved` vào knowledge base và câu trả lời;
   - không có citation hợp lệ thì phải từ chối.

## 3. Các tầng kiểm thử

| Tầng | Kiểm gì | Công cụ / lệnh | Khi nào chạy |
|---|---|---|---|
| T0 Tĩnh | Lint, format, kiểu; `mypy --strict` cho `core/schemas` và `core/guard`; JSON Schema hợp lệ | `make check`; CI `ci.yml`, `contract-lint.yml` | Mỗi commit (CI) |
| T1 Unit | Logic từng module với fake provider | `uv run pytest` | Mỗi commit (CI) |
| T2 Contract | Pydantic và `validate_against_contract` khớp `work_profile.schema.json` | pytest (spec 01 AC-04) | Mỗi commit (CI) |
| T3 Integration | Neo4j 5 + Postgres/pgvector thật | `pytest -m integration` (§4.2) | Trước khi merge thay đổi ở `knowledge_base/`; trước khi nộp. **CI không chạy tầng này** |
| T4 API | Endpoint FastAPI | `TestClient` trong `tests/test_api_endpoints.py`, `tests/backend/` | Mỗi commit (CI) |
| T5 E2E | Toàn luồng trên dữ liệu mẫu | `KNOWHOW_DEMO_OFFLINE=1 make demo` | Hằng ngày khi preflight đã xanh; bắt buộc trước khi nộp |
| T6 UI | Màn hình tablet, tiếng Việt, luồng duyệt | Thủ công (§7.4). CI chỉ chạy `tsc` + `vite build` | Khi UI thay đổi; trước khi nộp |
| T7 Chất lượng model | VLM sweep, Ragas | `knowhow vlm sweep`, `knowhow eval ragas` / `report` | Khi đổi prompt, model hoặc profile; trước khi nộp. So với ngưỡng, không pass/fail theo commit |
| T8 Bảo mật | DataGuard, outbound guard, path traversal, `.gitignore` | Tự động trong T1 + một lượt thủ công (§7.3) | Mỗi commit + trước khi nộp |

## 4. Môi trường và lệnh chạy

### 4.1 Cục bộ, không cần docker

```bash
uv sync --all-extras
make check                                  # ruff + mypy + pytest
uv run pytest tests/processing/vlm -k ac_02 # chạy một nhóm
uv run pytest -rs                           # liệt kê test bị skip và lý do
```

Mốc hiện tại trên `main` @ `da08a2e`: **274 pass, 1 skip** (test Neo4j ở §4.2).

Fixture `settings` trong `tests/core/providers/conftest.py` tắt `.env`. Các test khác có thể đọc biến
`KNOWHOW_*` từ shell. Nếu một test chỉ fail trên máy bạn, chạy `env | grep KNOWHOW_` trước.

### 4.2 Integration (Neo4j + Postgres)

```bash
make up    # spec 01 AC-02: Neo4j và Postgres healthy trong ≤ 120 s
KNOWHOW_TEST_NEO4J_URI=bolt://localhost:7687 KNOWHOW_TEST_NEO4J_PASSWORD=change-me \
  uv run pytest -m integration -rs
make down
```

- Test Neo4j gắn dữ liệu với một token ngẫu nhiên (`IT…`). Dù vậy, vẫn nên dùng một instance Neo4j riêng
  cho test, không dùng chung với DB demo.
- Sau khi merge nhánh ingest, test pgvector **tự skip** nếu Postgres không chạy. Skip không phải pass:
  luôn chạy với `-rs` và dán phần tóm tắt skip vào PR.

### 4.3 API và UI

```bash
uv run uvicorn mentormind.backend.app.main:app --reload --port 8000   # Swagger: http://127.0.0.1:8000/docs
cd mentormind/frontend && npm ci && npm run dev                       # VITE_API_BASE_URL=http://localhost:8000
```

`make start` chạy `./start.sh`: cài dependency frontend, rồi bật uvicorn (cổng 8000) và Vite dev server cùng lúc.

### 4.4 VLM/LLM thật (chỉ với dữ liệu `public`/`synthetic`)

| Cách chạy | Cấu hình | Ghi chú |
|---|---|---|
| Giả lập (mặc định cho test và demo offline) | `KNOWHOW_VLM_PROVIDER=fake`, `KNOWHOW_LLM_PROVIDER=fake` | Không mạng, kết quả tất định |
| Tự host (Ollama, macOS hoặc Linux) | `make vlm-server` rồi `uv run knowhow vlm ping --frames 48` (spec 04 AC-15); `.env` mặc định đã trỏ `http://127.0.0.1:11434/v1`, model `qwen3-vl:8b` | Cần submodule: `git submodule update --init 3rdparty/vlm_server`. Xem bên dưới |
| Cloud (OpenRouter, SiliconFlow, Qwen API) | Key trong `.env` (`uv run knowhow vlm providers`) | Không bao giờ dùng với dữ liệu mật |

Chạy server bằng `bash 3rdparty/vlm_server/scripts/serve-ollama.sh` (hướng dẫn: `3rdparty/vlm_server/scripts/README.md`).
Script tải Ollama 0.35.1, đặt context (macOS 49152, Linux 98304; Ollama mặc định chỉ 4096) và
**số token tối thiểu mỗi ảnh** (`--image-min-tokens`, mặc định 512): Ollama tự ép 1024 token cho mỗi ảnh Qwen-VL,
nên trước đây 48 khung đã cần khoảng 50k token. Thêm `--ngrok` để mở cho máy khác.

Mốc đo ngày 04/10 trên Mac mini M4 16 GB (bản cũ, 1024 token/ảnh, context 16k): `vlm ping` **PASS**, 8 khung,
khoảng 87 s, chạy 100% GPU; context 32k tràn 29% sang CPU. Với 512 token/ảnh, 40 khung (một đoạn 10 s) khoảng 22k token.

## 5. Dữ liệu kiểm thử

| Bộ dữ liệu | Đường dẫn | Dùng cho | Trạng thái 04/10 |
|---|---|---|---|
| Fixture VLM | `tests/fixtures/vlm/` | Spec 04 | Có |
| Khung hình tổng hợp | fixture `frames` trong `tests/conftest.py` | Sampler, guard | Có |
| Sigma mock | `data/mock_sigma/` | Spec 05/07, RCA | Có |
| Ground truth LASI (public) | `data/video/groundtruth.json` | `vlm sweep`; tải video theo `docs/reports/c2-vlm-smoke-and-fps-sweep.md` | Có (không commit video) |
| Tài liệu mẫu | `data/samples/docs/` | Spec 02 AC-01…03 | Nằm trên nhánh ingest |
| Case PACK01 C1–C5 | `data/samples/packing/case_00x/` | E2E | Chưa có |
| `review_decisions.json` | `data/samples/` | `make demo` bước 4 | Chưa có |
| Golden set | `data/golden_set/qa.jsonl` | Spec 09 | Chưa có |

**Checklist khi nhận dữ liệu mẫu từ BA:**
- Mỗi case có `metadata.json` với `data_classification` là `synthetic` hoặc `public`, và có `case_id`.
- `expected/work_profile.json` qua được `validate_against_contract`.
- Có đủ C1–C5 theo PRD §6. Riêng C2 phải thật sự không có track audio (`ffprobe` không thấy stream audio).
- Ground truth do BA viết và có người thứ hai kiểm tra, không chép từ output của model.

**Checklist golden set:**
- Có ≥ 30 câu, đúng phân bố how 10 / why 6 / exception 5 / relational 5 / out_of_scope 4.
- Mỗi `expected_citations` trỏ tới một `profile_id` sẽ ở trạng thái `approved` sau `review_decisions.json`.
- Câu `out_of_scope` phải thật sự nằm ngoài dữ liệu.
- Validator (spec 09 AC-01) chạy không lỗi.

## 6. Ma trận phủ Acceptance Criteria (04/10/2026)

| Spec | AC | Test tự động trên `main` | Trên nhánh chờ merge | Chưa có test | Kiểm thủ công |
|---|---|---|---|---|---|
| 01 | 01–11 | 03–11 | — | — | AC-01 (clone mới, CI), AC-02 (`make up`) |
| 02 | 01–06 | — | 01–06, cùng các AC mới đến 16 trong bản spec 02 cập nhật trên nhánh | — | — |
| 03 | 01–08 | — | — | **01–08** | — |
| 04 | 01–19 | 01–13, 16–19; AC-14 trong `tests/infra/test_compose.py` | — | — | AC-15 (GPU) |
| 05 | 01–11 | 10, 11 theo tên; 01, 03, 05, 06, 09 bằng test đặt tên mô tả | — | AC-02 (nạp lại không đổi số node/cạnh) và AC-07 (câu không liên quan thì không chọn template) chưa có test khẳng định trực tiếp; AC-08 luôn skip | AC-08 trên Neo4j (§4.2) |
| 06 | 01–08 | 04 (lọc dữ liệu mật ở LLM provider) | 01–08 | — | — |
| 07 | 01–06 | AC-06 phủ một phần (`test_committed_sigma_fixture_is_case_and_time_linkable`) | — | **01–05** | — |
| 08 | 01–08 | 01, 02, 03, 04, 06 | — | AC-05 (job lỗi trả `failed`) | AC-07 (`make demo`), AC-08 (UI) |
| 09 | 01–07 | — | 01–07 | — | — |

**Quy ước truy vết.** Tên `test_ac_xx` không chứa số spec, nên `test_ac_04` xuất hiện ở cả spec 01, 06
và 08. Hiện phải truy theo đường dẫn file. Đề xuất: mọi test AC mới có docstring `"""Spec NN AC-xx."""`.
Các test đặt tên mô tả nhưng đang phủ AC (chủ yếu ở spec 05) cũng nên được thêm docstring như vậy.

## 7. Test case thủ công và E2E

Ưu tiên: **P1** phải pass mới được nộp; **P2** nên pass, nếu fail thì ghi vào phần "Hạn chế" của báo cáo.
Ghi kết quả từng lượt chạy vào issue hoặc PR, kèm commit hash.

### 7.1 Luồng chính (PRD §11)

| ID | Truy vết | Bước | Kết quả mong đợi | Ưu tiên |
|---|---|---|---|---|
| E2E-01 | PRD-AC-01, spec 08 AC-07, NFR-05 | Clone mới, không có `.env`; pull image docker trước rồi ngắt mạng; chạy `KNOWHOW_DEMO_OFFLINE=1 make demo` | Exit 0, toàn luồng ≤ 5 phút, không có lời gọi ra ngoài | P1 |
| E2E-02 | PRD-AC-08 | Lấy case C1: video → `segment_id` (`VID-…#sNN`) → `evidence.segment_ids` của profile → citation trong câu trả lời → bấm mở nguồn | Mỗi mắt xích trỏ đúng mắt xích kế tiếp; clip mở đúng `t_start` | P1 |
| E2E-03 | US-04, PRD-AC-04 | Hỏi "Bước 3 làm thế nào?" | Có ≥ 1 citation; mỗi marker `[n]` có citation tương ứng; citation trỏ tới profile `approved` | P1 |
| E2E-04 | US-05, BR-02 | Hỏi "Vì sao…?" cho một bước có `reason` đã duyệt, rồi cho một bước có `reason = null` | Bước thứ nhất: trả đúng `reason` kèm citation. Bước thứ hai: không bịa lý do (bỏ phần lý do, hoặc từ chối kèm gợi ý chuyên gia) | P1 |
| E2E-05 | US-06, BR-05, NFR-07 | Hỏi câu ngoài phạm vi, ví dụ "Lịch nghỉ lễ tháng sau thế nào?" | `refused = true`, có gợi ý người cần hỏi khi process có chuyên gia | P1 |
| E2E-06 | PRD-AC-03, BR-01 | Reject 1 profile, để 1 profile ở `draft`; hỏi câu khớp đúng nội dung của hai profile đó | Hai profile này không xuất hiện trong citation; `knowhow kg stats` không tăng | P1 |
| E2E-07 | Spec 08 AC-01 | Sửa một profile đã `approved` | `version` + 1, `status = in_review`; trong lúc chưa duyệt lại, assistant vẫn trích bản cũ | P1 |
| E2E-08 | PRD-AC-02, case C2 | Chạy `describe` trên video câm | Mọi profile có `reason = null` và `reason_source = null` | P1 |
| E2E-09 | PRD-FR-03, spec 04 AC-08/09 | Case C1 có lời chuyên gia → `knowhow vlm propose-reasons` | `reason` khớp nguyên ý phát ngôn, `reason_source = expert_verbal`, `status = in_review`; câu không có trong transcript thì `reason` giữ null | P1 (sau khi có spec 03) |
| E2E-10 | PRD-FR-09, spec 06 AC-05/07 | RCA với lot mock có defect `D-03` | ≤ 3 giả thuyết; giả thuyết `high`/`medium` có evidence; `five_why` có 3–5 bước, bước không có căn cứ ghi `verified = false`; có disclaimer | P2 |
| E2E-11 | Spec 08 AC-06, spec 06 AC-06 | RCA với `lot_id` không tồn tại | API trả 404; UI báo lỗi bằng tiếng Việt | P2 |
| E2E-12 | Case C3 | Chạy `describe` trên case có ngoại lệ | `exceptions` có đủ `case` và `handling` | P2 |
| E2E-13 | Case C4, C5 | Chạy trên case mơ hồ hoặc mâu thuẫn | `confidence` thấp, profile nằm trong hàng đợi duyệt, không có gì tự publish | P2 |

### 7.2 Evaluation

| ID | Truy vết | Bước | Kết quả mong đợi | Ưu tiên |
|---|---|---|---|---|
| EVAL-01 | PRD-AC-06, NFR-04, spec 09 FR-04/05 | `knowhow eval ragas` rồi `knowhow eval report` | `usefulness_report.md` có: bảng chỉ số với cột "Đạt ngưỡng" ✅/❌, 5 câu tệ nhất, bảng "Profile cần xem lại", phần Hạn chế và thiết kế pilot. `summary.json` có `run_id`, thời điểm, model, commit hash | P1 |
| EVAL-02 | Spec 09 FR-02 | Kiểm judge của lượt chạy dùng cho báo cáo nộp | Judge là model mạnh (không phải model khoảng 8B) và được ghi trong báo cáo | P1 |
| EVAL-03 | BRD §11 | Đối chiếu từng con số trên slide với `summary.json` | Mọi số khớp một `run_id` cụ thể; chỉ số pilot (nhóm C) chỉ trình bày thiết kế, không có số | P1 |
| EVAL-04 | Spec 09 nhóm A | `knowhow eval review-stats` | Có tỷ lệ approve không sửa / approve sau sửa / reject; `reason_coverage.synthetic ≥ 0.6` | P2 |
| EVAL-05 | Spec 04 AC-07 | `knowhow vlm sweep` trên video LASI | CSV đủ cột; so với mốc trong `docs/reports/c2-vlm-smoke-and-fps-sweep.md`, sụt rõ rệt thì mở lỗi | P2 |

### 7.3 Bảo mật và dữ liệu (tất cả P1)

| ID | Truy vết | Bước | Kết quả mong đợi |
|---|---|---|---|
| SEC-01 | PRD-AC-05, BR-04, spec 04 AC-03 | Đặt `KNOWHOW_VLM_PROVIDER=openrouter` (key giả), chạy `knowhow vlm describe --video <clip> --classification factory_confidential` | `ConfidentialDataError` trước khi đọc file; không có request nào đi ra |
| SEC-02 | Spec 04 AC-13 | `local_openai` với `KNOWHOW_VLM_BASE_URL` trỏ tới host public; sau đó trỏ tới `localhost` hoặc IP LAN | Host public bị coi là cloud và dữ liệu mật bị chặn; localhost/LAN được coi là local |
| SEC-03 | Spec 06 AC-04 | LLM cloud, context chứa một passage `factory_confidential` | Passage đó không có trong prompt gửi đi |
| SEC-04 | Spec 04 AC-16/17 | Gửi prompt có số điện thoại và khung hình có mặt người tới provider cloud | Prompt đã che (`[PHONE_1]`), mặt bị làm mờ, audit chỉ ghi số lượng; thiếu model làm mờ thì từ chối gửi |
| SEC-05 | Spec 08 AC-04 | `curl -i http://127.0.0.1:8000/media/../../etc/passwd`, sau đó thử bản mã hóa `%2e%2e%2f` | 400 hoặc 404, không trả nội dung file |
| SEC-06 | Spec 01 AC-06, constitution Điều 2 | Sau một lượt demo, chạy `git status` | Không có video/audio ngoài `data/samples/`, không có `.env`, không có gì từ `data/work/` |
| SEC-07 | Spec 04 FR-09, constitution Điều 6 | Chạy với key sai hoặc URL có basic-auth | Thông báo lỗi và log không in ra key hay mật khẩu |
| SEC-08 | Spec 08 FR-05 | Gọi API từ một origin khác origin đã cấu hình | Trình duyệt chặn CORS |

### 7.4 UI tablet

Viewport cần thử: 1024×768 và 768×1024 (Chrome DevTools); thêm một máy tablet thật nếu có.

| ID | Truy vết | Kiểm | Kết quả mong đợi | Ưu tiên |
|---|---|---|---|---|
| UI-01 | NFR-06 | Cỡ chữ, nút bấm | Chữ ≥ 16px; nút đủ lớn để bấm bằng ngón tay (đề xuất ≥ 44px) | P1 |
| UI-02 | NFR-06, CLAUDE.md | Toàn bộ text hiển thị | Tiếng Việt. **Lỗi đã biết**, xem §11 | P1 |
| UI-03 | Spec 08 AC-08 | Nhập `reason` nhưng không chọn `reason_source` | Nút Duyệt bị vô hiệu và có thông báo (hiện đã đúng hành vi, nhưng thông báo là tiếng Anh) | P1 |
| UI-04 | PRD §10 Screen 1 | Màn duyệt | Hiện 3 keyframe, clip, step, hand_action, key_point, reason + nguồn, exceptions, pass_criteria, evidence | P1 |
| UI-05 | Spec 08 AC-03, PRD-FR-05 | Reject không nhập comment | Bị chặn; chọn được error_tags | P1 |
| UI-06 | PRD-AC-07 | Mở một profile đã `approved` | Thấy người duyệt và thời điểm duyệt | P1 |
| UI-07 | PRD §10 Screen 2 | Bấm vào citation | Video tua tới `t_start`; tài liệu hiện đoạn trích | P1 |
| UI-08 | PRD §10 Screen 3 | Màn RCA | Phân biệt rõ bước 5-Why `verified` và chưa xác minh; luôn có disclaimer | P2 |
| UI-09 | — | Tắt API rồi thao tác trên UI | Thông báo lỗi thân thiện bằng tiếng Việt, không lộ stack trace | P2 |
| UI-10 | — | Tải lại trang giữa lúc đang duyệt | Kết quả duyệt đã lưu không bị mất | P2 |

### 7.5 Độ bền

| ID | Truy vết | Bước | Kết quả mong đợi | Ưu tiên |
|---|---|---|---|---|
| RES-01 | Spec 08 AC-05 | VLM báo lỗi khi đang xử lý video | `GET /jobs/{id}` trả `failed` kèm message; server vẫn phục vụ request khác | P1 |
| RES-02 | Spec 04 AC-06 | Một segment trả JSON lỗi 2 lần liên tiếp | Segment đó vào `failed_segments.json`; các segment khác vẫn có kết quả | P2 |
| RES-03 | Spec 05 AC-10 | Tắt router LLM | Retrieval vẫn trả kết quả vector + expansion | P2 |
| RES-04 | — | Tắt Neo4j hoặc Postgres rồi bấm approve | Lỗi rõ ràng; profile không bị ghi `approved` nửa vời | P2 |
| RES-05 | — | Chạy `knowhow vlm ping` khi Ollama/vLLM chưa bật | Báo lỗi kết nối rõ ràng, không treo | P2 |

## 8. Hồi quy khi merge hai nhánh đang chờ

**Bước 1 — `phuc-nguyen/agents-eval-on-main`** (merge sạch):
1. `uv sync --all-extras && make check`. Kỳ vọng 0 fail, số test ≥ 274 cộng phần test mới.
2. `knowhow agent ask --help`, `knowhow agent rca --help`, `knowhow eval --help` đều có lệnh con.
3. Gọi `/assistant/ask`: câu trả lời **không còn** là câu mock viết cứng ("…cầm hai mép carton để tránh
   rách cạnh…"); citation trỏ tới profile hoặc chunk có thật trong KB.
4. Khi từ chối: `suggested_expert` của API có giá trị lấy từ `suggested_contact` của agent
   (`mentormind/agents/api.py:67`).

**Bước 2 — `viethoang/ingext-index-trungntresolve`** (5 conflict):
1. Chốt **một** bản pgvector trước khi gỡ conflict (xem [10-work-left.md](10-work-left.md) §3).
2. Sau khi merge: `grep -rn "store.pgvector\b\|store.embedding\b\|pgvector_store\|store.embedder" mentormind tests`.
   Chỉ được còn import tới bản được giữ.
3. `make check`, rồi chạy integration ở §4.2 cùng test pgvector. Không được có skip ngoài ý muốn.
4. `KNOWHOW_VECTOR_BACKEND=memory` vẫn chạy được mà không cần docker (spec 01 AC-08).
5. Chạy `knowhow ingest run data/samples/docs --classification synthetic` hai lần. Số dòng JSONL và
   `chunk_id` không đổi (spec 02 AC-04).

**Bước 3 — sau cả hai:** chạy `make demo` và ghi lại các mục preflight còn `[ ]`.

## 9. Tiêu chí vào/ra cho bản nộp 12/10

**Điều kiện bắt đầu test hệ thống:**
- Hai nhánh đã merge, preflight `make demo` xanh.
- Có ít nhất case C1, C2 và golden set.

**Điều kiện được phép nộp:**
- `make check` và CI xanh trên commit nộp.
- Integration (§4.2) đã chạy ít nhất một lần trên commit nộp, 0 fail, kết quả đính kèm PR.
- E2E-01 pass 3 lần liên tiếp trên máy sạch, mỗi lần ≤ 5 phút.
- Mọi test case P1 ở §7 pass. Không còn lỗi S1 hoặc S2 đang mở.
- Báo cáo evaluation sinh từ chính commit nộp. Chỉ số không đạt ngưỡng được ghi trung thực, không chỉnh
  tay, và có giải thích trong phần Hạn chế.
- `git status` sạch, không có file dữ liệu bị cấm.

## 10. Báo lỗi

| Mức | Định nghĩa | Ví dụ |
|---|---|---|
| S1 Chặn | Vi phạm constitution, mất dữ liệu duyệt, hoặc `make demo` hỏng | Dữ liệu mật đi ra cloud; `reason` do AI tự điền; profile chưa duyệt xuất hiện trong câu trả lời; câu trả lời không có citation mà không từ chối |
| S2 Nặng | Luồng chính sai, không chấp nhận được khi demo | Citation trỏ sai nguồn; RCA lỗi; duyệt không lưu được |
| S3 Vừa | Sai hiển thị hoặc trải nghiệm, luồng vẫn đi được | Text tiếng Anh cho người dùng; thông báo lỗi khó hiểu |
| S4 Nhẹ | Thẩm mỹ, chính tả | Lệch căn lề, sai dấu |

**Mẫu issue (GitHub):**

```
Tiêu đề: [S2][spec 06 AC-02] Câu trả lời có marker [3] nhưng chỉ có 2 citation
Môi trường: commit <hash>, macOS/Linux, VLM=<provider/model>, LLM=<provider/model>, vector=<memory|pgvector>
Dữ liệu: case_id=CASE-PACK01-001, data_classification=synthetic
Bước tái hiện: 1. … 2. … 3. …
Mong đợi: <trích nguyên văn AC/BR/FR>
Thực tế: …
Bằng chứng: log, ảnh chụp, file trong data/work/… (đã che key; không đính kèm dữ liệu mật)
```

## 11. Lỗi đã biết, rủi ro và khoảng trống

**Lỗi đã biết (04/10):**
- **[S3] UI còn nhiều text tiếng Anh**, vi phạm NFR-06 và CLAUDE.md. Ví dụ:
  `ReviewProfilesTab.tsx:121` ("AC-08 VIOLATION: reason_source must be set before approving."),
  `:268`, `:451–452`, `:473`, `:578`; `AssistantTab.tsx:84`, `:104`, `:144`, `:289`; `RcaTab.tsx:87`.
  Nên nâng lên S2 nếu demo trước người dùng nhà máy.
- **[S2] `/assistant/ask` và `/rca/investigate` trên `main` trả câu trả lời mock viết cứng.** Không được dùng
  để chứng minh PRD-AC-04 cho tới khi nhánh agents được merge.
- **[S4] `mentormind/core/schemas.py` là file chết**, bị package `core/schemas/` che mất.

**Rủi ro và khoảng trống:**
- Spec 03 chưa có nên E2E-01, E2E-02, E2E-08 và E2E-09 bị chặn. Trong lúc chờ, kiểm phần còn lại của
  luồng bằng profile seed (`mentormind/knowledge_base/store/seed_demo.py`).
- CI không chạy integration, nên lỗi Neo4j/pgvector chỉ lộ ra khi chạy tay theo §4.2.
- Frontend không có test tự động; toàn bộ UI dựa vào §7.4. Sau 12/10 nên thêm ít nhất một smoke test
  Playwright cho luồng duyệt.
- Judge Ragas cỡ khoảng 8B chấm không ổn định (spec 09 FR-02). Nếu hai lượt chạy cùng cấu hình lệch nhau
  nhiều, ghi cả hai vào báo cáo.
- Chưa có test cho spec 07 AC-01…05, spec 08 AC-05, và spec 05 AC-02/AC-07 (xem §6).

## Changelog
- v1.0 (04/10/2026): bản đầu, dựa trên `main` @ `da08a2e` và hai nhánh `phuc-nguyen/agents-eval-on-main`,
  `viethoang/ingext-index-trungntresolve`.
