# T03-0 — Spike công cụ video (4/10/2026)

Máy: MacBook Apple Silicon, **chỉ CPU**, Python 3.11, ffmpeg 9.0.2. Thử bằng `uv run --with ...` (môi trường tạm), **chưa sửa** `pyproject.toml`/`uv.lock`.
Video: `data/video/LASI Success Case ... [m4icg6FgTBU].mkv` (193,8 s, 1920x1080, 29,97 fps, H.264 + opus; sha256 khớp bản LFS của đội).
Nhãn so sánh: `data/video/groundtruth.json` (50 cảnh gán tay, 49 điểm cắt). **File này còn `draft`, các cảnh fade dùng mốc ước lượng** → số đo dưới đây là tham khảo.

## 1. Cắt cảnh — PySceneDetect 0.7.1
Mỗi lần chạy ~6–7 s cho cả video. Đối chiếu với 49 điểm cắt thật:

| Cấu hình | Tìm được | Đúng (±0,5 s) | Precision | Recall |
|---|---|---|---|---|
| `ContentDetector` th=15 | 49 | 42 | 0,86 | 0,86 |
| `ContentDetector` th=20 | 46 | 42 | 0,91 | 0,86 |
| `ContentDetector` th=27 (mặc định thư viện) | 42 | 41 | 0,98 | 0,84 |
| `ContentDetector` th=35 | 42 | 41 | 0,98 | 0,84 |
| `AdaptiveDetector` 3.0 | 46 | 42 | 0,91 | 0,86 |

**Chọn th=20** làm mặc định (`KNOWHOW_SCENE_THRESHOLD`): cắt thừa sẽ bị bước gộp đoạn < 3 s hấp thụ, còn cắt thiếu thì không sửa lại được, nên ưu tiên recall. Th=27 đúng hơn một chút nhưng bỏ sót nhiều hơn. Chênh lệch nhỏ và nhãn còn draft, nên chưa coi là kết luận cuối.

## 2. ffmpeg
| Việc | Kết quả |
|---|---|
| Cắt clip 10 s, encode lại H.264, cạnh dài 640 px, bỏ audio | ~0,4 s/clip, 300–500 KB |
| 1 keyframe 768 px (`-ss` trước `-i`) | ~0,1 s, 40–60 KB |
| Tách audio 16 kHz mono (194 s) | 0,4 s |
| `-c copy` xin 8 s | ra **8,7–13,0 s**; keyframe gốc cách nhau 2–5 s → ranh giới lệch tới ~5 s |

→ Xác nhận quyết định D3: **encode lại** (nhanh, đủ chính xác); `-c copy` chỉ làm tùy chọn.

## 3. Whisper — faster-whisper 1.2.1, `small`, CPU `int8`, `vad_filter=True`
- Tải model + nạp: 22 s. Phiên âm 194 s audio: **134 s** (~0,7× thời gian thực).
- **Audio của video LASI là tiếng Thái** (phát hiện `th`, độ tin cậy 0,96), 76 đoạn; chữ ra khá lỗi. Mặc định `language="vi"` của spec sẽ ra chữ rác trên video này.
- Hệ quả: (a) thêm `--language auto` (bỏ tham số `language` để Whisper tự nhận diện) và ghi `language` thật vào `TranscriptSegment`; (b) video LASI **không phải ví dụ tốt cho lời bình tiếng Việt** (spec 04 `propose-reasons` cần lời chuyên gia tiếng Việt); (c) Whisper `small` hợp với việc chạy ngoài giờ cao điểm, cho `--model` cấu hình được (`tiny`/`base` nếu cần nhanh).

## 4. MediaPipe Hands
| Bản | Kết quả |
|---|---|
| `mediapipe 1.0.1` | Cài được, nhưng API cũ `solutions.hands` **đã bị bỏ**; `tasks.vision.HandLandmarker` cần tải thêm model (7,8 MB) và **abort ở tầng C++** (`Check failed: service_ Service is unavailable`, Metal helper) trên macOS, cả khi ép `delegate=CPU`. Lỗi này kéo sập cả tiến trình Python, không bắt được bằng `try/except`. |
| `mediapipe 0.10.21` | Chạy được (`solutions.hands`), quét 968 khung trong 21 s. Nhưng nó **hạ numpy 2.4.6 → 1.26.4** và opencv 5.0 → 4.11; đây là xung đột với phần còn lại của dự án |
| Hiệu quả trên video LASI | Chỉ thấy tay ở **3%** số khung (nhiều cảnh toàn cảnh, robot, cảnh phỏng vấn) → ít ý nghĩa để cắt đoạn |

→ T03-4 (`hand_activity`) **rủi ro cao, giá trị thấp** trên dữ liệu đang có. Nếu làm: chạy trong **tiến trình con** để một lần abort không giết cả lệnh, thất bại thì rơi về `scene` (đúng AC-04), và cài ở môi trường riêng, không đưa vào extra `video` chung.

## Quyết định rút ra
1. Giữ nguyên các quyết định D1–D8, D10, D12 của `03-video-spec.md`; **D3 được xác nhận bằng số đo**.
2. `KNOWHOW_SCENE_THRESHOLD` mặc định **20**.
3. Whisper: `--language` mặc định `vi` nhưng nhận `auto`; thêm `--model`.
4. T03-4 xuống cuối hàng đợi, làm theo cách cách ly tiến trình, hoặc bỏ nếu hết thời gian.
5. Phụ thuộc mới cho extra `video`: `scenedetect` (Must), `faster-whisper` (Should). `mediapipe` **không** đưa vào.

## 5. motion_score — calibrate (T03-7, 4/10)
ffmpeg đọc video ở 5 fps, xám 160x90: 3,3 s cho 194 s video. So 4 cách gộp chênh lệch khung theo từng cảnh của `groundtruth.json` (26 cảnh `work` vs 24 cảnh tĩnh: phỏng vấn, logo, tiêu đề, overlay, họp, tham quan, toàn cảnh):

| Cách gộp | AUC (work > tĩnh) | `work` p25/50/75 | tĩnh p25/50/75 |
|---|---|---|---|
| mean | 0,91 | 0,051 / 0,059 / 0,081 | 0,007 / 0,021 / 0,033 |
| **median** | **0,93** | 0,041 / 0,054 / 0,073 | 0,003 / 0,006 / 0,010 |
| p75 | 0,92 | 0,049 / 0,061 / 0,081 | 0,005 / 0,009 / 0,016 |
| trung bình bỏ 10% cao nhất | 0,92 | 0,039 / 0,052 / 0,068 | 0,003 / 0,007 / 0,012 |

Chọn **median** (bền với điểm cắt cảnh: chênh lệch toàn video p99 = 0,27, max = 0,63 đều là điểm cắt) và `scale = 0,1`: cảnh `work` rơi 0,4–0,7, cảnh tĩnh dưới 0,15, khớp ngưỡng 0,3/0,6 của spec 04. Nhãn còn `draft`; số này là tham khảo.

## 6. hand_activity — triển khai (T03-4, 4/10)
Làm đúng hướng đã ghi ở mục 4: MediaPipe 0.10.21 trong **tiến trình + môi trường riêng** (`uv run --no-project --python 3.11 --with mediapipe==0.10.21`; ~16 s cho video 194 s, lần đầu tải gói), worker chỉ in JSON vị trí cổ tay; toàn bộ logic cắt nằm trong `hand_activity.py`, kiểm được không cần MediaPipe.
- **Cô lập:** kiểm bằng tiến trình con thật gọi `os.abort()` (SIGABRT như MediaPipe 1.0.x): cha vẫn sống, `SegmenterError`, chuỗi rơi về `scene`.
- **Video LASI:** thấy tay ở 32/968 mẫu (3,3%); cửa sổ 20 s dày nhất 14%. Tốc độ cổ tay đo được 0,1–1,7 (đơn vị ảnh/giây), p50 = 0,18, p75 = 0,68. Dưới ngưỡng hiện diện 10% nên bị từ chối và rơi về `scene` kèm "3% số khung".
- **Nếu không có ngưỡng hiện diện:** toàn video cho 5 điểm cắt, đều là chỗ tay vắng mặt chứ không phải chỗ nghỉ. Đó là lý do có ngưỡng.
- **Hạn chế đã biết:** MediaPipe hay mất dấu tay 1–2 mẫu ngay giữa chuyển động; vì khung không thấy tay tính là nghỉ nên có thể ra điểm cắt thừa (đoạn < 3 s bị gộp lại ở bước hậu xử lý nên hại nhỏ). **Chưa có ca dương thật** để chỉnh `valley_ratio`/`min_presence`: cần video quay tại trạm có người thao tác.
- **Lỗi phụ tìm ra:** `import scenedetect` nạp luôn PyAV (có mặt do faster-whisper) cùng OpenCV → macOS in cảnh báo "duplicate class ... mysterious crashes". Đã chặn PyAV trong lúc import `scenedetect` (nó coi PyAV là tùy chọn).
