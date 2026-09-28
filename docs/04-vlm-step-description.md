# 04 — VLM Step Description

**Owner:** Phúc · **Tasks Excel:** S0-6, S1-3, S1-4, S2-6 (phần gắn reason)

## 1. Mục tiêu
Từ các `Segment` (spec 03) sinh ra danh sách `WorkProfile` ở trạng thái `draft`, hợp lệ theo contract, không chứa `reason` bịa. Đổi provider (API cloud ↔ self-host) chỉ bằng config.

## 2. Provider abstraction — `processing.vlm.providers` (registry, theo pattern omnia)
Bố cục package `processing/vlm/`: `providers/` (`base`, `models`, `registry`, `factory`, `catalog`, `backends/{openai_compat,fake}`), `frames/` (`sampler`, `dedup`), `guard/face_blur`, `passes/` (`describe` = lượt A, `postprocess`, `models`, `prompting`), `sweep/` (`truth`, `matching`, `metrics`, `runner`, `report`, `windows`), `cli/` (`diagnostics`, `sweep`), `prompts/*.md`.

Phần dùng chung mọi loại provider nằm ở `core.providers` (spec 06 dùng lại cho LLM): `ProviderBase`,
`ProviderConfig`, `ProviderRegistry` (tên → class), `HttpClient` + retry (FR-07), bảng endpoint
OpenAI-compatible `OPENAI_COMPAT_ENDPOINTS`, `parse_json_object`.
```python
class VLMProvider(ProviderBase):          # ABC; subclass + @register_vlm("ten") là đủ
    name: str                             # tên registry, ghi vào model_info.provider
    model: str
    is_cloud: bool
    def generate(self, frames, prompt, *, classification, json_schema=None, system=None,
                 temperature=None, max_tokens=None) -> VLMResponse: ...   # text + usage + latency
    def generate_json(self, frames: list[Path], prompt: str, json_schema: dict, *,
                      classification, ...) -> dict: ...
    def _complete(self, images, prompt, ...) -> tuple[str, TokenUsage | None]: ...  # subclass viết

@register_vlm("local_openai", "qwen_api", "openrouter", "siliconflow", "openai_compatible")
class OpenAICompatVLM:   # 1 class cho mọi endpoint /chat/completions; vendor = 1 dòng trong bảng endpoint
@register_vlm("fake")
class FakeVLM:           # test: trả JSON cố định từ tests/fixtures/vlm/*.json, ghi lại mọi lời gọi
class GeminiVLM:         # Could — chỉ khi còn thời gian
```
- `generate` là template method: `DataGuard.check(classification, self)` chạy **trước** khi đọc file ảnh
  nên không provider nào quên được guard (AC-03).
- `is_cloud`: vendor cloud luôn `True`; `local_openai`/`openai_compatible` suy ra từ `base_url`
  (loopback, IP private, CGNAT/Tailscale, hostname LAN → local; còn lại → cloud) — AC-13.
- JSON mode theo endpoint (`KNOWHOW_VLM_JSON_MODE=auto`): `local_openai`, `openrouter` → `json_schema`;
  `qwen_api`, `siliconflow` → `json_object`. Luôn parse lại bằng `parse_json_object` (chịu được markdown fence).
- Key lấy theo tên biến của vendor (`OPENROUTER_API_KEY`...) từ môi trường rồi `.env`;
  `KNOWHOW_VLM_API_KEY` (khác rỗng) thắng tất cả. Hướng dẫn: `.secrets/README.md`.
- **Chế độ gửi mặc định: `frames`** — lấy mẫu khung hình từ `clip_path` theo `KNOWHOW_VLM_FPS`, gửi dạng nhiều ảnh base64 trong một message. Cách này chạy được trên mọi endpoint OpenAI-compatible, kể cả vLLM self-host với Qwen3-VL-8B sau này.
- Ảnh gửi đi resize cạnh dài 448px (ưu tiên độ dày thời gian hơn độ nét).
- **Lấy mẫu thích ứng** theo `Segment.motion_score` (spec 03): `≥ 0.6` → 8 fps; `< 0.3` → 2 fps; còn lại hoặc `None` → `KNOWHOW_VLM_FPS`.
- **Bỏ khung gần trùng**: perceptual hash (dHash 64-bit), bỏ khung có khoảng cách Hamming ≤ 4 so với khung giữ lại liền trước.
- **Trần số ảnh**: tối đa `KNOWHOW_VLM_MAX_FRAMES` (mặc định 48) ảnh/lời gọi; vượt trần → lấy mẫu đều lại cho vừa trần. `model_info.fps` ghi fps thực tế đã dùng.
- `get_vlm_provider(settings) -> VLMProvider` là factory duy nhất; code nghiệp vụ không import class cụ thể.
- Mọi lời gọi đi qua `DataGuard.check(classification, provider)` (spec 01, FR-09) **trước** khi đọc file.

## 3. Pipeline 3 lượt — `processing.vlm.pipeline.describe_video(video_id) -> list[WorkProfile]`

**Lượt A — mô tả từng đoạn.** Với mỗi `Segment`, gọi VLM với prompt `prompts/pass_a_describe.md`, output theo schema:
```json
{"steps": [{"step": "str", "hand_action": "str", "objects": ["str"],
            "key_point_observed": "str|null", "t_start_rel": 0.0, "t_end_rel": 0.0,
            "confidence": 0.0}]}
```
Một đoạn có thể có 0..n bước.

**Lượt B — tự nhất quán.** Chạy lượt A thêm 1 lần (tổng k=2, `temperature=0.2`). Chỉ giữ bước xuất hiện ở cả hai lần (so khớp: `rapidfuzz.token_set_ratio(step) ≥ 70` và overlap thời gian > 0). `confidence` cuối = trung bình hai lần × tỷ lệ khớp.

**Lượt C — tổng hợp.** Gọi LLM text (không cần ảnh) với prompt `prompts/pass_c_merge.md`: gộp bước trùng giữa các đoạn kề nhau, sắp `step_order` theo thời gian, chuẩn hóa tên bước (động từ ở đầu). Không được thêm bước mới không có trong input.

**Hậu xử lý bắt buộc**
- Ép `reason = None`, `reason_source = None`, `generated_by = "vlm"`, `status = "draft"`.
- Gán `evidence` = video_id, t_start/t_end tuyệt đối, `segment_ids` (mọi đoạn mà bước gộp từ đó), keyframes của đoạn, `transcript_excerpt` từ `align_transcript` (spec 03) nếu có.
- Gán `model_info` = provider, model, fps.
- Validate bằng `validate_against_contract`. JSON lỗi → gọi lại 1 lần với prompt sửa (`prompts/repair_json.md`); vẫn lỗi → ghi segment vào `failed_segments.json`, không crash.

## 4. Prompt lượt A (nội dung chuẩn, lưu tại `processing/vlm/prompts/pass_a_describe.md`)
```
Bạn là kỹ sư IE đang ghi lại thao tác trong công đoạn {process_id} (đóng gói, xếp sản phẩm/linh kiện vào hộp).
Các ảnh sau là khung hình liên tiếp của một đoạn video dài {duration}s, lấy mẫu {fps} khung/giây, theo đúng thứ tự thời gian.
Mốc thời gian (giây, tính từ đầu đoạn) của từng ảnh: {timestamps}.

Bước 1 — "scene": mô tả ngắn (1-2 câu) những gì thấy trong các ảnh: ai hoặc máy/robot nào, đang làm gì.
Bước 2 — "steps": liệt kê CÁC BƯỚC THAO TÁC QUAN SÁT ĐƯỢC của người (công nhân, kỹ sư) hoặc của máy/robot.
Quy tắc:
- Chỉ mô tả điều nhìn thấy trong ảnh. Không suy đoán lý do, không thêm bước "thường có" trong SOP.
- Mỗi bước: động từ ở đầu, ngắn gọn (VD "Đặt linh kiện A vào ngăn trái").
- Một thao tác lặp lại nhiều lần chỉ ghi MỘT bước; tối đa 6 bước cho cả đoạn.
- hand_action: ai/tay nào, động tác gì (nhặt, xoay, ấn, đặt nghiêng...); objects: vật được thao tác.
- key_point_observed: chi tiết kỹ thuật NHÌN THẤY được (hướng, vị trí, thứ tự), null nếu không có.
- t_start_rel, t_end_rel: giây tính từ đầu đoạn (0 đến {duration}), dựa vào mốc thời gian của ảnh.
- Nếu không chắc, hạ confidence (< 0.5) thay vì bỏ qua hoặc bịa.
- Cảnh chỉ có người nói chuyện, logo, chữ hoặc bảng số liệu thì không phải thao tác: "steps" rỗng.
Trả về DUY NHẤT một đối tượng JSON với hai khóa "scene" và "steps", không markdown, không giải thích.
```
Schema output thêm khóa **`scene`** (bắt buộc, đứng trước `steps`): `{"scene": "str", "steps": [...]}`.
*Vì sao (thí nghiệm 28/9, Qwen3-VL-8B tự host, video demo LASI 20 đoạn × 4 fps):* prompt v1.0 ở trên
trả `{"steps": []}` cho **mọi** đoạn, kể cả có/không `json_schema`; bỏ câu "Không có thao tác nào →
trả {"steps": []}" hoặc dòng JSON mẫu vẫn rỗng; chỉ khi bắt model **mô tả cảnh trước rồi mới trích
bước** thì mới ra bước đúng giờ (robot đặt vào hộp 74.8–79.8 s vs truth 72.6–79.7 s). Thêm dòng mốc
thời gian từng ảnh vì bỏ khung trùng làm khoảng cách giữa các ảnh không còn đều.

## 5. Gắn `reason` từ lời chuyên gia (Should, task S2-6)
`knowhow vlm propose-reasons <video_id>`: với mỗi profile có `transcript_excerpt`, gọi LLM text trích **nguyên ý chuyên gia nói** về lý do (không diễn giải thêm). Nếu tìm thấy → điền `reason`, `reason_source = "expert_verbal"`, chuyển `status = "in_review"`. Không tìm thấy → giữ nguyên.

**Hậu kiểm trích dẫn**: `reason` do LLM trả về phải khớp nguyên văn với `transcript_excerpt` (`rapidfuzz.fuzz.partial_ratio ≥ 85`, so trên chuỗi đã lowercase). Không khớp → coi như LLM đã diễn giải: loại, giữ `reason=None`, ghi log. Mục đích: chặn vi phạm Constitution Điều 3 qua đường gián tiếp.

## 6. Quét fps — `knowhow vlm sweep`
```
knowhow vlm sweep --video data/samples/video/pack_demo_01.mp4 \
  --fps 1,2,4,8 --truth data/golden_set/steps/pack_demo_01.json --out data/work/sweep.csv
```
- `truth` là danh sách bước do Đạt gán tay (`[{step, t_start, t_end, key_point?}]`); `key_point` là chi tiết kỹ thuật nhìn thấy được (hướng, góc, vị trí), tùy chọn. File truth có thể là danh sách đó hoặc một object `{"video": ..., "annotation": ..., "scenes": [...], "steps": [...]}`; mỗi bước có thể thêm `essential` (bước thuộc công đoạn chính, mặc định `true`). Mẫu: `data/video/groundtruth.json` (video LASI, 50 cảnh, 27 bước).
- Chưa có `segments.json` của spec 03 thì sweep tự cắt đoạn `fixed_window` 10 s (spec 03 FR-03 fallback, ffmpeg, cache tại `data/work/video/<video_id>/clips/`); có rồi thì truyền `--segments`. Sweep ép cùng một fps cho mọi đoạn (bỏ qua `motion_score`) để so sánh các mức fps.
- So khớp như lượt B. Chỉ số: `recall` (1 − tỷ lệ bỏ sót), `precision` (1 − tỷ lệ bịa), `order_accuracy` (Kendall tau chuẩn hóa), `key_point_recall` (tỷ lệ bước truth có `key_point` được khớp với `key_point_observed` của bước dự đoán tương ứng, `token_set_ratio ≥ 70`; không bước truth nào có `key_point` → để trống), `tokens_used`, `latency_s`.
- Chỉ số phụ (cột thêm, không thay chỉ số chính): `recall_essential` (chỉ bước `essential`), `recall_time_only` (bước truth có ít nhất một dự đoán trùng thời gian, bất kể câu chữ — đo độ phủ khi luật khớp chữ ≥ 70 quá khắt khe với tiếng Việt tự do), `fps_effective`, `predicted`, `failed_segments`.
- Xuất CSV + in bảng markdown để dán vào slide; chi tiết mỗi fps (raw answer, `predictions.json`, `profiles_draft.json`) tại `data/work/vlm/<video_id>/sweep-<provider>/fps<N>/`.

## 7. Functional Requirements
- **FR-01** Factory `get_vlm_provider(settings)` theo `KNOWHOW_VLM_PROVIDER` = một tên trong registry:
  `local_openai` (mặc định, server tự host FR-08), `qwen_api` (DashScope), `openrouter`, `siliconflow`,
  `openai_compatible` (server bất kỳ, cần `KNOWHOW_VLM_BASE_URL`), `fake`; `gemini` là Could. Tên lạ →
  `ProviderConfigError` liệt kê các tên có sẵn. `knowhow vlm providers` in registry + trạng thái key.
- **FR-01b** `KNOWHOW_VLM_EXTRA_BODY` (JSON) gộp vào mọi request body cho tham số sampling riêng của vendor
  (vd. `{"presence_penalty": 1.5}`); không bao giờ đè `model`, `messages` hay tham số của chính lời gọi.
- **FR-02** DataGuard chặn trước mọi lời gọi.
- **FR-02b** Frame sampler thích ứng + bỏ khung trùng + trần số ảnh như mục 2.
- **FR-02c** Mọi lời gọi tới provider **cloud** đi qua outbound guard (spec 01 FR-09b, port từ bankassist-mcp): che PII trong prompt/system (`[TYPE_n]`, hoàn nguyên trong câu trả lời), LeakGuard quét lại và **từ chối** nếu còn sót (kể cả khi `KNOWHOW_GUARD_MASK_TEXT=false`), **làm mờ khuôn mặt** trong khung hình (YuNet, model tải một lần, SHA-256 ghim; không tải/không nạp được → từ chối gửi), ghi audit `data/work/audit/outbound-YYYYMMDD.jsonl` (chỉ số đếm, không giá trị). Provider tự host nhận dữ liệu nguyên bản.
- **FR-03** Pipeline 3 lượt như mục 3.
- **FR-04** Hậu xử lý + validate như mục 3.
- **FR-05** CLI: `knowhow vlm describe <video_id>`, `knowhow vlm propose-reasons <video_id>`, `knowhow vlm sweep ...`; chẩn đoán: `knowhow vlm providers` (registry + key) và `knowhow vlm ping [--provider] [--video --classification]` (clip tổng hợp phụ thuộc thứ tự khung, hoặc video thật; `--classification` mặc định `factory_confidential` để fail-closed).
- **FR-06** Kết quả lưu vào profile store (spec 08) với `status=draft`; lưu raw response mỗi lượt tại `data/work/vlm/<video_id>/` để debug.
- **FR-07** Retry mạng: tối đa 3 lần, backoff mũ; timeout 90s/lời gọi.
- **FR-08** Server tự host tại `3rdparty/vlm_server/` — uv project riêng (vLLM 0.16.0 + torch 2.9.1 cu126,
  vì driver máy dev là CUDA 12.6), API OpenAI-compatible, phục vụ `Qwen/Qwen3-VL-8B-Instruct` BF16 trên
  **đúng 1 GPU** (`VLM_SERVER_GPU` = một index hoặc `auto`; `CUDA_VISIBLE_DEVICES` một index;
  `--tensor-parallel-size 1`). Mặc định nghe `127.0.0.1:8100` (8000 là backend spec 08), máy khác vào
  qua SSH tunnel. Token tùy chọn `VLM_SERVER_API_KEY` truyền qua biến môi trường, không qua argv. Code
  chính chỉ gọi HTTP qua provider `local_openai`, không import server.
- **FR-09b** URL theo tài khoản: endpoint có thể khai biến secret cho base URL; `qwen_api` đọc `DASHSCOPE_BASE_URL` (key Singapore mới `sk-ws...` đi kèm host `{WorkspaceId}.ap-southeast-1.maas.aliyuncs.com`), không có thì dùng `dashscope-intl.aliyuncs.com`.
- **FR-09** Secret nằm trong `.env` ở gốc repo (bị `.gitignore` chặn; chỉ `.env.example` được commit;
  `.secrets/README.md` là hướng dẫn lấy key). Cloud provider thiếu key → lỗi nêu đúng tên biến và `.secrets/README.md`.

## 8. Acceptance Criteria
- **AC-01** Với `FakeVLM` + 3 segment fixture → ra WorkProfile hợp lệ contract, `step_order` liên tục từ 1.
- **AC-02** FakeVLM trả JSON có khóa `reason` → profile cuối vẫn `reason=None`.
- **AC-03** Video `factory_confidential` + provider cloud → raise `ConfidentialDataError`, không file nào được đọc.
- **AC-04** Lượt B: bước chỉ xuất hiện ở 1 trong 2 lần chạy bị loại.
- **AC-05** Lượt C không tạo bước không có trong input (test với fake LLM cố tình thêm bước → bị lọc bằng so khớp ngược).
- **AC-06** JSON lỗi 2 lần liên tiếp → segment vào `failed_segments.json`, pipeline vẫn trả kết quả cho các segment khác.
- **AC-07** `sweep` trên fixture ra CSV đủ cột `fps, recall, precision, order_accuracy, key_point_recall, tokens_used, latency_s`.
- **AC-08** `propose-reasons` chỉ điền `reason` khi transcript chứa phát ngôn; `reason_source="expert_verbal"`, `status="in_review"`.
- **AC-09** FakeLLM trả `reason` là câu diễn giải không có trong `transcript_excerpt` → profile giữ `reason=None`, `status` không đổi.
- **AC-10** Segment có `motion_score=0.8` → sampler dùng 8 fps; clip fixture gồm các khung giống hệt nhau → sau bỏ trùng còn 1 khung; clip dài cho ra > 48 khung → số ảnh gửi đi = 48.
- **AC-11** Thêm provider mới = 1 class + `@register_vlm("ten")`, dựng được bằng tên qua registry mà không sửa code nghiệp vụ; tên chưa đăng ký → `ProviderConfigError` liệt kê tên có sẵn.
- **AC-12** Provider cloud thiếu key → `ProviderConfigError` nêu tên biến (vd. `OPENROUTER_API_KEY`) và `.secrets/README.md`; key chỉ có trong `.env` vẫn được dùng; `KNOWHOW_VLM_API_KEY` khác rỗng thắng key của vendor, rỗng thì bị bỏ qua.
- **AC-13** `local_openai` trỏ `KNOWHOW_VLM_BASE_URL` tới host public → `is_cloud=True`, dữ liệu `factory_confidential` bị chặn.
- **AC-14** Launcher server: `VLM_SERVER_GPU="0,1"` bị từ chối; môi trường chạy vLLM có `CUDA_VISIBLE_DEVICES` đúng 1 index, lệnh có `--tensor-parallel-size 1`; token không xuất hiện trong argv.
- **AC-15** (thủ công, cần GPU) `make vlm-server` rồi `uv run knowhow vlm ping --frames 48` → `PASS` (model nhận ra hình vuông đỏ đi từ trái sang phải vào hộp).
- **AC-16** Provider cloud nhận prompt đã che PII (vd. số điện thoại → `[PHONE_1]`), câu trả lời được hoàn nguyên, audit ghi số lượng đã che; provider tự host nhận prompt nguyên bản; tắt che PII mà prompt còn PII → `SensitiveDataLeakError`, không có HTTP request nào.
- **AC-17** Khung hình gửi provider cloud bị làm mờ vùng mặt (vùng khác giữ nguyên), audit ghi `faces_blurred`; khung gửi provider tự host giữ nguyên byte; không có model làm mờ mặt → từ chối gửi (fail closed).

## 9. Tasks
- [x] T04-1 Provider protocol + `OpenAICompatVLM` + `FakeVLM` + factory + DataGuard (AC-03).
- [x] T04-2 Frame sampler từ clip (fps thích ứng, bỏ trùng, trần số ảnh, resize) (AC-10).
- [x] T04-3 Lượt A + prompt + validate + repair (AC-01, AC-02, AC-06). *(Nối vào profile store chờ spec 08; hiện ghi `profiles_draft.json`.)*
- [ ] T04-4 Lượt B tự nhất quán (AC-04).
- [ ] T04-5 Lượt C tổng hợp (AC-05).
- [x] T04-6 `sweep` + `key_point_recall` (AC-07).
- [ ] T04-7 `propose-reasons` + hậu kiểm trích dẫn (AC-08, AC-09).
- [x] T04-8 Registry provider dùng chung (`core.providers`) + cloud `openrouter`/`siliconflow` + key từ `.env` + `knowhow vlm providers|ping` (AC-11, AC-12, AC-13).
- [x] T04-9 Server tự host `3rdparty/vlm_server` (vLLM, Qwen3-VL-8B-Instruct, 1 GPU) + smoke test (AC-14, AC-15).
- [x] T04-10 Outbound guard cho VLM cloud: che PII + LeakGuard + làm mờ mặt + audit (AC-16, AC-17).

## Changelog
- v1.0 (23/9): khởi tạo.
- v1.1 (23/9): hậu xử lý gán `evidence.segment_ids` (contract WorkProfile thêm field).
- v1.2 (24/9): FR-02b lấy mẫu thích ứng theo `motion_score` + bỏ khung trùng + `KNOWHOW_VLM_MAX_FRAMES`; `sweep` thêm `key_point_recall`; hậu kiểm `reason` phải khớp transcript (AC-09, AC-10).
- v1.3 (27/9): đường dẫn module theo layout mới (bỏ `knowhow.`/`src/knowhow/`, xem spec 01 v1.3).
- v1.4 (28/9, Phúc): provider theo registry (`core.providers` + `@register_vlm`), thêm `openrouter`, `siliconflow`, `openai_compatible`; `generate` là template method chạy DataGuard trước khi đọc file; FR-01b `KNOWHOW_VLM_EXTRA_BODY`; FR-08 server tự host `3rdparty/vlm_server` trên 1 GPU; FR-09 secret trong `.secrets/`; AC-11..AC-15; T04-1, T04-2, T04-8, T04-9 xong. Đo trên A5000: 48 khung ≈ 5.5k token, 2.9–3.8 s. Lưu ý: Alibaba ngừng `qwen3-vl-8b-instruct` ngày 10/10/2026.
- v1.5 (28/9, Phúc): prompt lượt A thêm bước mô tả `scene` trước `steps` + mốc thời gian từng ảnh (§4, kèm số liệu thí nghiệm); FR-02c outbound guard cho cloud (che PII, LeakGuard, làm mờ mặt, audit) + AC-16, AC-17, T04-10; sweep nhận truth dạng object, fallback `fixed_window` khi chưa có spec 03, thêm cột phụ `recall_essential`/`recall_time_only`; T04-3, T04-6 xong; package `processing/vlm/` chia theo chức năng.
- v1.6 (28/9, Phúc): FR-09b `DASHSCOPE_BASE_URL` cho host workspace Singapore (tài liệu Alibaba 28/9).
- v1.7 (28/9, Phúc): FR-09 + AC-12 key đọc từ `.env` (không còn `.secrets/secrets.env`); `.secrets/README.md` chỉ là hướng dẫn lấy key.
- v1.8 (28/9, Phúc): lượt A nhận `objects` dạng chuỗi "a, b" (DashScope `json_object` không ép schema, gặp khi chạy cloud trên video LASI); AC-15 chạy thật trên MI250 (GCD 1, vLLM 0.23 ROCm): PASS.
