# `.secrets/` — API key và cách thiết lập

Thư mục này chứa **mọi secret** của dự án: API key của cloud provider, token của server tự host.
Git chỉ theo dõi 2 file là hướng dẫn này và `secrets.env.example`; mọi file khác trong `.secrets/`
bị `.gitignore` chặn (luật ở `.gitignore` gốc: `.secrets/*`).

> **Luật bất biến (constitution Điều 2):** dữ liệu `factory_confidential` không bao giờ đi tới
> provider cloud. Việc này được chặn bằng code (`DataGuard`), nhưng key cloud vẫn chỉ nên dùng cho
> dữ liệu `public` (Assembly101, IKEA ASM, MECCANO) và `synthetic` (video đội tự quay).

## 1. Thiết lập lần đầu (2 phút)

```bash
cp .secrets/secrets.env.example .secrets/secrets.env
chmod 700 .secrets && chmod 600 .secrets/secrets.env   # máy dev dùng chung: chỉ bạn đọc được
$EDITOR .secrets/secrets.env                            # điền key của provider bạn dùng
uv run knowhow vlm providers                            # cột "api key" hiện ✓ khi đã nhận key
```

**Chỉ dùng server tự host (`local_openai`, mặc định) thì không cần key nào.**

## 2. Code đọc key như thế nào

| Biến | Ai đọc | Thứ tự tìm |
|---|---|---|
| `KNOWHOW_*` (vd. `KNOWHOW_VLM_API_KEY`) | `mentormind.core.config.Settings` | biến môi trường → `.secrets/secrets.env` → `.env` |
| Key theo vendor (`OPENROUTER_API_KEY`, ...) | `mentormind.core.config.secrets.lookup_secret` | biến môi trường → `.secrets/secrets.env` |
| `VLM_SERVER_API_KEY` | server `3rdparty/vlm_server` **và** client `local_openai` | biến môi trường → `.secrets/secrets.env` |

- Key được chọn theo provider đang dùng (`KNOWHOW_VLM_PROVIDER`). Có thể để sẵn key của nhiều vendor;
  đổi provider thì chỉ cần đổi `KNOWHOW_VLM_PROVIDER`.
- `KNOWHOW_VLM_API_KEY` nếu có giá trị thì thắng mọi key theo vendor. Để trống thì bị bỏ qua.
- Thiếu key của một provider cloud → lệnh báo rõ cần đặt biến nào, không bao giờ gửi request không có key.

## 3. Bảng provider (giá kiểm tra ngày 28/9/2026)

Tất cả đều là **Qwen3-VL-8B-Instruct**. Ảnh tính phí như token đầu vào (khoảng 115 token cho một khung
448×252), nên một lần gọi 48 khung tốn khoảng 5.5k token.

| `KNOWHOW_VLM_PROVIDER` | Biến key | Giá / 1M token (vào / ra) | Miễn phí | Ghi chú |
|---|---|---|---|---|
| `local_openai` | `VLM_SERVER_API_KEY` (tùy chọn) | 0 | — | GPU của đội, **provider duy nhất nhận được dữ liệu nhà máy** |
| `openrouter` | `OPENROUTER_API_KEY` | $0.117 / $0.455 (qua Alibaba), $0.25 / $0.75 (qua Parasail) | Không có bản `:free` cho model này | Đăng ký dễ nhất (Google/GitHub/email), hỗ trợ JSON schema. **Rẻ nhất khi trả phí**: khoảng $0.001 cho mỗi lần gọi 48 khung |
| `siliconflow` | `SILICONFLOW_API_KEY` | $0.18 / $0.68 | **$1 credit khi đăng ký**, khoảng 500 lần gọi 48 khung | Dùng trang quốc tế `siliconflow.com` (bản `.cn` cần SĐT +86). Chỉ có JSON mode, không có schema |
| `qwen_api` | `DASHSCOPE_API_KEY` | $0.18 / $0.70 (Singapore) | 1M token / 90 ngày (chỉ region Singapore) | ⚠️ **Alibaba ngừng `qwen3-vl-8b-instruct` lúc 00:00 ngày 10/10/2026 (UTC+8)**, trước hạn nộp bài |

Nguồn: [OpenRouter endpoints](https://openrouter.ai/api/v1/models/qwen/qwen3-vl-8b-instruct/endpoints),
[SiliconFlow](https://www.siliconflow.com/models/qwen3-vl-8b-instruct),
[Alibaba: giá](https://www.alibabacloud.com/help/en/model-studio/model-pricing),
[Alibaba: thông báo ngừng model](https://www.alibabacloud.com/en/notice/model_studio_notice_on_the_postponed_retirement_of_selected_legacy_models_7d0).
Giá và danh sách model của vendor thay đổi thường xuyên, hãy kiểm tra lại trước khi nạp tiền.

## 4. Lấy key từng provider

### 4.1 OpenRouter (`OPENROUTER_API_KEY`) — khuyến nghị cho bản demo trả phí
1. Vào https://openrouter.ai, đăng nhập bằng Google, GitHub hoặc email (không cần SĐT).
2. Vào **Settings → Credits**, nạp tiền bằng thẻ hoặc crypto. $5 là quá đủ cho cả hackathon.
3. Vào **Settings → Keys → Create Key**. Nên đặt credit limit cho key, ví dụ $5. Copy key dạng `sk-or-v1-...`.
4. Tùy chọn: ở **Settings → Privacy**, tắt các provider được phép train trên dữ liệu của bạn.
5. Ghi `OPENROUTER_API_KEY=sk-or-v1-...` vào `.secrets/secrets.env`, rồi kiểm tra:
   ```bash
   KNOWHOW_VLM_PROVIDER=openrouter uv run knowhow vlm ping --frames 48
   ```
   Sau ngày 10/10 route Alibaba có thể biến mất. Khi đó OpenRouter chỉ còn Parasail (đắt hơn, và theo
   tài liệu Parasail có thể giới hạn 8 ảnh mỗi request). Hãy chạy thử `--frames 48` sớm.

### 4.2 SiliconFlow (`SILICONFLOW_API_KEY`) — dùng thử miễn phí
1. Vào https://cloud.siliconflow.com, đăng ký bằng email hoặc Google.
2. Kiểm tra mục **Balance** đã có $1 credit tặng (chưa xác minh việc có cần thẻ hay không).
3. Vào **API Keys → Create new API key**, copy key dạng `sk-...`.
4. Ghi `SILICONFLOW_API_KEY=sk-...`, rồi kiểm tra: `KNOWHOW_VLM_PROVIDER=siliconflow uv run knowhow vlm ping`.

### 4.3 Alibaba Model Studio / DashScope, Singapore (`DASHSCOPE_API_KEY` + `DASHSCOPE_BASE_URL`)
Chỉ còn dùng được `qwen3-vl-8b-instruct` đến 00:00 ngày 10/10/2026 (UTC+8). Hướng dẫn từng bước kèm ảnh
màn hình và cách tránh bị trừ tiền nằm trong `guidance/alibaba-singapore.md`. Tóm tắt:
1. Tạo tài khoản https://www.alibabacloud.com. **Từ 15/9 phải hoàn tất thông tin tài khoản trước khi kích hoạt.**
2. Mở https://modelstudio.console.alibabacloud.com, chọn region **Singapore** ở góc trên bên phải,
   đồng ý điều khoản. Model Studio được kích hoạt và **tự cấp 1M token miễn phí cho mỗi model, trong 90 ngày**.
3. Vào **Free Quota**, tìm `qwen3-vl-8b-instruct` rồi bật **Free Quota Only**. Hết quota thì API trả lỗi
   `AllocationQuota.FreeTierOnly` thay vì trừ tiền.
4. Vào **API Key → Create API Key** (workspace mặc định, quyền All). Copy ngay **key** (dạng `sk-ws...`) và
   **API Host**, vì đóng hộp thoại là không xem lại được nữa.
5. Ghi vào `.secrets/secrets.env`:
   ```
   DASHSCOPE_API_KEY=sk-ws-...
   DASHSCOPE_BASE_URL=https://<API Host>/compatible-mode/v1
   ```
   `<API Host>` có dạng `{WorkspaceId}.ap-southeast-1.maas.aliyuncs.com`. Key chỉ dùng được đúng ở region của nó.
6. Kiểm tra: `KNOWHOW_VLM_PROVIDER=qwen_api uv run knowhow vlm ping`.

### 4.4 Server tự host (`VLM_SERVER_API_KEY`) — tùy chọn
Server `3rdparty/vlm_server` chỉ nghe trên `127.0.0.1`, nên thường không cần token. Nếu mở cho người
khác qua SSH tunnel hoặc LAN và muốn khóa lại:
```bash
echo "VLM_SERVER_API_KEY=$(openssl rand -hex 24)" >> .secrets/secrets.env
```
Khởi động lại server. Client `local_openai` tự gửi token này, không cần cấu hình thêm.

### 4.5 Hugging Face (`HF_TOKEN`) — tùy chọn
Model Qwen3-VL-8B-Instruct là public, tải không cần token. Token chỉ giúp tránh bị giới hạn tốc độ.
Lấy token ở https://huggingface.co/settings/tokens (quyền **Read**). Lệnh `hf` không tự đọc file này,
nên cần nạp vào shell trước:
```bash
set -a; source .secrets/secrets.env; set +a; cd 3rdparty/vlm_server && uv run hf download Qwen/Qwen3-VL-8B-Instruct
```

## 5. Thêm provider mới

Ví dụ một vendor khác có API tương thích OpenAI:
1. Thêm một dòng vào `mentormind/core/providers/openai_compat/endpoints.py` (`OPENAI_COMPAT_ENDPOINTS`): `base_url`,
   `is_cloud=True`, tên biến key (vd. `NEWVENDOR_API_KEY`), `json_mode`.
2. Thêm model id mặc định vào `mentormind/processing/vlm/providers/catalog.py`.
3. Thêm dòng `NEWVENDOR_API_KEY=` vào `secrets.env.example` và vào bảng ở mục 3.

Vendor không tương thích OpenAI: viết subclass `VLMProvider` trong
`mentormind/processing/vlm/providers/backends/`, gắn `@register_vlm("ten")` và import module trong
`mentormind/processing/vlm/providers/__init__.py`. Code nghiệp vụ không phải sửa gì (constitution Điều 5).

## 6. Sự cố thường gặp

| Lỗi | Nguyên nhân |
|---|---|
| `Thiếu API key cho provider '...'` | Chưa điền đúng biến nêu trong thông báo vào `.secrets/secrets.env` |
| `HTTP 401` | Key sai, hết hạn, hoặc dán nhầm key của vendor khác |
| `HTTP 402` (OpenRouter) | Hết credit, hoặc chạm credit limit của key |
| `HTTP 429` | Bị giới hạn tốc độ. Client tự retry tối đa 3 lần với backoff mũ (spec 04 FR-07) |
| `Chặn gửi dữ liệu factory_confidential tới provider cloud` | Đúng thiết kế: dùng `local_openai` cho dữ liệu nhà máy |

## 7. Khi lộ key
Thu hồi (revoke) key ngay trên trang của vendor, tạo key mới và sửa `.secrets/secrets.env`. Nếu key
đã lỡ vào một commit thì xóa file khỏi commit **chưa đủ**, vì lịch sử git vẫn còn key: phải revoke key.
