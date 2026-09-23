# Mentor Mind — Accumulate Master Know-How for AI to Learn

> Denso Hackathon · AI Challenge
> Số hóa bí quyết chuyên gia trong nhà máy — capture tri thức không cần viết tài liệu thủ công.

## Đề bài

Xây dựng hệ thống thu thập workflow và cách suy luận của chuyên gia vào một
knowledge base, kết hợp LLM để tái sử dụng tri thức cho các tác vụ tương tự —
không cần viết tài liệu thủ công.

**Deliverables :** Standardized Knowledge Capture Template ·
Knowledge Base · LLM Assistant · Usefulness Evaluation Report.

## Ý tưởng

Thiết bị capture ghi lại thao tác của chuyên gia tại trạm làm việc. Chuyên
gia dừng lại giải thích bằng lời — và **nhận benefit/ghi nhận** cho việc đó,
thay vì bị âm thầm khai thác. AI (VLM + LLM) chuyển video và lời giải thích
thành hồ sơ công đoạn có cấu trúc, chuyên gia duyệt, rồi nạp vào Knowledge
Graph + Vector Store để AI Agent hỏi-đáp và truy nguyên nhân lỗi.

Chi tiết kiến trúc: [`docs/architecture.md`](docs/architecture.md)

## Kiến trúc tóm tắt
<img width="1280" height="698" alt="image" src="https://github.com/user-attachments/assets/be178b8a-7d39-45b3-9b9a-fe442c0bec6d" />
