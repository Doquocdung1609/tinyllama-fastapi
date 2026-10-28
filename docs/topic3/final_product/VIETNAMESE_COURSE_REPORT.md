# Báo cáo khóa học — Financial Intelligence Studio

## Bài toán

Báo cáo tài chính chứa bảng nhiều kỳ, đơn vị và phiên bản filing. Một đoạn tìm được có thể liên quan về từ khóa nhưng sai công ty hoặc sai cột kỳ. Sản phẩm này giúp người học tìm bằng chứng, so sánh BM25/Dense/Hybrid và chỉ công bố số khi ánh xạ được ô nguồn SEC đúng phạm vi.

## Thiết kế

Giao diện sáu trang theo bảy concept được cung cấp; hệ màu navy/blue/cyan, card sáng, điều hướng gọn và bố cục xếp dọc ở màn hình nhỏ. Hai luồng chính dùng cùng nguồn SEC đã pin. PDF cá nhân được tách workspace, tạo BM25 bằng SQLite FTS5, Dense bằng Nomic/Qdrant và Hybrid bằng RRF k=60. Viewer mở trang PDF thực và tô sáng cụm được `page.search_for` xác nhận; nguồn SEC có URL chính thức và locator, không dựng anchor giả.

Financial AI dùng D1 để hiểu issuer/kỳ, D2 để đọc ô nguồn và D4 để tính `Decimal`. Khi thiếu kỳ, unit hoặc nguồn, phản hồi là trạng thái từ chối. Demo P&G NET SALES trả 23,276,000,000 USD từ ô 23,276 với scale 1,000,000, kỳ ba tháng kết thúc 2026-09-30 và accession `0000080424-26-000256`. Câu hỏi Costco năm 2031 trả `NEEDS_CLARIFICATION` và không có số.

## Kết quả chạy thực

Trình duyệt đã mở đủ sáu trang, upload PDF fixture tổng hợp 77.3 KiB, quan sát READY, tìm bằng ba mode, mở PDF trang 1 với `EXACT_PDF_TEXT_MATCH`, so sánh ba kênh cùng generation và mở filing HD chính thức trên sec.gov. HTTP và UI đều xác nhận ca SEC P&G thành công và ca thiếu chứng cứ từ chối. Full regression: **590 passed, 1 warning**; lệnh và phạm vi chi tiết ở [E2E report](END_TO_END_TEST_REPORT.md). Các ảnh chụp là giao diện thật dưới [`screenshots/`](screenshots/); bảy ảnh đầu vào chỉ là concept, không cung cấp ground truth.

## Kết luận trung thực

Đây là nguyên mẫu demo cục bộ có chứng cứ cho một số câu hỏi thực SEC; không chứng minh độ chính xác cho mọi filing/câu hỏi, không có kết luận Hybrid vượt BM25 và không chứng nhận dùng trong sản xuất. Dữ liệu SEC/Qdrant lịch sử và các đánh giá đã tiêu thụ được giữ nguyên. Bước quyết định tiếp theo của chủ sở hữu là xem Draft PR, kiểm tra các snapshot địa phương cần cho demo và cân nhắc giới hạn hạ cánh chính xác vào ô SEC.
