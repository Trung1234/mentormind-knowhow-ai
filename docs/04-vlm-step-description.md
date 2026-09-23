# 04 — VLM Step Description

**Owner:** Phúc · **Tasks Excel:** S0-6, S1-3, S1-4, S2-6 (phần gắn reason)

## 1. Mục tiêu
Từ các `Segment` (spec 03) sinh ra danh sách `WorkProfile` ở trạng thái `draft`, hợp lệ theo contract, không chứa `reason` bịa. Đổi provider (API cloud ↔ self-host) chỉ bằng config.

## 2. Provider abstraction — `knowhow.vlm.providers`
```python
class VLMProvider(Protocol):
    name: str
    model: str
    is_cloud: bool
    def generate_json(self, frames: list[Path], prompt: str, json_schema: dict) -> dict: ...

class OpenAICompatVLM:   # qwen_api (DashScope compatible mode), local_openai (vLLM self-host)
class GeminiVLM:         # Could — chỉ khi còn thời gian
class FakeVLM:           # test: trả JSON cố định từ tests/fixtures/vlm/*.json
```
- **Chế độ gửi mặc định: `frames`** — lấy mẫu khung hình từ `clip_path` theo `KNOWHOW_VLM_FPS`, gửi dạng nhiều ảnh base64 trong một message. Cách này chạy được trên mọi endpoint OpenAI-compatible, kể cả vLLM self-host với Qwen3-VL-8B sau này.
- Ảnh gửi đi resize cạnh dài 448px (ưu tiên độ dày thời gian hơn độ nét).
- `get_vlm_provider(settings) -> VLMProvider` là factory duy nhất; code nghiệp vụ không import class cụ thể.
- Mọi lời gọi đi qua `DataGuard.check(classification, provider)` (spec 01, FR-09) **trước** khi đọc file.

## 3. Pipeline 3 lượt — `knowhow.vlm.pipeline.describe_video(video_id) -> list[WorkProfile]`

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

## 4. Prompt lượt A (nội dung chuẩn, lưu tại `src/knowhow/vlm/prompts/pass_a_describe.md`)
```
Bạn là kỹ sư IE đang ghi lại thao tác của một công nhân lành nghề trong công đoạn {process_id}
(xếp linh kiện vào hộp). Các ảnh sau là khung hình liên tiếp của một đoạn video dài {duration}s,
lấy mẫu {fps} khung/giây, theo đúng thứ tự thời gian.

Nhiệm vụ: liệt kê CÁC BƯỚC THAO TÁC QUAN SÁT ĐƯỢC.
Quy tắc:
- Chỉ mô tả điều nhìn thấy trong ảnh. Không suy đoán lý do, không thêm bước "thường có" trong SOP.
- Mỗi bước: động từ ở đầu, ngắn gọn (VD "Đặt linh kiện A vào ngăn trái").
- hand_action: tay nào, động tác gì (nhặt, xoay, ấn, đặt nghiêng...).
- key_point_observed: chi tiết kỹ thuật NHÌN THẤY được (hướng, vị trí, thứ tự), null nếu không có.
- Nếu không chắc, hạ confidence (< 0.5) thay vì bỏ qua hoặc bịa.
- Không có thao tác nào → trả {"steps": []}.
Trả về DUY NHẤT JSON đúng schema, không markdown, không giải thích.
```

## 5. Gắn `reason` từ lời chuyên gia (Should, task S2-6)
`knowhow vlm propose-reasons <video_id>`: với mỗi profile có `transcript_excerpt`, gọi LLM text trích **nguyên ý chuyên gia nói** về lý do (không diễn giải thêm). Nếu tìm thấy → điền `reason`, `reason_source = "expert_verbal"`, chuyển `status = "in_review"`. Không tìm thấy → giữ nguyên.

## 6. Quét fps — `knowhow vlm sweep`
```
knowhow vlm sweep --video data/samples/video/pack_demo_01.mp4 \
  --fps 1,2,4,8 --truth data/golden_set/steps/pack_demo_01.json --out data/work/sweep.csv
```
- `truth` là danh sách bước do Đạt gán tay (`[{step, t_start, t_end}]`).
- So khớp như lượt B. Chỉ số: `recall` (1 − tỷ lệ bỏ sót), `precision` (1 − tỷ lệ bịa), `order_accuracy` (Kendall tau chuẩn hóa), `tokens_used`, `latency_s`.
- Xuất CSV + in bảng markdown để dán vào slide.

## 7. Functional Requirements
- **FR-01** Factory provider theo `KNOWHOW_VLM_PROVIDER` ∈ {`qwen_api`, `local_openai`, `gemini`, `fake`}.
- **FR-02** DataGuard chặn trước mọi lời gọi.
- **FR-03** Pipeline 3 lượt như mục 3.
- **FR-04** Hậu xử lý + validate như mục 3.
- **FR-05** CLI: `knowhow vlm describe <video_id>`, `knowhow vlm propose-reasons <video_id>`, `knowhow vlm sweep ...`.
- **FR-06** Kết quả lưu vào profile store (spec 08) với `status=draft`; lưu raw response mỗi lượt tại `data/work/vlm/<video_id>/` để debug.
- **FR-07** Retry mạng: tối đa 3 lần, backoff mũ; timeout 90s/lời gọi.

## 8. Acceptance Criteria
- **AC-01** Với `FakeVLM` + 3 segment fixture → ra WorkProfile hợp lệ contract, `step_order` liên tục từ 1.
- **AC-02** FakeVLM trả JSON có khóa `reason` → profile cuối vẫn `reason=None`.
- **AC-03** Video `factory_confidential` + provider cloud → raise `ConfidentialDataError`, không file nào được đọc.
- **AC-04** Lượt B: bước chỉ xuất hiện ở 1 trong 2 lần chạy bị loại.
- **AC-05** Lượt C không tạo bước không có trong input (test với fake LLM cố tình thêm bước → bị lọc bằng so khớp ngược).
- **AC-06** JSON lỗi 2 lần liên tiếp → segment vào `failed_segments.json`, pipeline vẫn trả kết quả cho các segment khác.
- **AC-07** `sweep` trên fixture ra CSV đủ cột `fps, recall, precision, order_accuracy, tokens_used, latency_s`.
- **AC-08** `propose-reasons` chỉ điền `reason` khi transcript chứa phát ngôn; `reason_source="expert_verbal"`, `status="in_review"`.

## 9. Tasks
- [ ] T04-1 Provider protocol + `OpenAICompatVLM` + `FakeVLM` + factory + DataGuard (AC-03).
- [ ] T04-2 Frame sampler từ clip (fps, resize).
- [ ] T04-3 Lượt A + prompt + validate + repair (AC-01, AC-02, AC-06).
- [ ] T04-4 Lượt B tự nhất quán (AC-04).
- [ ] T04-5 Lượt C tổng hợp (AC-05).
- [ ] T04-6 `sweep` (AC-07).
- [ ] T04-7 `propose-reasons` (AC-08).

## Changelog
- v1.0 (23/9): khởi tạo.
- v1.1 (23/9): hậu xử lý gán `evidence.segment_ids` (contract WorkProfile thêm field).
