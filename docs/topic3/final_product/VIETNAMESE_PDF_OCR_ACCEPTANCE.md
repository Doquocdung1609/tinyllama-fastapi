# Kiểm chứng PDF Việt Nam / OCR

Nguồn do chủ dự án cung cấp, không commit raw PDF hoặc index cá nhân.

| PDF | SHA256 | Kiểu trang gốc | Kết quả |
|---|---|---|---|
| 20260130-hpg-bao-cao-tai-chinh-rieng-cong-ty-me-va-giai-trinh-q4-2025.pdf | 4a92af827aaf1e73e017544d0ff20d0d14ae4d368bd9c90d5d6d60a28af8b447 | 24 trang: đầu chỉ signature text; 2–24 không có native text | OCR tuần tự, 64 chunks, READY |
| 20251023+-+BID+-+CBTT+Dieu+chinh+BCTC+2024+theo+ket+qua+KTNN.pdf | 2bed2b3c312c8149e6a2ff6ab80c694a4c710e82f65b1c35a1a943eae4fa32a6 | 8 trang: 1–2 scan, 3–8 native | mixed extraction, 23 chunks, READY |

Tesseract vie+eng và osd đã có tại máy, kiểm tra capability pack thực. HPG trang PDF 5 cần xoay 90° theo OCR: browser hiển thị đúng chiều, highlight từ “Doanh thu” trùng chữ thật. Số trang in trên trang đó là 4; không suy rộng mapping số trang in cho các trang khác. BIDV trang PDF 6 có native selectable layer và ba ô tổng tài sản được tô xanh đúng nguồn. Trang 3 BIDV là báo cáo riêng, không thay thế bảng hợp nhất trang 6.

Các page checkpoint lưu engine/dpi/rotation/word confidence/bbox/text/hash; retry dùng lại trang tốt. Layout V3 tái tạo từ checkpoint bất biến, fingerprint kết hợp page/source/layout. Khi thay fingerprint hoặc giá trị ô, fact cũ không còn đủ điều kiện. Chưa có bằng chứng mọi ô trên cả 32 trang đều đúng; trạng thái bảng vẫn TABLE_STRUCTURE_UNVERIFIED trừ ô đối chiếu cục bộ. Confidence cao không tự thành verified.

PASS: upload thực trong React, xử lý trang, Unicode, 15 request tìm kiếm, viewer, scan/native highlight, zoom/rotation, đối chiếu ô, Decimal, từ chối, upload lại và restart. Recovery trang lỗi/gián đoạn được kiểm tra bằng regression có điều khiển; không phá tiến trình OCR trên PDF cá nhân đang dùng chỉ để tạo lỗi minh họa.

Giới hạn: scan mờ, bảng nhiều cột/gộp ô, OCR ký tự sai và ngày/kỳ phức tạp vẫn cần đối chiếu ảnh. Không hứa tự động trích toàn bộ bảng chuẩn kế toán. OCR không có pack phải báo không sẵn sàng, không ngầm đổi model hoặc bịa text. GTX1650Ti chưa được chạy thử; máy này RTX3050 4GB, khoảng 15GB RAM, thực tế RAM rảnh biến động.
