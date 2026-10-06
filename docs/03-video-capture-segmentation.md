# 03 — Video Capture, Segmentation & Transcript

**Owner:** Việt Hoàng · **Tasks Excel:** S0-7 (dữ liệu, Đạt), S1-2, S2-6

## 1. Mục tiêu
Cắt video thao tác thành các đoạn ngắn có ranh giới hợp lý để VLM (spec 04) mô tả chính xác, trích keyframe làm minh họa SOP, và chuyển lời bình luận của chuyên gia thành transcript có timestamp.

## 2. Vì sao phải tự cắt đoạn trước khi đưa VLM
VLM lấy mẫu thưa (mặc định ~1 fps) sẽ bỏ sót động tác tay nhanh. Cắt trước thành đoạn 5–15s cho phép đẩy fps cao trên từng đoạn mà không tốn token.

## 3. Data model — `core.schemas.video`
```python
class VideoAsset(BaseModel):
    video_id: str  # "VID-" + sha256[:12]
    path: str
    duration_s: float
    fps: float
    has_audio: bool
    process_id: str | None
    data_classification: DataClassification


class Segment(BaseModel):
    segment_id: str  # f"{video_id}-S{index:03d}"
    video_id: str
    index: int
    t_start: float
    t_end: float
    method: Literal["scene", "hand_activity", "fixed_window"]
    motion_score: float | None  # 0..1, None nếu không tính
    keyframes: list[str]  # đường dẫn JPG
    clip_path: str  # mp4 đã cắt
    data_classification: (
        DataClassification  # kế thừa từ VideoAsset, để DataGuard (spec 04) kiểm tra không cần tra ngược
    )


class TranscriptSegment(BaseModel):
    video_id: str
    t_start: float
    t_end: float
    text: str
    language: str
    source: Literal["inline", "cued_recall"] = "inline"  # lời bình khi quay / ghi âm video-cued recall
    data_classification: DataClassification
```

## 4. Functional Requirements
- **FR-01** `knowhow video probe <file>` trả `VideoAsset` (ffprobe).
- **FR-02** `knowhow video segment <file> --process-id PACK01 --classification synthetic` ghi `segments.json` (danh sách JSON phẳng của `Segment`, `index` từ 1, đúng định dạng spec 04 đọc) và `asset.json` (`VideoAsset`) tại `data/work/video/<video_id>/`, cùng `keyframes/` và `clips/`. `--classification` bắt buộc. Chạy lại cùng file cho cùng kết quả; đổi nhãn trên video đã xử lý là lỗi trừ khi có `--force`. JSON ghi sau cùng và nguyên tử. *(Chi tiết định dạng và nhãn: chờ Trung duyệt, `docs/plans/03-video-spec.md` §10.)*
- **FR-03** Chiến lược cắt theo thứ tự ưu tiên, cấu hình được bằng `--method`:
  1. `hand_activity` (Should): MediaPipe Hands, tính năng lượng chuyển động cổ tay; ranh giới ở điểm năng lượng thấp kéo dài ≥ 0.4s.
     *Cách làm:* MediaPipe 0.10.x chạy trong **tiến trình và môi trường Python riêng** (`hand_worker.py`, mặc định `uv run --no-project --with mediapipe==0.10.21`, hoặc Python có sẵn qua `KNOWHOW_HAND_PYTHON`) vì bản 1.0.x crash ở tầng C++ trên macOS và bản 0.10.x ép numpy<2. Worker lấy mẫu 5 fps và trả vị trí cổ tay; phần quyết định cắt ở đâu nằm trong `hand_activity.py`: tốc độ cổ tay giữa hai mẫu (ghép cổ tay gần nhất), nghỉ = chuỗi ≥ `KNOWHOW_HAND_VALLEY_MIN_S` (0,4 s) có tốc độ < `KNOWHOW_HAND_VALLEY_RATIO` (0,2) × phân vị 75 của chính video, cắt ở giữa chỗ nghỉ. Khung không thấy tay tính là nghỉ. Dưới `KNOWHOW_HAND_MIN_PRESENCE` (10%) số khung thấy tay thì từ chối (điểm cắt khi đó chỉ phản ánh lúc tay vắng mặt) → rơi về `scene` kèm tỉ lệ đo được. Worker crash, quá `KNOWHOW_HAND_TIMEOUT_S`, thiếu `uv` hoặc không tải được MediaPipe → cũng rơi về `scene` (AC-04).
  2. `scene` (Must): PySceneDetect `ContentDetector`.
  3. `fixed_window` (Must, fallback): cửa sổ 10s.
  - **FR-03b** `--method` mặc định `scene` (ngưỡng `KNOWHOW_SCENE_THRESHOLD`, mặc định 20 theo spike T03-0). Chiến lược thiếu thư viện hoặc lỗi → rơi về chiến lược kế tiếp (`hand_activity` → `scene` → `fixed_window`) và log; chiến lược ra ít hơn 3 đoạn (vd `scene` trên một cảnh quay liền) → cũng rơi về chiến lược kế tiếp.
- **FR-04** Hậu xử lý: gộp đoạn < 3s vào đoạn kế bên; tách đoạn > 20s thành các đoạn ≤ 15s.
- **FR-05** Mỗi đoạn xuất 3 keyframe (đầu, giữa, cuối) JPG, cạnh dài 768px.
- **FR-06** Mỗi đoạn xuất `clip_path` mp4: re-encode H.264, cạnh dài tối đa 640 px, không audio (`-c copy` chỉ khi chọn riêng: ranh giới lệch tới keyframe gốc, đo ở spike T03-0 được 8,7–13,0 s khi xin 8 s).
- **FR-07** `knowhow video transcribe <file>` (Should): nếu `has_audio`, chạy Whisper local (faster-whisper, model `small`, `language="vi"` mặc định, cấu hình được) → `TranscriptSegment` list tại `transcript.json`. Không dùng ASR cloud. `--classification` bắt buộc (như `segment`; nhãn đã ghi trong `asset.json` thì đổi là lỗi trừ `--force`); `--language` nhận mã ngôn ngữ hoặc `auto` (Whisper tự nhận diện, `TranscriptSegment.language` ghi ngôn ngữ thật), `--model` chọn model; `vad_filter` bật để tránh bịa chữ trên đoạn im lặng. Chạy lại thay các dòng `inline`, giữ các dòng `cued_recall`. Video LASI có audio **tiếng Thái** nên cần `--language auto` (xem `docs/plans/03-spike-notes.md`).
- **FR-07b** `knowhow video transcribe --recall-audio <audio_file> --video-id <VID-...> [--offset <s>]` (Should): nhận file ghi âm video-cued recall (architecture mục 4) cho video câm. Timestamp transcript = timestamp audio + `offset` (mặc định 0, tức chuyên gia bắt đầu ghi âm cùng lúc phát video). Kết quả `source="cued_recall"`, `data_classification` lấy từ `VideoAsset`, ghi vào `transcript.json` của video đó. `<file>` và `--recall-audio` loại trừ nhau; `--classification` không dùng ở chế độ này (nhãn lấy từ `asset.json`); `--video-id` phải có dạng `VID-<mã>` (là tên thư mục, nên không cho `/` hay `..`) và video phải đã được xử lý (`segment` hoặc `transcribe`), `--offset` ≥ 0. **Một bản ghi âm sở hữu khoảng thời gian video nó phủ** (`offset` đến `offset` + độ dài audio): chạy lại cùng file, hoặc ghi âm mới trong khoảng đó, thay các câu `cued_recall` đã có trong khoảng ấy; ghi âm ở khoảng khác thì được thêm vào; câu `inline` luôn giữ nguyên. Không so từng chữ vì Whisper chia câu khác nhau giữa các lần chạy. Câu kết thúc sau khi hết video → in cảnh báo kiểm tra lại `--offset`, không từ chối.
- **FR-08** `align_transcript(segments, transcripts) -> dict[segment_id, list[TranscriptSegment]]` gán mỗi câu transcript vào đoạn có overlap thời gian lớn nhất.
- **FR-09** (Should) `Segment.motion_score` (0..1): median chênh lệch tuyệt đối giữa các khung liên tiếp (lấy mẫu 5 fps, xám 160x90) của các cặp nằm trọn trong đoạn, chia `KNOWHOW_MOTION_SCALE` (mặc định 0,1) rồi kẹp về 1. Điểm tuyệt đối (không chuẩn hóa theo từng video) vì spec 04 chọn fps theo ngưỡng 0,3/0,6. Không tính được (ffmpeg lỗi, đoạn < 0,4 s) → `None`, không làm hỏng lệnh. Dùng median vì mean bị điểm cắt cảnh kéo lên.

## 5. Acceptance Criteria
- **AC-01** 3 video demo trong `data/samples/video/` → mỗi video ra ≥ 3 đoạn, mọi đoạn có 3 keyframe và 1 clip tồn tại trên đĩa (áp dụng cho video ≥ 9 s). *(Hiện kiểm trên video LASI và video tổng hợp; 3 video mẫu chính thức chờ S0-7.)*
- **AC-02** Không đoạn nào < 3s hoặc > 20s sau hậu xử lý.
- **AC-03** Các đoạn liên tiếp không chồng lấn và phủ ≥ 95% thời lượng video.
- **AC-04** `--method hand_activity` khi thiếu MediaPipe → tự rơi về `scene`, log cảnh báo, không crash.
- **AC-05** Video không có audio → `transcribe` trả list rỗng, không lỗi.
- **AC-06** `align_transcript` với dữ liệu giả lập: câu nằm vắt qua ranh giới được gán cho đoạn chứa phần lớn thời lượng của câu.
- **AC-07** Mọi `Segment` và `TranscriptSegment` mang đúng `data_classification` của `VideoAsset` gốc.
- **AC-09** Chạy `video segment` 2 lần trên cùng file → `segments.json` giống từng byte, media không bị cắt lại.
- **AC-10** `motion_score` ∈ [0,1] cho mọi đoạn; trên video LASI, các cảnh `work` của `data/video/groundtruth.json` có điểm cao hơn cảnh phỏng vấn/logo/tiêu đề (AUC ≥ 0,85, đo được 0,93; trung vị `work` ≥ 0,3 > trung vị cảnh tĩnh). `groundtruth.json` còn `draft`.
- **AC-11** Chạy lại cùng video với `--classification` khác → lỗi, file cũ giữ nguyên; với `--force` → ghi đè.
- **AC-08** `--recall-audio` với `--offset 12.5` trên audio giả lập → mọi `t_start` được cộng 12.5, `source="cued_recall"`; `--video-id` không tồn tại → báo lỗi, không ghi file.

## 6. Tasks
- [x] T03-0 Spike công cụ (ffmpeg, PySceneDetect, Whisper, MediaPipe) — `docs/plans/03-spike-notes.md`.
- [x] T03-1 Models + `probe`.
- [x] T03-2 Cắt `scene` + `fixed_window` + hậu xử lý (AC-01..03).
- [x] T03-3 Keyframe + clip export.
- [x] T03-4 `hand_activity` với MediaPipe + fallback (AC-04). *(Logic và cô lập tiến trình đã kiểm; chưa có ca dương thật vì chưa có video quay tại trạm.)*
- [x] T03-5 `transcribe` faster-whisper + `align_transcript` (AC-05, AC-06).
- [x] T03-7 `motion_score` (FR-09, AC-10).
- [x] T03-6a Lan truyền `data_classification` (AC-07), nhãn bắt buộc và đổi nhãn (AC-11).
- [x] T03-6b `--recall-audio` (AC-08).

## Changelog
- v1.0 (23/9): khởi tạo.
- v1.1 (23/9): `Segment`/`TranscriptSegment` mang `data_classification`; thêm FR-07b nạp audio video-cued recall cho video câm (AC-07, AC-08, T03-6).
- v1.2 (27/9): đường dẫn module theo layout mới (bỏ `knowhow.`/`src/knowhow/`, xem spec 01 v1.3).
- 4/10/2026 (Việt Hoàng): T03-0..T03-3 và T03-6a xong — `capture/video/{probe,postprocess,segmenters,media,pipeline,cli}.py`, `knowhow video probe|segment`; thêm FR-03b, AC-09, AC-11; sửa FR-02, FR-06 theo spike (`docs/plans/03-spike-notes.md`). Chạy thật trên video LASI (193,8 s): 31 đoạn (3,0–15,1 s, phủ 100%), 22 s; `knowhow vlm describe <video_id>` (provider fake) đọc được `segments.json`. Test hợp đồng với `processing/vlm/sweep/windows.py` của spec 04 (chỉ đọc). Chưa làm: `motion_score`, `transcribe`, `--recall-audio`, `hand_activity`. `make check` xanh (494 test).
- 4/10/2026 (Việt Hoàng): T03-7 xong — `capture/video/motion.py` (ffmpeg → khung xám 5 fps → median chênh lệch → chia `motion_scale`=0,1), gán `Segment.motion_score` trong `video segment`; thêm FR-09, AC-10. Calibrate trên LASI vs `groundtruth.json` (AUC 0,93; cảnh `work` TB 0,56, phỏng vấn 0,05). Trên 31 đoạn: 17 đoạn < 0,3 (spec 04: 2 fps), 10 đoạn mặc định, 4 đoạn ≥ 0,6 (8 fps). +7 s xử lý. `make check` xanh.
- 4/10/2026 (Việt Hoàng): T03-5 xong — `capture/video/{transcribe,align}.py`, `knowhow video transcribe` (Whisper `small` local, `--language auto`, `--model`, nhãn bắt buộc, giữ dòng `cued_recall` khi chạy lại), `align_transcript` (câu vào đoạn chồng thời gian lớn nhất, hòa thì đoạn sớm hơn). Chạy thật trên LASI (tiếng Thái): 30 câu, 168 s (~0,87× thời gian thực), 30/30 câu gán được vào 21/31 đoạn. Thêm `faster-whisper` vào extra `video` (numpy 2.4 và OpenCV 5 giữ nguyên). Chưa làm: `--recall-audio` (T03-6b), `hand_activity`. `make check` xanh.
- 4/10/2026 (Việt Hoàng): T03-6b xong — `knowhow video transcribe --recall-audio <audio> --video-id <VID-...> [--offset s]` (`transcribe_recall`): timestamp = audio + offset, `source=cued_recall`, nhãn từ `asset.json`, `--video-id` lạ hoặc sai dạng → lỗi không ghi gì (AC-08). Chạy thật với Whisper trên LASI: phát hiện ban đầu là chạy lại cùng file ghi âm làm tăng dòng (Whisper chia câu 5, 6, 8 câu ở các lần chạy), nên đổi sang quy tắc "bản ghi âm sở hữu khoảng thời gian nó phủ"; xác nhận lại: chạy lại thay 6 câu bằng 6 câu, ghi âm khoảng khác thì thêm. `make check` xanh (554 test).
- 4/10/2026 (Việt Hoàng): T03-4 xong — `capture/video/{hand_activity,hand_worker}.py`: MediaPipe 0.10.21 chạy trong tiến trình/môi trường riêng (`uv run --no-project`), thuật toán nghỉ ≥ 0,4 s theo tốc độ cổ tay, ngưỡng hiện diện 10%, mọi lỗi (crash `os.abort`, timeout, thiếu uv, JSON hỏng) rơi về `scene` (AC-04) và đã kiểm bằng tiến trình con thật. Trên LASI: thấy tay 3,3% số khung → từ chối đúng, rơi về `scene` (31 đoạn). **Chưa kiểm được ca dương thật** (LASI không có đủ khung có tay; cần video quay tại trạm, việc S0-7). Sửa thêm: cảnh báo ObjC "duplicate class" khi `scenedetect` nạp PyAV cùng OpenCV (từ khi thêm faster-whisper) nay được chặn; thông báo fallback không còn lặp tiền tố. `make check` xanh (578 test).
