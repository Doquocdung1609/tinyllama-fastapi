# Báo cáo E2E sản phẩm — 2026-10-28

## Môi trường

Windows, Python từ venv dự án, FastAPI `127.0.0.1:8079`, Research API `:8767`, Streamlit `:8517`, Ollama `:11434`. Bộ SEC P7/P10 READY generation `8f0a7ba5ed851313a9948ddb465753c54012d94f9c36942239f7b2ec15b5e2fb`, manifest `86ad36365fbfb813e78e14246a48ae5735d7a8a1218f73daa4289caa98b215d0`, 1.781 parent, 3 filing PG/HD/COST. PDF workspace cô lập ngoài Git; hai fixture là **synthetic**. Model Nomic digest `0a109f422b47e3a30ba2b10eca18548e944e8a23073ee3f3e947efcf3c45e59f`.

## Kết quả kiểm thử trực tiếp

| Kịch bản | Chứng cứ quan sát | Kết luận |
|---|---|---|
| Khởi động Windows | `scripts/start_financial_studio.ps1 -ApiPort 8079 -ResearchPort 8767 -UiPort 8517 -NoBrowser` khởi động ba tiến trình; health FastAPI, Research và Streamlit trả 200; file PID ghi đúng process đang nghe cổng | PASS trên máy đã cấu hình snapshot |
| Sáu trang | Browser mở và đọc Tổng quan, Search, AI, Library, Compare, System | PASS |
| Corpus SEC | Overview: 3 filing, 1.781 parent, BM25/Dense READY; Library liệt kê PG/HD/COST | PASS |
| Upload PDF qua UI | Chọn `B_mixed_text_table.pdf` 77.3 KiB, nhấn upload, UI lần lượt UPLOADED rồi READY; Library có 2 PDF READY | PASS, fixture tổng hợp |
| Search PDF | HTTP `POST /studio/search` trên `C_financial_statement.pdf`, query `Tổng tài sản`: BM25 12.33 ms, Dense 149.36 ms, Hybrid 129.81 ms, cùng chunk `pdf_4bcefcfd551adf771f5a40949c1f72cb_1_00000`; mỗi mode 1 kết quả | PASS, lần đo đơn lẻ không phải p50 |
| PDF viewer/highlight | Browser mở kết quả, trang 1, `EXACT_PDF_TEXT_MATCH`; endpoint highlight HTTP 200, 50.169 bytes PNG; [ảnh desktop](screenshots/pdf-highlight-desktop.jpg) | PASS trên PDF tổng hợp; khớp cụm nguồn thật |
| SEC Search | UI query `P&G net sales` Hybrid có kết quả PG, cùng generation P7/P10; bảng Net Sales xuất hiện rank 2. HTTP HD Hybrid cũng trả nguồn HD. | PASS về truy xuất, không chứng nhận xếp hạng tối ưu |
| So sánh B/D/F | UI `HD total assets` dùng cùng generation, lần lượt HTTP 2299.4/491.98/450.31 ms; rank và phần giao nhau hiển thị, không có Recall giả | PASS, số đo một lượt với cache/cold không đồng nhất |
| Financial AI số thật | UI và HTTP câu hỏi P&G net sales quý kết thúc 2026-09-30: `SUPPORTED`, 23,276,000,000 USD = 23,276 × 1,000,000, ô nguồn SEC `NET SALES`, accession `0000080424-26-000256`, kỳ 2026-07-01–2026-09-30 | PASS cho ca được hỗ trợ |
| Từ chối an toàn | UI và HTTP `What was Costco operating cash flow in 2031?`: `NEEDS_CLARIFICATION`, `result_values=[]` | PASS, không tính là câu trả lời đúng |
| Link SEC | Click viewer HD mở tab `https://www.sec.gov/Archives/edgar/data/354950/000162828026058715/hd-20260802.htm`; DOM nhận dạng FORM 10-Q, Home Depot, kỳ 2026-08-02 và có `Total assets` | Filing đúng; browser **không** được xác nhận tự cuộn tới hàng/ô |
| Auth và route bỏ | `GET /studio/documents` không token = 401; `/chat` = 404. Test suite bảo vệ mutation/upload/search | PASS |
| Restart | Dịch vụ đã khởi động lại bằng script; PDF `C_financial_statement.pdf` vẫn READY và tìm được; test tamper/restart downgrade về FAILED | PASS trong workspace cô lập |
| Dữ liệu lịch sử | `git diff --exit-code HEAD -- docs/topic3/milestone_d/recovery` = 0; không chạy test phá hủy trên nguồn/vector owner | VERIFIED_WITH_LIMITATIONS: chưa đo hash trước/sau toàn bộ owner filesystem |

## Regression

Lệnh trong venv sau các chỉnh sửa cuối: `python -m pytest -q tests/test_product_pdf_workspace.py tests/test_product_api_security.py tests/test_api.py` → **11 passed, 1 warning, 4.56 s**. `python -m pytest -q` → **590 passed, 1 warning, 29.89 s**. `python -m pytest -q -m "not integration"` → **590 passed, 1 warning, 38.89 s**. `python` hệ thống không có dependencies của dự án nên một lần thử trước đó dừng ở collection với `pymupdf` và `portalocker` thiếu; kết quả chính thức dùng `C:\Users\Admin\Desktop\AI_thay_Hieu\tinyllama-fastapi\.venv\Scripts\python.exe`. Warning duy nhất trong venv: `StarletteDeprecationWarning` từ `fastapi.testclient`/`httpx`. `python -m compileall -q app scripts product_ui.py main.py` và PowerShell parser startup script đều thành công.

## Giới hạn kiểm thử

UI được kiểm bằng trình duyệt cục bộ thật; ảnh chụp có trong `screenshots/`. Benchmark độ trễ chỉ là các lần thử riêng, không so sánh phân phối lạnh/ấm. Chưa thử PDF scan hoàn toàn không có text, đa người dùng, hay triển khai mạng công cộng. Financial AI chưa kiểm chứng câu trả lời tùy ý ngoài phạm vi adapter thực SEC.
