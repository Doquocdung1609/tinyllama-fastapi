# Nghiệm thu cục bộ V4

## Nguồn SEC47

- Danh mục có **47 accession / 10 ticker**. Đã xác nhận **0** nguồn trùng SHA.
- **45** bản EDGAR xác minh danh tính, SHA lệch bản nghiên cứu. **2** filing cần xem lại danh tính hoặc exhibit.
- **45** có dữ liệu đã parse, **45** có BM25 xuất bản, **0** có Dense READY trong SEC47. Kho demo cũ có bốn filing hoạt động trên các generation có Dense.
- `chat_numeric` ghi đúng các accession đã có phép thử số thành công trong lần chạy. Các filing có BM25 chưa được chấm Chat từng accession.

## API · câu trả lời và ô nguồn

| Ca | Đánh giá | Giá trị từ ô nguồn hoặc kết quả | Filing / trang PDF | Giây |
| --- | --- | --- | --- | --- |
| cost-quarter | PASS | 69,154 (2026-05-10) | 0000909832-26-000051 | 4.307 |
| cost-quarter-warm | PASS | 69,154 (2026-05-10) | 0000909832-26-000051 | 0.388 |
| cost-12w | PASS | 69,154 (2026-05-10) | 0000909832-26-000051 | 0.626 |
| cost-36w | PASS | 203,374 (2026-05-10) | 0000909832-26-000051 | 0.457 |
| cost-prior | PASS | 61,965 (2025-05-11) | 0000909832-26-000051 | 0.453 |
| cost-assets | PASS | 86,430 (2026-05-10) | 0000909832-26-000051 | 0.755 |
| hd-13w | PASS | 47,861 (2026-08-02) | 0001628280-26-058715 | 1.614 |
| hd-26w | PASS | 89,626 (2026-08-02) | 0001628280-26-058715 | 0.542 |
| hd-assets | PASS | 109,384 (2026-08-02) | 0001628280-26-058715 | 0.254 |
| hd-ambiguous | PASS | SEC_PERIOD_DURATION_REQUIRED | — | 0.62 |
| pg-cross-generation | PASS | 21,235 (2026-03-31), 23,276 (2026-09-30) | 0000080424-26-000060, 0000080424-26-000256 | 15.24 |
| pg-prior-year | PASS | 22,386 (2025-09-30), 23,276 (2026-09-30) | 0000080424-26-000256 | 0.833 |
| issuer-conflict | PASS | SEC_COMPANY_SCOPE_AMBIGUOUS | — | 11.991 |
| federated-search | PASS | 10 citation kết quả, 2 generation | 0000080424-26-000256, 0000080424-26-000060 | 5.865 |
| pdf-multi | PASS | Tìm bảng cân đối trong hai PDF | PDF 31, PDF 34, PDF 3, PDF 6 | 8.18 |
| pdf-apple | PASS | 26.23 | PDF 32 | 29.066 |
| apple | PASS | 391,035 (2024-09-28), 416,161 (2025-09-27) | 0000320193-24-000123, 0000320193-25-000079 | 32.492 |
| apple-income | PASS | SEC_COMPARISON_DURATION_CONFLICT | 0000320193-24-000123, 0000320193-23-000106 | 50.537 |
| apple-assets | PASS | 364,980 (2024-09-28), 359,241 (2025-09-27) | 0000320193-24-000123, 0000320193-25-000079 | 0.471 |
| microsoft | PASS | 88,136 (2024-06-30), 101,832 (2025-06-30) | 0000950170-24-087843, 0000950170-25-100235 | 76.455 |
| microsoft-revenue | PASS | 245,122 (2024-06-30), 281,724 (2025-06-30) | 0000950170-24-087843, 0000950170-25-100235 | 1.523 |
| microsoft-assets | BLOCKED | ReadTimeout | — | 90.025 |
| bidv-restatement | PASS | 1114 | PDF 7, PDF 4 | 25.876 |
| apple-margin | PASS | 38.60, 104.89 | PDF 27 | 16.272 |
| hpg-separate | PASS | SOURCE_EXCERPTS | PDF 1, PDF 2 | 5.699 |
| apple-income-comparable | PASS | 93,736 (2024-09-28), 112,010 (2025-09-27) | 0000320193-24-000123, 0000320193-25-000079 | 0.625 |

So sánh nhiều filing thật đạt **6/7** ca trong danh sách. Ca Apple FY2023/FY2024 từ chối so sánh số tuyệt đối vì số tuần khác nhau, và được chấm riêng như negative case.

## Hiệu năng

- Trước sửa, cùng câu hỏi COST three months ended 2026-05-10 hết hạn đọc sau 180 giây. Đó là một mẫu timeout, không phải p95 baseline.
- Sau sửa, cùng câu trả **4.307 s** ở lượt đầu và **0.388 s** ở lượt lặp.
- Thống kê mô tả 9 lượt COST/HD xác minh thành công trong lần đo, gồm nhiều trạng thái cache. p50 **0.542 s**, p95 theo nearest rank **4.307 s**. Số mẫu nhỏ và điều kiện chưa ghép cặp với baseline.
- Microsoft FY2024/FY2025 lần đầu mất 76,455 s cho lợi nhuận ròng và 1,523 s cho doanh thu trên cùng hai filing ở lượt sau. Một ca tổng tài sản Microsoft khác cặp kỳ chạm timeout 90 s. Tối ưu sau lần đo giới hạn truy xuất bằng chứng khi chưa xác minh được số, và giữ kết quả cần làm rõ phạm vi mà không chạy thêm tìm kiếm.
- Chưa đo RAM peak hoặc phân phối cold/warm đầy đủ. Máy Windows có lúc còn dưới 1 GiB RAM khả dụng trong thời gian chạy import và kiểm thử.

## Trình duyệt và hồi quy

- **PASS** · pdf-multi
- **PASS** · sec-federation
- **PASS** · mobile-picker
- Chromium desktop 1366×768 và 1920×1080 cùng mobile 390×844. Trình duyệt mở PDF sau reload, xác nhận đúng hai accession SEC và hai ô được chọn qua endpoint viewer.
- **PASS** · Kho SEC trên Chromium hiển thị 45/47 cùng trạng thái BM25 và Dense.
- Ảnh cục bộ gồm `pdf-1366.png`, `pdf-citation.png`, `sec-1920.png`, `sec-citation.png`, `pdf-mobile.png` và `sec-library.png`. Browser zoom 125% chưa được đo.
- Frontend production build và 36 Vitest trên Node 24 đã đạt. Hai lỗi CI phát hiện ban đầu đã được sửa; Python và frontend xanh trên commit `d775d3c`. Nhóm 19 ca Python liên quan đạt sau các sửa tiếp theo. Truy vấn trạng thái CI ở HEAD mới hơn chưa trả được kết quả.

Các tính năng Dense mới, kiểm thử Chat từng accession, và báo cáo RAM/latency cold-warm đầy đủ vẫn chưa nghiệm thu.
