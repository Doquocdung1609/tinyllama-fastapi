# PDF modality audit

## Bộ fixture

Mười PDF tổng hợp A–J bao phủ: văn bản tiếng Việt, text + table, báo cáo tài chính có số âm trong ngoặc, bar/line chart, pie chart, process diagram, scan ảnh, nhiều cột, bảng kéo dài hai trang và bảng song ngữ. Tất cả đã được render bằng Poppler và kiểm tra trực quan, không thấy chữ bị cắt hoặc tràn trang.

## Kết quả extraction

- Bảng: 5/5 trang bảng giữ đúng số cột, số hàng, đơn vị; số âm `(25)`/`(30)` được giữ; bảng I nối đúng từ trang 1 sang trang 2.
- Chart/diagram: 16/16 cặp nhãn/giá trị hoặc nhãn nút gốc được thu nhận từ native PDF text.
- Multi-column: fixture H được nhận diện đúng.
- Scan: fixture G được nhận diện là scan; OCR bị chặn rõ vì không có engine.
- Provenance: table/chart/figure chunk có page, source ID, modality và bbox.

Kết quả extraction không đồng nghĩa mọi câu hỏi generation đều đúng. Benchmark API thực tế có 15 PASS, 1 PARTIAL, 3 FAIL và 1 BLOCKED.
