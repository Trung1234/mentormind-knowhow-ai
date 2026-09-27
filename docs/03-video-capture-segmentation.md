# 03 — Video Capture, Segmentation & Transcript

**Owner:** Việt Hoàng · **Tasks Excel:** S0-7 (dữ liệu, Đạt), S1-2, S2-6

## 1. Mục tiêu
Cắt video thao tác thành các đoạn ngắn có ranh giới hợp lý để VLM (spec 04) mô tả chính xác, trích keyframe làm minh họa SOP, và chuyển lời bình luận của chuyên gia thành transcript có timestamp.

## 2. Vì sao phải tự cắt đoạn trước khi đưa VLM
VLM lấy mẫu thưa (mặc định ~1 fps) sẽ bỏ sót động tác tay nhanh. Cắt trước thành đoạn 5–15s cho phép đẩy fps cao trên từng đoạn mà không tốn token.

## 3. Data model — `core.schemas.video`
```python
class VideoAsset(BaseModel):
    video_id: str              # "VID-" + sha256[:12]
    path: str
    duration_s: float
    fps: float
    has_audio: bool
    process_id: str | None
    data_classification: DataClassification

class Segment(BaseModel):
    segment_id: str            # f"{video_id}-S{index:03d}"
    video_id: str
    index: int
    t_start: float
    t_end: float
    method: Literal["scene", "hand_activity", "fixed_window"]
    motion_score: float | None     # 0..1, None nếu không tính
    keyframes: list[str]           # đường dẫn JPG
    clip_path: str                 # mp4 đã cắt
    data_classification: DataClassification   # kế thừa từ VideoAsset, để DataGuard (spec 04) kiểm tra không cần tra ngược

class TranscriptSegment(BaseModel):
    video_id: str
    t_start: float
    t_end: float
    text: str
    language: str
    source: Literal["inline", "cued_recall"] = "inline"   # lời bình khi quay / ghi âm video-cued recall
    data_classification: DataClassification
```

## 4. Functional Requirements
- **FR-01** `knowhow video probe <file>` trả `VideoAsset` (ffprobe).
- **FR-02** `knowhow video segment <file> --process-id PACK01 --classification synthetic` tạo `Segment` list + file JSON tại `data/work/video/<video_id>/segments.json`.
- **FR-03** Chiến lược cắt theo thứ tự ưu tiên, cấu hình được bằng `--method`:
  1. `hand_activity` (Should): MediaPipe Hands, tính năng lượng chuyển động cổ tay; ranh giới ở điểm năng lượng thấp kéo dài ≥ 0.4s.
  2. `scene` (Must): PySceneDetect `ContentDetector`.
  3. `fixed_window` (Must, fallback): cửa sổ 10s.
- **FR-04** Hậu xử lý: gộp đoạn < 3s vào đoạn kế bên; tách đoạn > 20s thành các đoạn ≤ 15s.
- **FR-05** Mỗi đoạn xuất 3 keyframe (đầu, giữa, cuối) JPG, cạnh dài 768px.
- **FR-06** Mỗi đoạn xuất `clip_path` mp4 (ffmpeg `-c copy` nếu được, không thì re-encode H.264).
- **FR-07** `knowhow video transcribe <file>` (Should): nếu `has_audio`, chạy Whisper local (faster-whisper, model `small`, `language="vi"` mặc định, cấu hình được) → `TranscriptSegment` list tại `transcript.json`. Không dùng ASR cloud.
- **FR-07b** `knowhow video transcribe --recall-audio <audio_file> --video-id <VID-...> [--offset <s>]` (Should): nhận file ghi âm video-cued recall (architecture mục 4) cho video câm. Timestamp transcript = timestamp audio + `offset` (mặc định 0, tức chuyên gia bắt đầu ghi âm cùng lúc phát video). Kết quả `source="cued_recall"`, `data_classification` lấy từ `VideoAsset`, ghi nối vào `transcript.json` của video đó.
- **FR-08** `align_transcript(segments, transcripts) -> dict[segment_id, list[TranscriptSegment]]` gán mỗi câu transcript vào đoạn có overlap thời gian lớn nhất.

## 5. Acceptance Criteria
- **AC-01** 3 video demo trong `data/samples/video/` → mỗi video ra ≥ 3 đoạn, mọi đoạn có 3 keyframe và 1 clip tồn tại trên đĩa.
- **AC-02** Không đoạn nào < 3s hoặc > 20s sau hậu xử lý.
- **AC-03** Các đoạn liên tiếp không chồng lấn và phủ ≥ 95% thời lượng video.
- **AC-04** `--method hand_activity` khi thiếu MediaPipe → tự rơi về `scene`, log cảnh báo, không crash.
- **AC-05** Video không có audio → `transcribe` trả list rỗng, không lỗi.
- **AC-06** `align_transcript` với dữ liệu giả lập: câu nằm vắt qua ranh giới được gán cho đoạn chứa phần lớn thời lượng của câu.
- **AC-07** Mọi `Segment` và `TranscriptSegment` mang đúng `data_classification` của `VideoAsset` gốc.
- **AC-08** `--recall-audio` với `--offset 12.5` trên audio giả lập → mọi `t_start` được cộng 12.5, `source="cued_recall"`; `--video-id` không tồn tại → báo lỗi, không ghi file.

## 6. Tasks
- [ ] T03-1 Models + `probe`.
- [ ] T03-2 Cắt `scene` + `fixed_window` + hậu xử lý (AC-01..03).
- [ ] T03-3 Keyframe + clip export.
- [ ] T03-4 `hand_activity` với MediaPipe + fallback (AC-04).
- [ ] T03-5 `transcribe` faster-whisper + `align_transcript` (AC-05, AC-06).
- [ ] T03-6 Lan truyền `data_classification` (AC-07) + `--recall-audio` (AC-08).

## Changelog
- v1.0 (23/9): khởi tạo.
- v1.1 (23/9): `Segment`/`TranscriptSegment` mang `data_classification`; thêm FR-07b nạp audio video-cued recall cho video câm (AC-07, AC-08, T03-6).
- v1.2 (27/9): đường dẫn module theo layout mới (bỏ `knowhow.`/`src/knowhow/`, xem spec 01 v1.3).
