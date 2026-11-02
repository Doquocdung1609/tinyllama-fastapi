# Kịch bản bảo vệ — khoảng 8 phút

## Khởi động Windows

Checkout đúng nhánh PR35; cần `.venv` với dependencies dự án, Node 24, frontend đã build. Nomic đã cài và Ollama chạy cho embedding upload; không tự tải weights. HPG scan cần Tesseract vie+eng. Máy khác phải cấu hình các research roots tới snapshot/vector đã xác minh của chính máy đó; Git source code không tự cung cấp dữ liệu runtime hoặc khóa truy cập.

Build một lần hoặc sau khi cập nhật frontend:

```powershell
cd frontend
npm ci
npm run build
cd ..
```

Từ repo, một lệnh khởi động:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_financial_studio.ps1 -Mode Prebuilt -OpenBrowser
```

Mở URL `/app/` được in ra, nhập khóa cục bộ từ `tmp/studio-runtime/access-token.txt`, không chiếu khóa lên màn hình demo. Mặc định cổng 8110; kiểm thử RC dùng `-ApiPort 18110 -Workspace .\tmp\topic3\demo-workspace`. SEC cần `STUDIO_SEC_RESEARCH_ROOT`, `TOPIC3_RESEARCH_ROOT` và `STUDIO_SEC_VECTOR_ROOT` đã trỏ tới đúng cặp snapshot/vector; thiếu chúng phải báo không sẵn sàng, không thay nguồn khác.

Restart cùng workspace và biến môi trường:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_financial_studio.ps1 -Stop
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_financial_studio.ps1 -Mode Prebuilt -OpenBrowser
```

Launcher chỉ dừng process do nó sở hữu; giữ Ollama/dịch vụ khác. Restart thật trong phiên RC giữ hai PDF gốc READY và nguồn SEC; không rebuild historical index.

## Luồng trình bày

1. Kho tài liệu: chỉ rõ tên file, trạng thái READY và metadata có thể hiệu chỉnh. Upload một PDF được phép sử dụng, không nhập company/year, chờ READY. Không tuyên bố READY nếu embedding chưa xong.
2. Chọn Apple trong Trợ lý tài chính; hỏi `What was Apple's net income in fiscal year 2025?`. Giải thích 112.010 triệu USD và CELL_VERIFIED, mở nguồn trang 32/highlight rồi quay lại.
3. Hỏi `Which geographic segment generated the highest net sales in fiscal year 2025, and how much did it generate?` → Americas 178.353 triệu USD, trang 25.
4. Hỏi `Calculate Apple's year-over-year total net sales growth rate from fiscal 2024 to fiscal 2025. Show the calculation and round to two decimal places.` → 6,43%; xem hai toán hạng/formula. Hỏi tiếp `Còn năm 2024?` → 391.035 triệu USD.
5. Mở công cụ nâng cao SEC, chọn HD, hỏi `What were HD total assets as of August 2, 2026?`. Mở citation: bảng cân đối, 109.384 triệu USD tại 2026-08-02, khác ngày nộp 2026-08-25. Chỉ rõ hàng/cột/ô màu, giá trị gốc và provenance mở rộng.
6. Link SEC.gov là bản công bố chính thức; nếu trang chặn tự động, giải thích đây là hạn chế bên ngoài. Local viewer dùng bytes đã xác minh, không phải proxy vượt chặn.
7. Hỏi Microsoft trên Apple hoặc FY2037; trình bày refusal không bịa số. HPG scan có thể tìm kiếm, numeric mapping chưa hỗ trợ nên từ chối.
8. Research Lab: phân biệt truy vấn demo với kết quả nghiên cứu đã khóa. Không chạy holdout, không nói Hybrid vượt BM25 hay AI trả lời mọi câu hỏi.

Nếu thiếu nguồn/model: trình bày trạng thái lỗi thực tế và ảnh RC đã ghi rõ thời điểm; không trình bày ảnh cũ như một lượt live thành công.
