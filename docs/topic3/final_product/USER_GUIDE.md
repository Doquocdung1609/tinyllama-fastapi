# Hướng dẫn sử dụng nhanh

1. Khởi động theo [Windows startup](WINDOWS_STARTUP.md), mở URL Streamlit được in ra.
2. **Kho tài liệu:** xem filing SEC hiện có. Chọn tab **Tải PDF lên**, dùng PDF không quá 20 MiB, nhập issuer/kỳ nếu biết, nhấn **Tải lên & lập chỉ mục**, rồi làm mới tới `READY`. Trạng thái `FAILED` có thể thử lại; xóa PDF riêng cần xác nhận.
3. **Tìm kiếm tài chính:** chọn `Hồ sơ SEC` hoặc `PDF của bạn`, nhập câu hỏi, chọn BM25/Dense/Hybrid RRF, top-k và bộ lọc. Nhấn kết quả để mở viewer. Với PDF, viewer hiển thị trang và vùng tô vàng; nhãn `EXACT_PDF_TEXT_MATCH` chỉ dùng khi cụm chữ thật được tìm trên trang. Với SEC, viewer cung cấp đoạn, issuer, accession, kỳ, SHA và link filing chính thức.
4. **Phân tích tài chính AI:** hỏi giá trị hoặc so sánh kỳ SEC được hỗ trợ. Đọc phép tính Decimal, từng ô nguồn, đơn vị, khoảng kỳ và cảnh báo trích xuất. Trạng thái từ chối nghĩa là hệ thống chưa có ô đủ tin cậy; không suy diễn số từ Search.
5. **So sánh truy xuất:** cùng câu hỏi được gửi qua ba phương pháp trên cùng generation. Xem rank B/D, phần chung và độ trễ. Không suy ra phương pháp nào tốt hơn từ một ví dụ. Chỉ xem Recall/MRR/nDCG khi có qrels thật và xem nhãn review của bộ dữ liệu.
6. **Hệ thống & cài đặt:** xem trạng thái FastAPI, Ollama, SEC index/vector, số PDF READY và tài nguyên; phần kỹ thuật chi tiết nằm trong mục mở rộng.

Các PDF demo trong repo là **fixture tổng hợp**, không phải tài liệu SEC. Dữ liệu người dùng được lưu tại `STUDIO_WORKSPACE_DIR` riêng; không tải PDF nhạy cảm vào môi trường demo dùng chung.
