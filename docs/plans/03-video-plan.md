# Plan — Video capture (Việt Hoàng)

Spec: `docs/plans/03-video-spec.md` · Deadline nộp: 12/10/2026 · Hôm nay: 4/10 (còn 8 ngày).
Quy trình mỗi task theo CLAUDE.md: viết test từ AC trước → code tối thiểu → `make check` xanh → tick task và ghi changelog trong spec 03.

## Thứ tự và phụ thuộc
```
T03-0 spike ─► T03-1 probe ─► T03-2 cắt + hậu xử lý ─► T03-3 keyframe + clip ─► T03-6a nhãn ─► [MỐC 1]
                                                                                          │
                          T03-7 motion_score ◄──────────────────────────────────────────┤
                          T03-5 transcribe + align ◄────────────────────────────────────┤
                          T03-4 hand_activity ◄─────────────────────────────────────────┤
                          T03-6b recall-audio ◄── T03-5 ─────────────────────────────────┘
```
**MỐC 1** (Must xong): `knowhow video segment` ra `segments.json`; `knowhow vlm describe <video_id>` đọc được. Đây là thứ Phúc đang chờ.

## Giai đoạn 0 — Điều kiện trước (4/10)
| Việc | Ai | Ra gì |
|---|---|---|
| Giải conflict nhánh ingest với `main` (store, cli.py, pyproject, uv.lock) | Hoàng + Trung | Nhánh video tách từ `main` mới nhất |
| Cài `ffmpeg` (`brew install ffmpeg`) | Hoàng | `ffmpeg -version` chạy được |
| Báo Phúc: phần video là module riêng, không đụng code spec 04 | Hoàng | Thông báo (không cần Phúc sửa gì) |
| Hỏi Đạt nguồn 3 video mẫu | Hoàng | Danh sách file và nguồn |
| **T03-0 spike** | Hoàng | Ghi chú `docs/plans/03-spike-notes.md` |

**T03-0 spike** (S, nửa ngày): trên video thật (hoặc video tổng hợp nếu chưa có) đo: tốc độ ffmpeg cắt/encode, PySceneDetect có ra điểm cắt hợp lý không, `mediapipe` có cài chung được với `opencv-python-headless` không (`uv pip install --dry-run` rồi thử thật), faster-whisper `small` chạy bao lâu trên CPU với 1 phút audio. Điểm dừng: nếu `ffmpeg` hoặc `scenedetect` không chạy được thì dừng, báo Trung.

## Giai đoạn 1 — Must (5–7/10)
| Task | Cỡ | AC | Ghi chú |
|---|---|---|---|
| **T03-1** probe + `VideoAsset` + validator | S | — | `ffprobe` JSON → model; `video_id_for` viết riêng trong `capture/video/`, kèm test hợp đồng khớp bản của Phúc (D11b) |
| **T03-2** `Segmenter` (scene, fixed_window) + hậu xử lý | M | AC-01..03 | Interface `Segmenter` + `FakeSegmenter`; rơi về `fixed_window` khi < 3 đoạn; đo scene vs `groundtruth.json` |
| **T03-3** keyframe (3 JPG, 768 px) + clip (H.264, 640 px, không audio) | M | AC-01 | ffmpeg; ghi qua tệp tạm; cache theo tên; test cần ffmpeg tự skip |
| **T03-6a** lan truyền `data_classification`, `--classification` bắt buộc, `store.py` ghi `segments.json`/`asset.json` | S | AC-07, AC-11 | Ghi nguyên tử; đổi nhãn → lỗi trừ `--force` |
| CLI `knowhow video probe|segment` + đăng ký trong `core/cli.py` | S | — | Thay placeholder `video` |
| Test hợp đồng với spec 04 | S | — | `video_id_for`/`window_bounds` khớp `vlm.sweep.windows`; `segments.json` do spec 03 sinh được `vlm describe` đọc (provider `fake`). Không sửa file nào của spec 04 |

**Mốc 1:** chạy `video segment` trên video mẫu → `vlm describe <video_id>` (provider `fake`) chạy được.

## Giai đoạn 2 — Should (8–10/10)
| Task | Cỡ | AC | Ghi chú |
|---|---|---|---|
| **T03-7** `motion_score` | M | AC-10 | cv2 chênh lệch khung; hiệu chuẩn bằng `groundtruth.json` |
| **T03-5** `transcribe` + `align_transcript` | M | AC-05, AC-06 | `Transcriber` + `FakeTranscriber`; `vad_filter`; không audio → `[]` |
| **T03-6b** `--recall-audio` | S | AC-08 | `offset`, `source="cued_recall"`, lỗi khi thiếu `asset.json` |
| **T03-4** `hand_activity` (MediaPipe) + fallback | M | AC-04 | Spike: 1.0.1 abort C++, 0.10.21 hạ numpy, chỉ thấy tay 3% khung LASI. Nếu làm: tiến trình con, lỗi/thiếu → rơi về `scene`; cuối hàng đợi hoặc bỏ |

Thứ tự trong giai đoạn: T03-7 trước (spec 04 hưởng lợi ngay), rồi T03-5, T03-6b, cuối cùng T03-4 (rủi ro cao nhất, giá trị thấp nhất).

## Giai đoạn 3 — Tích hợp và đệm (11–12/10)
- Chạy end-to-end: `video segment` → `video transcribe` → `vlm describe` trên video mẫu; `transcript_excerpt` đi vào evidence.
- Ghép với `make demo` (spec 08 T08-6) cùng đội.
- Đệm cho lỗi ffmpeg/Whisper và chờ duyệt.

## Phân cấp ưu tiên (Điều 7)
- **Must:** T03-1, T03-2, T03-3, T03-6a, CLI.
- **Should:** T03-7, T03-5, T03-6b, T03-4 — không làm trước khi Must xong.
- **Could (không làm):** thêm `method` mới, tách đoạn theo giọng nói, nhận diện thao tác bằng pose.

## Việc cần người khác
| Việc | Ai | Cần trước |
|---|---|---|
| Xác nhận owner S1-2/S2-6 | Trung/Đạt | 5/10 |
| 3 video mẫu + nguồn/quyền | Đạt (S0-7) | 6/10 |
| Duyệt `groundtruth.json` | Đạt/Phúc | 8/10 (trước khi chốt số đo) |
| Thống nhất `video_id` với endpoint upload | Người làm backend | 7/10 |
| Duyệt các diff ở spec §10 | Trung | 8/10 |

## Kiểm tra trước khi đóng từng task
1. Mỗi `AC-xx` có test `test_ac_xx_...`; test không gọi mạng; test cần ffmpeg/model thật tự skip khi thiếu.
2. `make check` xanh.
3. Không commit video/audio thật ngoài `data/samples/` (Điều 2); `data/work/` không commit.
4. Tick `[x]` task và ghi 1 dòng changelog vào spec 03.
