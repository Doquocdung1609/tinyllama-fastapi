# Hành trình demo — HTTP và Chromium thật

Code `209faf9988490ec9f8f6979f304b4e3852724d5a`, tiếp nối checkpoint `53a1ab2`. Live API và frontend prebuilt tại loopback cổng 18110; bearer lấy từ tệp runtime, không ghi vào bằng chứng. Chạy `node frontend/v7p_demo_rc_smoke.cjs` với Chromium đã cài. Không mock phản hồi. [Kết quả đầy đủ](V7P_RELEASE_CANDIDATE_RESULTS.json) chứa câu hỏi, trạng thái, giá trị, hash, citation và locator.

| Ca | Kết quả thực tế | Browser |
|---|---|---|
| Apple net income FY2025 | SUPPORTED / CELL_VERIFIED; 112010 MILLION_USD; PDF trang 32 | PASS; mở PDF đúng trang, có ít nhất ba highlight xác minh; quay lại giữ chat và tài liệu |
| Địa lý doanh thu lớn nhất Apple | Americas, 178353 MILLION_USD; trang 25; năm 2025 | PASS |
| Apple tăng trưởng FY2024–2025 | 6.43%; hai ô Total net sales trang 32 | PASS |
| HD Total assets | 109384000000 USD; giao diện 109.384 triệu USD; instant 2026-08-02 | PASS; bảng/cell gốc, chú giải màu đúng; desktop và 390px không tràn toàn trang |
| Link SEC chính thức | Đúng URL filing HD; SEC trả trang chặn tự động | PASS cho link/cảnh báo; nội dung ngoài EXTERNAL_ACCESS_BLOCKED, không xác nhận exact-cell landing |
| Upload không nhập metadata | Hai trang, năm chunks, READY; tự metadata; hiệu chỉnh explicit giữ sau re-upload và reload | PASS; tên file/READY còn hiển thị |
| Follow-up “Còn năm 2024?” | 391035 MILLION_USD, kỳ 2024-09-28, nguồn trang 32 | PASS |
| Sai công ty / FY2037 | QUERY_CONTEXT_CONFLICT / INSUFFICIENT_EVIDENCE; không có số trả lời | PASS |
| HPG scan | READY 24 trang/64 chunks; BM25 có 5 hits; số liệu bị từ chối AMBIGUOUS_METRIC_DEFINITION | PASS trong phạm vi tìm kiếm + từ chối; không chứng nhận numeric OCR |
| Research Lab | Mở được, nhãn lịch sử/provisional rõ ràng | PASS; không chạy benchmark/sealed questions |

Upload mới là **mẫu dẫn xuất hai trang** 1 và 32 từ PDF Apple gốc, SHA `2ba930aa3611c0e5420288a96b204c1393163e38d1d92cdf0cfa98401b2c6f0e`, không phải toàn bộ filing, không dùng để chứng nhận QA tài chính. Script xóa đúng tài liệu mẫu vừa tạo bằng ID sau kiểm tra; không xóa Apple/HPG gốc. HPG là index OCR đã có, không OCR lại. Nhãn issuer HPG đang có hiệu chỉnh từ trước; giữ nguyên hiệu chỉnh đó, không coi nó là chứng thực nội dung nguồn.

Một lượt browser ban đầu tái hiện lỗi mất advanced SEC answer sau back; đã sửa và thêm regression scope. Lượt cuối hoàn tất **10/10**, `page_errors=[]`, tài liệu mẫu đã dọn. Không đếm lượt thất bại ban đầu là PASS. Không đo latency hay suy luận độ chính xác tổng quát từ các control này.
