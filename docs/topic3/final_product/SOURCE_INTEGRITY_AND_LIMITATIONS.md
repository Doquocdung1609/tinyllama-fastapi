# Tính toàn vẹn nguồn và giới hạn

## Ranh giới tin cậy

- SEC Search chỉ đọc snapshot P7 và Qdrant P10 READY. Trước truy xuất, code kiểm tra generation, manifest, parent count, raw source hashes, Nomic digest/dimension/cosine/prefix và đối chiếu identity với Research QA. Mỗi kết quả được khôi phục từ nguồn đã xác minh, có SHA256, filing ID, accession và locator.
- Financial AI dùng Research API riêng có bearer token, D1 xác định phạm vi, D2 ánh xạ ô bảng từ nguồn đã xác thực, D4 tính Decimal. Chọn chứng cứ SEC trong Search chuyển CIK và filing ID làm bộ lọc rõ ràng; câu hỏi mâu thuẫn không được tự nới bộ lọc.
- PDF người dùng được giới hạn 20 MiB, số trang/chunks/text, kiểm chữ ký PDF, hash file và page text. Chunks FTS5 và vector Qdrant có ID/hash nguồn riêng. Trước trả kết quả và ảnh highlight, hệ thống rehash nguồn. Sau restart, tài liệu bị thay đổi sẽ chuyển FAILED, không còn READY.
- Quyền truy cập `/studio` và `/research/v1/query` mặc định yêu cầu bearer token. Chỉ giao diện server-side giữ token; không ghi token vào Git hay screenshot. Workspace PDF có marker sở hữu để không dùng nhầm thư mục owner.

## Dữ liệu lịch sử

Nhánh sản phẩm bắt đầu tại P11 commit `ecd81627c3714e96c9e386fd06ce4e25757ce283`. `git diff --exit-code HEAD -- docs/topic3/milestone_d/recovery` trả 0; các artifact nghiên cứu cũ không được sửa. Bốn JSON P11 có quy tắc LF trong `.gitattributes` để Git trên Windows giữ blob gốc. Thử nghiệm UI chỉ ghi vào workspace PDF mới; SEC snapshot và vector generation đã tồn tại được dùng để đọc. Chưa tiến hành kiểm kê hash toàn bộ filesystem owner trước và sau buổi thử, nên bằng chứng bảo toàn filesystem ở mức **không có thao tác ghi chủ đích và không có sai lệch Git**, không phải chứng nhận tuyệt đối.

## Giới hạn sản phẩm

1. SEC HTML có link đúng filing và locator cấu trúc; browser không được chứng minh hạ cánh chính xác vào ô. Ảnh SEC ở bộ tham chiếu chỉ là minh họa.
2. Financial AI hỗ trợ phạm vi metric/period đã ánh xạ; số ngoài phạm vi phải từ chối. Search evidence relevance khác với xác thực số/câu trả lời.
3. PDF text highlight là chính xác khi `EXACT_PDF_TEXT_MATCH`; PDF scan không có text layer có thể FAILED hoặc thiếu tọa độ. PDF tải lên hiện **chưa** có financial numeric QA đã kiểm chứng.
4. Workspace PDF được thiết kế cho demo cục bộ một người dùng. Chưa chứng nhận đa người dùng, mạng công cộng, phục hồi thảm họa hay kiểm toán bảo mật sản xuất.
5. Chưa có phép so sánh khoa học độc lập mới để thay kết luận cũ rằng BM25 là mặc định được khuyến nghị trên corpus đánh giá đã chấp nhận.
