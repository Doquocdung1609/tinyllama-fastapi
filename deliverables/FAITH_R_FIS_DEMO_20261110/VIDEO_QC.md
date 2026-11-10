# Kiểm tra video cuối cùng

- File mở và phát thật bằng Chromium ở khoảng 00:26, 10:40 và 20:54. Đã giải mã khung hình, không có lỗi phát. PLAYBACK_QC.json lưu kết quả.
- Thời lượng 21 phút 19,233 giây. 1920 × 1080, 30 FPS, H.264, yuv420p. Không có thuyết minh âm thanh.
- FFmpeg đọc và giải mã toàn bộ file thành công. Số đoạn đen kéo dài từ một giây theo blackdetect là 0.
- Đã xem khung hình đầu, giữa, cuối, Kho tài liệu, bảng SEC và phần công thức Apple. Chữ đọc được ở 1080p. Trang dài được cuộn theo từng vùng.
- Token được cấp qua sessionStorage trước khi thao tác. Không hiển thị ô nhập khóa. Không thấy token hay cấu hình bí mật trong các khung hình đã kiểm tra.
- Các cảnh là video Playwright của React/FastAPI thật trên Windows, dùng nguồn cục bộ. Có cuộn trang, gõ câu hỏi, chọn phương pháp, chờ phản hồi và mở nguồn. Không dựng video bằng ảnh tĩnh.
- Các ảnh PNG đi kèm phục vụ kiểm tra chất lượng. Chúng không được sử dụng để thay khung hình trong MP4.
- Đoạn bổ sung công thức khôi phục hội thoại thật từ máy chủ và mở các bước tính trên React.
- Phần lớn giao diện dùng thanh điều hướng dạng icon. Đoạn metadata bổ sung mở thanh điều hướng đầy đủ.
- Một số điều khiển trong bảng Kho tài liệu bị giới hạn chiều rộng bởi bố cục hiện tại. Nội dung bảng nguồn và ô đã chọn được hiển thị trong viewer.
- Các khoảng dừng dành cho đọc kết quả được giữ trong bản quay. Không chấm thời gian dừng đọc như thời gian phản hồi của mô hình.
- SEC được kiểm tra bằng viewer nguồn lưu cục bộ. Không xác nhận truy cập website SEC.gov.
- Giới hạn sản phẩm được giữ nguyên. APPLE-02 trả sai loại chỉ tiêu và sai trang mục tiêu. HPG-OCR chưa trả số nợ và dẫn trang 5 thay vì trang 4. Nghiệm thu toàn bộ yêu cầu là PARTIAL.
- Ảnh kiểm tra theo mẫu không thay thế kiểm tra thủ công từng khung hình của toàn bộ video.

SHA256 — 4c0ffe7b9f13b4dc1b37824ef3d7c012b2c3f50b6226b883b534878ff10e5ee1
