# 03b — Video capture: spec chi tiết cho phần của Việt Hoàng

**Owner:** Việt Hoàng (cần xác nhận, xem §9) · **Tasks Excel:** S0-7 (dữ liệu, Đạt), S1-2, S2-6 · **Bổ sung cho:** `docs/03-video-capture-segmentation.md`
**Trạng thái:** DRAFT chờ duyệt. Chưa sửa spec gốc; các thay đổi đề xuất nằm ở §10 dưới dạng diff (theo CLAUDE.md).

## 1. Phạm vi
Nhận một file video thao tác → `VideoAsset` → danh sách `Segment` (đoạn 3–20 s, mỗi đoạn có keyframe và clip) → (tùy chọn) transcript có timestamp. Spec 04 (VLM) đọc kết quả này; spec 06/08 trích dẫn `segment_id`.

Ngoài phạm vi: mô tả bước thao tác (spec 04), giao diện upload (spec 08), tải video về, face-blur (đã có ở `core/guard/image`).

| # | Việc | Task | DoD đề xuất |
|---|---|---|---|
| A | probe + cắt đoạn + hậu xử lý | T03-1, T03-2 | AC-01..03 trên video thật; `segments.json` được spec 04 đọc được |
| B | keyframe + clip + nhãn dữ liệu | T03-3, T03-6a | Mỗi đoạn có 3 JPG + 1 mp4 trên đĩa; AC-07 |
| C | `motion_score` | T03-7 (mới) | Điểm 0..1 hiệu chuẩn với `groundtruth.json`; spec 04 chọn fps theo điểm này |
| D | transcript + align | T03-5 | AC-05, AC-06 |
| E | hand_activity (MediaPipe) | T03-4 | AC-04 (fallback), nếu cài được |
| F | `--recall-audio` | T03-6b | AC-08 |

## 2. Brainstorm: các quyết định và lý do

| # | Câu hỏi | Lựa chọn | Lý do |
|---|---|---|---|
| D1 | Camera trạm quay liên tục thì `scene` ít điểm cắt | Giữ `scene` làm chiến lược Must; nếu sau hậu xử lý < 3 đoạn thì **tự rơi về `fixed_window`**, log lý do | Video LASI (đã dựng) có 50 cảnh, nhưng video quay tại trạm 3–5 phút gần như một cảnh. AC-01 đòi ≥ 3 đoạn |
| D2 | `--method` mặc định | `scene` | Spec chỉ nói "theo thứ tự ưu tiên"; `hand_activity` là Should và phụ thuộc MediaPipe |
| D3 | Clip: `-c copy` hay encode lại | **Encode lại** H.264, bỏ audio, cạnh dài 640 px; `--copy` là tùy chọn | `-c copy` chỉ cắt đúng tại keyframe gốc → ranh giới lệch vài giây, sai với đoạn 5–15 s. VLM chỉ thấy khung 448 px. Bỏ audio để clip không mang lời nói thật |
| D4 | Vị trí 3 keyframe | `t_start + 0.1 s`, giữa đoạn, `t_end − 0.1 s` (kẹp trong đoạn); cạnh dài 768 px từ video gốc | Khung đúng ranh giới thường thuộc cảnh bên cạnh hoặc đang mờ chuyển |
| D5 | Định dạng `segments.json` | **Danh sách JSON phẳng của `Segment`** | Spec 04 (`vlm/cli/describe.py`) đọc đúng định dạng này. `VideoAsset` ghi riêng ở `asset.json` |
| D6 | `Segment.index` bắt đầu từ 0 hay 1 | **1** | Code spec 04 đang dùng 1 (`S001`) |
| D7 | `motion_score` | Tính cho **mọi** đoạn bằng chênh lệch khung (cv2, không thêm phụ thuộc), hiệu chuẩn bằng `groundtruth.json` | Spec 04 chọn fps theo điểm (≥ 0.6 → 8 fps, < 0.3 → 2 fps); `None` làm mất lợi ích này. Không đòi MediaPipe |
| D8 | Thêm `method` mới (vd `motion_valley`)? | **Không** | `Segment.method` là `Literal` dùng chung; đổi là đổi hợp đồng với spec 04 |
| D9 | ASR | faster-whisper `small`, `vad_filter=True`, CPU `int8`; `--language` mặc định `vi` nhưng nhận `auto`; `--model` cấu hình được | Chạy local (Điều 2). VAD tránh bịa chữ trên đoạn im lặng. Spike: video LASI có audio **tiếng Thái**, nên cần `auto`; `small` chạy ~0,7× thời gian thực trên CPU |
| D10 | `video_id` | `VID-` + sha256[:12] của file (spec 03 §3) | Endpoint upload trên `main` đang tạo `VID-{process_id}-{uuid}` — lệch, xem §9 |
| D11 | Bộ cắt tạm của Phúc (`processing/vlm/sweep/windows.py`) và `groundtruth.json` | **Không sửa, không import vào code chạy.** `capture/video/` viết độc lập, chấp nhận trùng một phần nhỏ (`video_id_for`, cửa sổ cố định). `groundtruth.json` chỉ **đọc** để hiệu chuẩn | Bộ cắt tạm tự ghi là dùng "until spec 03 lands"; spec 04 đã đọc `segments.json` nên khi phần này xong, Phúc dùng `vlm describe <video_id>` mà không phải sửa gì. Rủi ro trùng được chặn bằng test hợp đồng (D11b) |
| D11b | Hai bản `video_id`/chia cửa sổ lệch nhau về sau | Test hợp đồng: `capture.video.video_id_for(f) == vlm.sweep.windows.video_id_for(f)` và `window_bounds` cho cùng kết quả trên cùng độ dài | Nếu Phúc đổi, test đỏ và báo cho cả hai; test chỉ **đọc** code của Phúc |
| D12 | Hạ tầng | `ffmpeg`/`ffprobe` bắt buộc (binary ngoài); extra `video` = `scenedetect` (Must) + `faster-whisper` (Should). **`mediapipe` không vào extra chung** | Spike: bản 1.0.1 abort ở tầng C++ trên macOS; bản 0.10.21 chạy nhưng hạ numpy 2 → 1.26 |

## 3. Data model
Dùng nguyên `core/schemas/video.py` (đã có, đúng spec §3). Ràng buộc bổ sung (validator, không đổi trường):
- `Segment`: `0 ≤ t_start < t_end ≤ duration`; `len(keyframes) == 3` khi đã export; `motion_score ∈ [0,1]` hoặc `None`; `segment_id == f"{video_id}-S{index:03d}"`.
- `TranscriptSegment`: `t_start < t_end`, `text` không rỗng.

Tệp trong `data/work/video/<video_id>/`:
```
asset.json        # VideoAsset
segments.json     # list[Segment], sắp theo index
keyframes/<segment_id>-{0,1,2}.jpg
clips/<segment_id>.mp4
transcript.json   # list[TranscriptSegment]; --recall-audio ghi nối vào
```

## 4. Cắt đoạn (FR-02..FR-04)
1. `probe` → `VideoAsset` (ffprobe: duration, fps, có audio stream không).
2. Chiến lược: `scene` (`ContentDetector`, ngưỡng cấu hình `KNOWHOW_SCENE_THRESHOLD`, mặc định 20 theo spike T03-0), `fixed_window` (`KNOWHOW_SEGMENT_WINDOW_S`, mặc định 10), `hand_activity` (Should).
3. Hậu xử lý, theo thứ tự: (a) gộp đoạn < 3 s vào đoạn **trước**, đoạn đầu thì vào đoạn sau; (b) đoạn > 20 s chia đều thành `ceil(d/15)` phần (mỗi phần ≤ 15 s); (c) đánh lại `index` từ 1.
4. Các đoạn liền nhau, không chồng lấn, phủ toàn bộ video → AC-03 luôn đạt.
5. Ngoại lệ: video < 3 s chỉ có 1 đoạn (< 3 s); video < 9 s không thể có ≥ 3 đoạn. AC-01/02 áp dụng cho video ≥ 9 s.

## 5. Keyframe và clip (FR-05, FR-06)
- ffmpeg cho cả hai; ghi qua tệp tạm rồi `rename` (không để lại tệp dở).
- Cache theo tên tệp: chạy lại không cắt lại clip/keyframe đã có và hợp lệ; `--force` cắt lại.
- Lỗi ffmpeg trên một đoạn → báo lỗi rõ (đoạn nào, stderr), không bỏ đoạn đó im lặng.

## 6. motion_score (mới, Should)
- Lấy mẫu ~5 khung/giây, thu về xám 160 px, `mean(|f_t − f_{t−1}|) / 255` rồi lấy trung bình trên đoạn.
- Chuẩn hóa về 0..1 bằng hằng số hiệu chuẩn (`KNOWHOW_MOTION_SCALE`) chọn sao cho trên `data/video/groundtruth.json` các bước `actor=worker/robot` có điểm cao hơn các cảnh phỏng vấn/logo. Mục tiêu là **tách được hai nhóm**, không phải đúng tuyệt đối.
- Ngưỡng 0.3 / 0.6 của spec 04 là hằng số cố định nên điểm phải là tuyệt đối, không chuẩn hóa theo từng video.

## 7. Transcript (FR-07, FR-07b, FR-08)
- `transcribe <file>`: không có audio → `[]`, không lỗi (AC-05). Có audio: trích WAV 16 kHz mono bằng ffmpeg → faster-whisper (`small`, `language="vi"` cấu hình được, `vad_filter=True`) → `TranscriptSegment`.
- `--recall-audio <file> --video-id <id> [--offset s]`: `t = t_audio + offset`, `source="cued_recall"`, nhãn lấy từ `asset.json`; `video_id` chưa có `asset.json` → lỗi, không ghi gì (AC-08).
- `align_transcript`: mỗi câu gán vào đoạn có thời gian chồng lớn nhất; hòa thì chọn đoạn sớm hơn; không chồng với đoạn nào thì bỏ khỏi kết quả.
- ASR đứng sau interface `Transcriber`; test dùng `FakeTranscriber` (Điều 6: không gọi mạng; lần đầu faster-whisper cần tải model về cache, ghi trong README).

## 8. CLI và an toàn dữ liệu
```
knowhow video probe <file>
knowhow video segment <file> --process-id PACK01 --classification synthetic [--method scene|fixed_window|hand_activity] [--force]
knowhow video transcribe <file> [--language vi]
knowhow video transcribe --recall-audio <audio> --video-id VID-... [--offset 0]
```
- `--classification` bắt buộc cho `segment` (không mặc định, như `ingest run`); `Segment` và `TranscriptSegment` kế thừa từ `VideoAsset` (AC-07).
- Mọi bước chạy local; gọi `DataGuard.check` với provider local để giữ điểm chặn tập trung.
- Chạy lại cùng file + cùng tham số → cùng `video_id`, cùng `segment_id`, cùng `segments.json`. Đổi `--classification` trên video đã xử lý → lỗi, trừ `--force`.

## 9. Việc cần xác nhận / phối hợp
| Việc | Với ai | Vì sao |
|---|---|---|
| S1-2, S2-6 có đúng của Việt Hoàng không | Trung / Đạt | Danh sách việc ban đầu chỉ có S0-5, S1-1, S2-5; spec 03 ghi owner Việt Hoàng |
| Báo Phúc: phần video là module riêng, không đụng `windows.py`; khi xong có thể dùng `vlm describe <video_id>` | Phúc | Chỉ thông báo, không cần Phúc sửa gì |
| `video_id` của endpoint upload (`VID-{process}-{uuid}`) lệch spec | Người làm backend | Đường dẫn `data/work/video/<video_id>/` phụ thuộc id này |
| Nguồn 3 video mẫu cho AC-01 | Đạt (S0-7) | Repo chỉ có `groundtruth.json`; VID-03/04/05 không được phát hành lại; LASI là video quảng bá |
| `groundtruth.json` đang `draft`, gán bởi Claude | Đạt / Phúc | Chỉ đọc, không sửa; dùng để hiệu chuẩn `motion_score` và đo `scene` nên cần duyệt trước khi chốt số đo |

## 10. Đề xuất sửa spec gốc (diff, chưa áp dụng)
**`docs/03-video-capture-segmentation.md`**
```diff
- **FR-02** ... tạo `Segment` list + file JSON tại `data/work/video/<video_id>/segments.json`.
+ **FR-02** ... ghi `segments.json` (danh sách JSON phẳng của `Segment`, `index` từ 1, đúng định dạng spec 04 đọc) và `asset.json` (`VideoAsset`) tại `data/work/video/<video_id>/`. `--classification` bắt buộc.
+ **FR-03b** `--method` mặc định `scene`; nếu sau hậu xử lý < 3 đoạn thì tự rơi về `fixed_window` và log.
- **FR-06** Mỗi đoạn xuất `clip_path` mp4 (ffmpeg `-c copy` nếu được, không thì re-encode H.264).
+ **FR-06** Mỗi đoạn xuất `clip_path` mp4: re-encode H.264, cạnh dài 640 px, không audio (`-c copy` chỉ khi `--copy`, ranh giới lệch tới keyframe gốc).
+ **FR-09** `motion_score` (Should): chênh lệch khung trung bình của đoạn, 0..1, tuyệt đối (không chuẩn hóa theo video), hiệu chuẩn bằng `data/video/groundtruth.json`.
```
- **AC-01/02** thêm điều kiện "video ≥ 9 s".
- Thêm **AC-09** (idempotent: chạy lại cho cùng `segments.json`), **AC-10** (`motion_score ∈ [0,1]` và cao hơn ở cảnh có thao tác so với cảnh phỏng vấn trên `groundtruth.json`), **AC-11** (đổi `--classification` trên video đã xử lý → lỗi, `--force` mới ghi đè).
- Tasks: thêm `T03-0` (spike công cụ) và `T03-7` (`motion_score`).

## 11. Rủi ro
| Rủi ro | Giảm thiểu |
|---|---|
| Chưa có `ffmpeg`/`ffprobe` trên máy dev | Cài ở T03-0; test cần ffmpeg tự skip nếu thiếu |
| MediaPipe: abort C++ trên macOS (1.0.1) / hạ numpy (0.10.21) — **đã xác nhận ở spike** | T03-4 chạy trong tiến trình con, rơi về `scene` khi lỗi; không đưa vào extra chung; làm cuối hoặc bỏ |
| Whisper `small` chậm trên CPU/Mac, tiếng Việt kém | Đo ở T03-0; có `--model` cấu hình; transcript là Should |
| Chưa có video mẫu thật | Test dùng video tổng hợp sinh bằng `cv2.VideoWriter`; AC-01 chính thức chờ Đạt |
| `scene` quá nhạy/kém nhạy | Đo precision/recall với 50 điểm cắt của `groundtruth.json` (±0,5 s) để chọn ngưỡng |
| `groundtruth.json` chưa được duyệt | Ghi rõ trong báo cáo đo; không dùng làm số liệu chính thức khi chưa duyệt |

## Changelog
- v0.1 (4/10): khởi tạo từ brainstorm.
