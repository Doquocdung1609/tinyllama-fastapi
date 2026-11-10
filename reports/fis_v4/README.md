# FIS V4 · SEC47 và hội thoại nhiều nguồn

## Phạm vi và trạng thái

Bản triển khai chạy trong worktree PR #35 từ checkpoint `76467e0912696c2142112a5a8b96884d87cea378`. Danh mục gốc đọc bằng `git show` tại `4677339ac4da5a62685212cac718223fe30582ae`. Hai tệp nghiên cứu có thay đổi cục bộ từ trước được để ngoài staging. Các bảng kiểm toán chỉ chứa định danh công khai, kết quả kiểm chứng và hash.

- Kho SEC phân biệt nguồn trong manifest, dữ liệu đã xác minh và chỉ mục BM25/Dense. Bộ nhập dùng một worker có khóa liên tiến trình. Sau gián đoạn, lần chạy tiếp theo kiểm tra lại receipt và SHA rồi bỏ qua bản đã xác minh. Resume theo filing.
- Các bản EDGAR lệch SHA nằm trong kho sản phẩm. Với nguồn còn thiếu bản nghiên cứu, chỉ có thể đối chiếu hash, kích thước và danh tính. Chưa thể tạo diff byte với bản gốc.
- Kiểm toán ZIP đổi tên, ZIP đóng gói lại và HTML đổi tên bằng cỡ thành viên rồi SHA đã có test. Quét rộng trên máy bị ngắt; kết quả `SOURCE_MISSING` phản ánh phạm vi tìm thấy trong lượt kiểm toán, và chưa loại trừ mọi bản sao lưu.
- 6-K cần xác minh exhibit và kỳ từ nội dung công bố. Luồng tự động giữ các mục này ở trạng thái cần đối chiếu.
- Chỉ mục Dense mới phụ thuộc Ollama. Các lô thử trên máy cục bộ gặp read timeout. Lượt nhập tiếp theo dùng BM25 và ghi rõ `DENSE_PENDING`. Ba filing demo COST/HD/PG cùng filing P&G đã nhập vẫn có generation Dense hiện hữu.

## Truy vấn và xác minh

Bộ chọn Chat hỗ trợ tối đa 20 PDF hoặc 20 filing SEC trong một phiên. Khi bộ nguồn thay đổi, FIS mở phiên mới. ID của từng nguồn được lưu trong hội thoại, để reload khôi phục đúng bộ đã chọn.

- **SEC** · Chạy retrieval trong từng generation. Hợp nhất theo hạng cục bộ và generation để không so BM25/cosine giữa index. Mỗi citation mang accession, generation, hash và tham chiếu được ký.
- **Số liệu SEC** · Lấy đúng parent và ô từ các bản HTML/iXBRL đã xác thực. Bộ xử lý đọc context start/end/instant, tiêu đề cột, đơn vị và scale. Bộ kiểm tra `Decimal` tính lại phép chênh lệch và phần trăm độc lập. Từ chối khi số kỳ, doanh nghiệp, đơn vị hoặc ngữ cảnh nguồn mâu thuẫn.
- **PDF** · Đọc từng tài liệu và nối citation theo đúng ID file. Chênh lệch giữa hai file chỉ được tính sau khi kiểm tra doanh nghiệp từ nội dung nguồn và xác nhận cùng chỉ tiêu, đơn vị, loại kỳ, phạm vi và cơ sở báo cáo. E2E trên Apple và BIDV xác minh retrieval và mở nguồn từ hai PDF. So sánh số giữa hai PDF cùng doanh nghiệp cần thêm cặp tài liệu phù hợp để kiểm tra trực tiếp.
- **Kỳ kế toán** · Số quý và lũy kế cùng ngày kết thúc giữ hai context riêng. Ô COST Net sales với ProductMember được chấp nhận riêng trong báo cáo kết quả hợp nhất; Total revenue và phí thành viên giữ phạm vi khác. Độ dài được đối chiếu với khoảng ngày thực tế, nên cột 12/13 tuần không thể thay bằng cột 36/39 tuần.
- **Viewer** · Dựng bảng từ HTML đã xác thực và hiển thị văn bản. Citation phải khớp chữ ký, generation, accession, hash, hàng và cột.

## Chạy lại

Chạy các lệnh sau từ worktree PR #35 trong PowerShell.

```powershell
$env:STUDIO_WORKSPACE_DIR=(Resolve-Path studio_workspace/react-product-20261028).Path
.\.venv\Scripts\python.exe -m scripts.fis_v3_sec47_audit --verify-only --search-root C:/Users/Admin/Downloads
.\.venv\Scripts\python.exe -m scripts.fis_v3_sec47_audit --recover --install --lexical-only
.\scripts\run_financial_studio.ps1 -Mode Prebuilt -ApiPort 18110 -Workspace $env:STUDIO_WORKSPACE_DIR
.\.venv\Scripts\python.exe scripts/fis_v4_live_checks.py
node scripts/fis_v4_browser_checks.cjs
```

SEC dùng liên hệ cấu hình riêng trên máy. `--archive-map PACKAGE=PATH` và `--source-map ACCESSION=PATH` cung cấp thêm nguồn cho kiểm toán. Bỏ `--lexical-only` khi muốn tiếp tục lập Dense. Quy trình chạy lại bỏ qua nguồn đã xác minh và dùng lại generation sản phẩm đã hoàn tất. Hướng dẫn EDGAR chính thức mô tả giới hạn truy cập và cách khai báo User-Agent. [SEC Fair Access](https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data)

Log API và ảnh demo ở `tmp/studio-runtime/v4-live.json` và `tmp/studio-runtime/v4-browser/`. Tệp riêng chứa access token không nằm trong các đầu ra này.

Nếu cần rollback code, dùng `git revert` các commit V4 theo thứ tự ngược và khởi động lại bản build tương ứng. Kho runtime cục bộ vẫn cần được giữ để truy ngược các citation đã lưu.

## Kết quả

Xem [ma trận 47 accession](SEC47_SOURCE_READINESS.csv) và [kết quả API, browser, độ trễ và CI](LIVE_ACCEPTANCE.md). Các gate Dense toàn bộ thư viện, tính toán với các 6-K đang chờ exhibit, kiểm tra browser zoom 125% và đo cold/warm p95/RAM có kiểm soát vẫn chưa nghiệm thu.
