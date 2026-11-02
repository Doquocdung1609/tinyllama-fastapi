# Audit hiển thị đơn vị và nguồn

Code `209faf9988490ec9f8f6979f304b4e3852724d5a`; chỉ đổi presentation và metadata additive. Backend Decimal verifier, source-byte validation, signed references, auth và bounds giữ nguyên.

| Nội dung | Quy tắc và bằng chứng |
|---|---|
| HD amount | Typed value `109384`, raw `109,384`, USD × 1000000 → `109.384 triệu USD`; normalized backend `109384000000` ở chi tiết |
| Dấu/precision | Formatter không Number/parseFloat, giữ +/−/parentheses và phần thập phân, chuỗi dài; ưu tiên typed Decimal `value` vì iXBRL sign có thể không in trong raw cell |
| Phạm vi formatter | Chỉ tiền USD/VND và multiplier 1/1000/1000000/1000000000; không hiểu format thì giữ fallback gốc, không đoán currency/scale |
| Answer guard | Chỉ single EXTRACT với một operand khớp chính xác effective_value và unit mới dùng readable source amount; không áp vào phép so sánh hay phần trăm |
| Kỳ nguồn | HD INSTANT 2026-08-02; report end 2026-08-02; filing date 2026-08-25; FY2026 ghi rõ metadata. DURATION hiển thị start→end nếu có |
| Context | CONSOLIDATED BALANCE SHEETS; Total assets; bảng `table_483d3ac2b60916e1e4c8d837`, zero-based row14/column4; DOM tr15/td3; không tạo anchor |
| Highlight | Row amber RGB255,247,237; column blue224,242,254; cell green187,247,208. Browser đo computed styles và xác nhận cell text109,384 |
| Provenance | Hash/generation/manifest/locator đóng mặc định, còn inspectable; table là bounded safe derivative từ original bytes, không HTML active |
| Warnings | Cảnh báo partial giải thích tiếng Việt; mã nguyên gốc trong diagnostics. Không đánh đồng ô đã xác minh với toàn filing đã parse hoàn chỉnh |

HD 10-Q accession `0001628280-26-058715`,953101 bytes, raw SHA256 `3d638bc025ef9643317d539f63c3891c8db9b47e35a8edd8040928704d0703f1`. Hash trực tiếp sau smoke vẫn khớp registry. [Link chính thức](https://www.sec.gov/Archives/edgar/data/354950/000162828026058715/hd-20260802.htm) đúng, nội dung Chromium bị SEC chặn. Kiểm tra bytes/lineage dựa vào upstream registry đáng tin và storage local; không phải chứng nhận nguồn độc lập bằng con người.

React review: ordinary escaped text nodes, không innerHTML; source query retry:false, lỗi revalidation ẩn verified cell cũ; URL https SEC allowlist, external noopener/noreferrer; table scroll focusable; selection không thay source IDs/colspan. Không thêm library hoặc side effect source write. Frontend tests bao gồm active-content rejection, unsafe URL, stale-source removal, period semantics, scope và exact-string formatting.
