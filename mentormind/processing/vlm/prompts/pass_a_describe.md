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
