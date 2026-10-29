# Nghiệm thu sản phẩm cuối — 28/10/2026

Đề nghị: **FINANCIAL_INTELLIGENCE_PRODUCT_READY_WITH_LIMITATIONS**. React: **FINANCIAL_STUDIO_REACT_PRODUCT_READY_WITH_LIMITATIONS**. Quyền nghiệm thu cuối thuộc chủ repository. Không merge/main, không bắt đầu milestone học thuật mới.

## Ma trận nghiệm thu

| Nhóm | Trạng thái | Bằng chứng |
|---|---|---|
| Sáu trang React tiếng Việt | PASS | screenshots01–06; real Chromium |
| Native/scan/mixed, rotated OCR | PASS ca đã chạy | HPG24/BIDV8; source hashes; screenshot07/10/14 |
| BM25/Dense/RRF tiếng Việt, filters | PASS bounded | 15 request, 5 câu hỏi, 2 PDF thật; cùng scope |
| PDF navigation/highlight/selectable text | PASS | PDF.js canvas/textlayer + OCR geometry, screenshot09/14 |
| Numeric QA & calculations | PASS bounded | 7 reviewed cells; 5 supported cases + 4 abstentions |
| Company-research multi-tool report | PASS workflow | 8 event, cited report, Decimal highlights; screenshot15 |
| Chất lượng diễn giải LLM | PARTIAL | hai draft accepted-as-unverified, hai stage rejected ở lượt ghi nhận |
| Market/news trực tiếp | NOT_TESTED | không có connector, UNAVAILABLE an toàn |
| SEC ingestion/retrieval/QA | PASS product profile | 2 official files, 1.241 parents/vectors, HD/PG answers |
| Historical integrity | PASS phạm vi audit | 8 raw +8 manifests, active status partial giữ nguyên |
| Idempotency/restart/recovery | PASS | hash/87chunks giữ nguyên sau restart; fault recovery regression |
| Backend full suite | PASS | 610 passed,1 warning,23.65s; trước bổ sung recovery test:609/25.47s |
| Frontend unit/build | PASS |6 tests; TypeScript + Vite build |
| Browser E2E | PASS |3 sequential tests,33.6s; fresh rerun recorded in RUNTIME_EVIDENCE |
| Windows Development/Prebuilt | PASS | ownership stop/restart, duplicate-port rejection, actual built assets/PDF worker |
| GitHub final-head CI | xem Draft PR checks | chỉ kết luận PASS sau workflow đúng HEAD; không dùng CI nhánh cũ |
| Target GTX1650Ti / arbitrary financial accuracy | NOT_TESTED | máy kiểm tra RTX3050 4GB; không suy rộng |

## Bảo toàn và provenance

Base kiểm tra trước code: 39cc2ed203671ca3007db859eefe7155595a16b6, Draft PR22 mới nhất. Snapshot P10 cũ không có trên máy. Sau khi chủ dự án cho phép tải mới, SEC trả PG khác hash cũ; phiên mới product-pg-hd-20261028 giữ riêng. Xem SEC_PRODUCT_SOURCE_REGISTRY.json cho raw URL/hash/generation và RUNTIME_EVIDENCE.json cho kết quả thực. Catalog metadata giữ discovery timestamp gốc; thời điểm lưu raw mới được ghi riêng, không giả đó là timestamp tải cũ. READY index không nâng PARTIAL_EXTRACTION của filing.

Raw PDF riêng, SQLite/Qdrant, models, logs/token không commit. Annotations SOURCE_REVIEW_FIXTURES chỉ là evidence kiểm tra, app không import số từ đó. Không sửa qrels/benchmark lịch sử hoặc default model/digest/RRF. Legacy services/tests giữ nguyên. Streamlit chuyển khỏi đường chạy mặc định; rollback explicit đến khi chủ dự án chấp nhận parity giới hạn hiện tại.

## Lỗi phát hiện và cách xử lý

Tesseract tessdata Windows quoting được sửa bằng prefix path thực; tiếng Việt đ/gấp dấu có index cache riêng; cold workspace ownership race được khóa; stop-process creation-time so UTC ticks; header-column geometry và reviewed-fact audit chống gán nhầm/tamper. Từng lỗi có targeted regression phù hợp. Chạy chồng hai Playwright process đã làm xung đột tệp trace (hai lượt FAIL môi trường); chạy lại tuần tự3/3PASS. Một lệnh E2E từ sai working directory trước khi sửa đường dẫn source đã SKIP3; không tính các lượt đó là PASS. Không tắt test hoặc đổi status để tạo kết quả xanh.

## Giới hạn còn lại

OCR bảng phức tạp/chữ sai chưa được chứng nhận toàn bộ; kiểm chứng7 ô là thủ công theo ảnh, không tự động toàn báo cáo. Hỏi đáp tài liệu thường trả extractive excerpts; chỉ numerical service mới chứng nhận các toán hạng đã đối chiếu. Model draft cần source review dù qua guard; final prose có thể bị bỏ. SEC solver giữ phạm vi metrics/câu hỏi cũ, không hỗ trợ tài chính tùy ý. Mixed-source ordering dựa rank từng store, không so score thô hoặc tuyên bố benchmark. SEC HTML không có deep-link bảo đảm tới hàng. Archived derived revisions giữ file/manifest nhưng API lookup mặc định active revision theo hợp đồng hiện hữu. Không có connector thị trường/tin tức, không định giá/giao dịch. Không có holdout mới hoặc test mọi cấu hình legacy/hardware.

Xem WINDOWS_QUICKSTART, DEMO_SCRIPT_10_MINUTES, các acceptance theo Topic3/Topic5 và PAPER_ALIGNMENT_MATRIX. Các báo cáo trước trong thư mục là bằng chứng lịch sử, không bị ghi đè để áp trạng thái mới.
