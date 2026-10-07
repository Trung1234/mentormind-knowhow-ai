# Chạy full flow trên UI — VLM qua ngrok

Từ upload video + PDF → duyệt bước → trợ lý → truy nguyên lỗi, chạy trên máy của bạn (macOS).
VLM/LLM là Ollama `qwen3-vl:8b` trên **một Mac khác, mở ra ngoài bằng ngrok**.

```
Máy bạn: UI :5173 → API :8000 → Neo4j + Postgres (Docker) · Whisper, bge-m3, Docling (CPU)
                              └→ https://user:pass@<tên>.ngrok-free.dev/v1 → Mac chạy Ollama
```

## 0. Mac chạy Ollama (bỏ qua nếu ngrok đang chạy)

Cần quyền SSH tới repo `vlm-engine` (submodule) và tài khoản ngrok (`ngrok config add-authtoken …`).

```bash
git submodule update --init 3rdparty/vlm_server
NGROK_BASIC_AUTH=user:matkhau bash 3rdparty/vlm_server/scripts/serve-ollama.sh --ngrok   # in ra URL ngrok
```

Lần đầu kéo model 6,1 GB. Chi tiết: [test-guide.md §4.4.1](test-guide.md), [.secrets/README.md §4.4](../.secrets/README.md).

## 1. Công cụ (máy bạn)

```bash
brew install uv ffmpeg node
open -a Docker            # Docker Desktop phải đang chạy
```

## 2. Code + dependency

```bash
git clone git@github.com:Trung1234/mentormind-knowhow-ai.git && cd mentormind-knowhow-ai
git checkout phuc-nguyen/spec03-video        # sau khi PR #18 merge: main
uv sync --all-extras
npm --prefix mentormind/frontend ci
cp .env.example .env
```

Sửa trong `.env`:

```bash
KNOWHOW_VLM_BASE_URL=https://user:matkhau@<tên>.ngrok-free.dev/v1   # URL ngrok ở bước 0, thêm /v1
KNOWHOW_API_AGENTS=live
KNOWHOW_VIDEO_METHOD=scene          # video đã dựng, nhiều cảnh (LASI); quay liền 1 người: hand_activity
```

Kiểm tra:

```bash
uv run knowhow vlm ping --frames 8  # dòng cuối PASS (qua ngrok trên Mac 16 GB: 1–3 phút)
```

404 `model 'qwen3-vl:8b' not found` = Mac bên kia chưa kéo xong model; chờ rồi ping lại.

## 3. DB + graph + dữ liệu Sigma

```bash
docker compose --profile lite up -d postgres neo4j       # chờ healthy (~30 s): docker compose ps
uv run knowhow kg init
uv run knowhow kg load-sigma --classification synthetic  # 6 lot cho trang Truy nguyên lỗi
```

## 4. Bật API + UI (2 terminal)

```bash
caffeinate -i uv run uvicorn mentormind.backend.app.main:app --port 8000
npm --prefix mentormind/frontend run dev
```

Mở **http://localhost:5173**. Không dùng `127.0.0.1` vì CORS chỉ cho `localhost`.
Đừng dùng `make start` trên DB trống: script đó seed 4 bước giả `WP-PACK01-001..004`.

Lần đầu tự tải: Docling/OCR, bge-m3 (~2 GB), Whisper small (~480 MB), model tay MediaPipe (8 MB),
model làm mờ mặt YuNet (230 KB).

## 5. Thao tác trên UI

| # | Tab | Làm | Kết quả mong đợi |
|---|---|---|---|
| 1 | Tải dữ liệu → Video | Chọn video, mã công đoạn `PACK01`, cách cắt (hoặc "Mặc định của máy chủ"), nhãn **Công khai** → Tải lên & phân tích | Tiến độ 5 bước: cắt đoạn → nhận dạng lời nói → VLM mô tả → gộp bước → đề xuất lý do; xong thì ra bảng bước nháp có keyframe |
| 2 | Tải dữ liệu → Tài liệu | `data/demo/packing/packing_sop.pdf`, nhãn **Dữ liệu tổng hợp** → Tải lên & xử lý | 3 trang → 13 chunk (~40 s); chạy được song song với video |
| 3 | Duyệt (hoặc nút "Duyệt các bước này") | Xem keyframe, clip, lời chuyên gia của bước → sửa nếu cần → Approve & Verify | Thông báo `APPROVED`; bước vào Neo4j + pgvector |
| 4 | Trợ lý | `PACK01` + câu hỏi dùng từ của bước đã duyệt, VD "Đặt linh kiện vào hộp như thế nào?" | Câu trả lời + trích dẫn (bấm → keyframe). Câu ngoài phạm vi bị từ chối |
| 5 | Truy nguyên lỗi | Lot `LOT-PACK01-001` → Investigate Root Cause | Chuỗi 5-Why + giả thuyết + biện pháp + ghi chú "giả thuyết, chưa phải kết luận" |

Kiểm tra: `uv run knowhow kg stats` → số `Step` = số bước đã approve.

### Lưu ý khi VLM đi qua ngrok

- **Nhãn dữ liệu:** URL ngrok bị coi là cloud. Chỉ dùng nhãn *Công khai* hoặc *Dữ liệu tổng hợp*;
  dữ liệu *Mật – dữ liệu nhà máy* bị chặn, không gửi đi (DataGuard).
- **Mặt người tự làm mờ** trước khi khung hình gửi tới VLM; tên/số điện thoại trong text bị che.
- **Chậm:** mỗi đoạn video tốn 2 lượt VLM, mỗi lượt vài phút trên Mac 16 GB. Video LASI (31 phút, cắt
  theo cảnh → 30 đoạn) mất khoảng 1 giờ trên GPU MI250, trên Mac lâu hơn nhiều. Thử nhanh bằng 3 phút đầu:
  `ffmpeg -t 180 -i "<video>.mkv" -c copy lasi-3m.mkv`.
- Mac chạy Ollama hoặc máy bạn ngủ → lượt VLM lỗi → job `failed`. Giữ cả hai máy thức (`caffeinate`).
- Tắt API giữa chừng → job đang chạy hiện `failed`; tải lên lại.

## 6. Dọn

```bash
# Ctrl+C: uvicorn, vite
docker compose --profile lite down -v                 # xoá DB + graph
rm -rf data/work                                      # upload, chunk, keyframe, clip, job
```

Giữ `~/.cache/huggingface` (bge-m3, Whisper, Docling) và model Ollama bên Mac kia để lần sau khỏi tải lại.

## 7. Kiểm tra code (không cần VLM)

```bash
KNOWHOW_API_AGENTS=mock KNOWHOW_EVAL_JUDGE=ragas make check                   # ruff + mypy + pytest
npm --prefix mentormind/frontend run build
```
