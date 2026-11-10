# FIS V3 · bàn giao kiểm chứng trên PR #35

Mốc xuất phát 68b9432c725a6668c01d558982efdcaae9d9aefc. Đây là bản bàn giao theo mốc triển khai. Trạng thái nghiệm thu toàn bộ V3 là PARTIAL.

## Chat và giao diện

Bộ kiểm tra yêu cầu đọc lại câu hỏi gốc, kiểm tra nghĩa vụ trả lời độc lập với planner và đối chiếu kết quả cùng dấu xác nhận trong câu đã hiển thị. Các phép tính dùng Decimal và giữ tọa độ nguồn. Ở câu hỏi tăng trưởng nối tiếp, hai kỳ vừa được nhắc tới quyết định phép so sánh. Phạm vi phiên SEC gắn accession, SHA và thế hệ chỉ mục.

| Ca Apple | Kết quả kiểm chứng |
| --- | --- |
| A01 | Greater China giảm 2.575 triệu USD, tương đương 3,85%. Báo cáo nêu doanh thu iPhone giảm, được bù một phần bởi Mac. |
| A02 | Bác bỏ 69.377 triệu USD. Giá trị đúng là 64.377 triệu USD, chênh 5.000 triệu USD. |
| A03 | Services chiếm 26,23 trên mỗi 100. Tử số 109.158 và mẫu số 416.161 đều có citation đến ô nguồn. |
| A04 | 75,4% và 36,8% chênh 38,60 điểm phần trăm. Lấy Products làm mẫu số cho ra 104,89% tương đối theo tỷ lệ công bố. |
| A05 | Hoa Kỳ 151.790 triệu USD và Americas 178.353 triệu USD, chênh 26.563 triệu USD. |

Bản ghi trước sửa ở [before.json](before.json) và [before-browser.json](before-browser.json). Câu trả lời sau sửa, bằng chứng và kiểm tra trình duyệt ở [core-browser.json](core-browser.json). Bảng so sánh gốc và sau sửa ở [before/after](BEFORE_AFTER.md).

Ở 100%, vùng hội thoại chiếm khoảng 72,1% chiều cao ứng dụng tại 1366×768 và 80,7% tại 1920×1080. Phép đo 1280 và 390 px nằm trong [layout](final-layout-browser.json). Độ phóng đại tab Chromium 125% được kiểm tra bằng API zoom gốc, ảnh và phép đo lưu riêng. [Ảnh 125%](native-125-percent.png) · [Phép đo](native-zoom.json).

Chạy lại 56 kiểm tra trên React với Search, Chat và nguồn PDF thật. BIDV mở trang 4/7 và chỉ rõ phạm vi riêng, hợp nhất. HPG giữ nguồn khi không đủ căn cứ xác minh OCR hoặc phạm vi. [Browser PDF](pdf-regressions/browser-e2e.json).

## Kho SEC

Danh mục có 4 filing READY, gồm COST, HD và PG demo cùng PG kỳ 31/03/2026 do người dùng nhập qua UI từ EDGAR. Accessions và phiên đã lưu qua khởi động lại. Hai thế hệ có tổng 2.591 đoạn và 2.591 vector. Filing nhập mới dùng thư mục sản phẩm, job và registry riêng. Lượt nhập lặp lại trả về mục hiện có. [Import UI](sec-browser-import.json) · [SHA và kiểm tra danh tính](SEC_IMPORTED_PROOF.json) · [Khởi động lại](RESTART_RESULT.json).

PG nhập mới trả 21.235.000.000 USD doanh thu thuần cho quý kết thúc 31/03/2026. Citation mở hàng HTML/iXBRL chứa ô 21.235 với đơn vị triệu USD. Kiểm tra ô nguồn và Decimal được tiếp nối bằng cổng ngữ nghĩa dùng chung với PDF. [Browser SEC](sec-browser-viewer.json) · [Ô HTML](sec-imported-html-highlight.png).

Kiểm toán PR #36 tại 4677339ac4da5a62685212cac718223fe30582ae xác định 47 filing của 10 công ty. Ba gói nguồn theo manifest vắng mặt. Quét bổ sung 778 đường dẫn HTML/ZIP trong các worktree, Downloads và Desktop không tìm được bản raw ứng viên khớp theo tên hoặc dung lượng đã ghi. Kết quả có 47 SOURCE_NOT_AVAILABLE và 0 VERIFIED_READY thuộc bộ nghiên cứu. Việc đưa bộ này vào một thế hệ sản phẩm riêng cần raw bytes xác thực khớp SHA trong manifest. [Kiểm toán](SEC47_AUDIT.json) · [Ma trận 47 filing](SEC47_SOURCE_READINESS.csv).

## Các giới hạn nghiệm thu

- So sánh hai filing nằm ở hai thế hệ SEC vẫn trả mã CROSS_GENERATION_QUERY_REQUIRES_RECONCILIATION. UI hiện chọn một filing cho một phiên Chat.
- Hai ca doanh thu COST và HD theo quý 12/13 tuần còn PARTIAL. Cổng kỳ đo chưa xác thực các kỳ đó như khoảng ba tháng lịch. Các ca tổng tài sản dùng thời điểm được ghi rõ.
- Cổng ngữ nghĩa độc lập có phạm vi kiểm chứng theo tập yêu cầu và phép tính đã triển khai. Các câu thiếu kỳ, chỉ tiêu hoặc bằng chứng có thể nhận câu hỏi làm rõ hoặc kết quả PARTIAL.
- Kho SEC nhập từ danh sách filing gần đây của EDGAR. Các tệp nguồn và liên hệ vận hành được lưu trong workspace cục bộ.

## Chạy lại

Mở PowerShell ở worktree PR #35 và chạy:

```powershell
.\scripts\run_financial_studio.ps1 -Mode Prebuilt -ApiPort 18110 -Workspace 'C:/Users/Admin/.codex/worktrees/topic3-v7p/tinyllama-fastapi/studio_workspace/react-product-20261028'
```

Mở [Financial Intelligence Studio](http://127.0.0.1:18110/app/). Trong Kho tài liệu, chọn Hồ sơ SEC, tìm theo ticker hoặc CIK, lọc kỳ báo cáo, xem nguồn chính thức và chọn Thêm vào kho SEC. Sau khi READY, dùng Hỏi báo cáo này hoặc chọn accession trong Search. Khi chỉ mục chưa READY, mở lịch sử job để xem giai đoạn và lý do có thể thử lại.

Chạy hồi quy bằng `.venv/Scripts/python.exe scripts/fis_v3_acceptance.py --name acceptance-final`, `.venv/Scripts/python.exe scripts/fis_v3_followups.py` và `.venv/Scripts/python.exe scripts/fis_v3_sec_precise.py`. Chạy tuần tự để tránh giành tài nguyên trong cổng Chat. Các script Chromium nằm trong `frontend/e2e` với tiền tố `v3-`.

Các ca đo API dùng dữ liệu nguồn và dịch vụ đang chạy. Kết quả đánh giá ban đầu được giữ riêng trong [acceptance-development.csv](acceptance-development.csv). Lượt hồi quy sau sửa lỗi nhận nhầm token FY thành tên doanh nghiệp được ghi trong [acceptance-final.csv](acceptance-final.csv). Đây là số liệu hồi quy chức năng. Tài liệu đo và kết quả tổng hợp ở [RESULTS.md](RESULTS.md).
