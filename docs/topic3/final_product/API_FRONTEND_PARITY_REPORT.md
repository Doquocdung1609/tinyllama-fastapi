# Đối chiếu API / React

| Luồng | API/service giữ lại hoặc bổ sung | React | Kết quả |
|---|---|---|---|
| Tổng quan / chẩn đoán | /health, /studio/readiness | số đếm thật, readiness, RAM | PASS |
| SEC BM25/Dense/RRF | SecResearchIndex + /studio/query | issuer/period/source, rank + score riêng | PASS PG/HD |
| PDF BM25/Dense/RRF | PdfWorkspace + /studio/query | Việt Nam / uploads / tất cả, chọn tài liệu | PASS hai PDF thật |
| Upload/retry | /studio/documents, /retry, /extraction | trạng thái từng trang, lỗi và thử lại | PASS; recovery regression + real restart |
| Nguồn PDF | /file, /pages/{n}/evidence, /chunks | native selectable text + OCR overlay, zoom/page/rotate | PASS |
| Highlight cũ | page_image /highlight | legacy rollback còn hỗ trợ | contract giữ nguyên; test cũ PASS |
| SEC Financial AI | ResearchBackend qua /studio/sec/analysis | công ty đọc được, authenticated cells | PASS hai câu hỏi hỗ trợ; câu 2031 từ chối |
| PDF số liệu | /facts/review, /facts, /analysis | đối chiếu ô theo ảnh + công thức/toán hạng | PASS |
| Nghiên cứu doanh nghiệp | POST /research + GET job | tiến trình thật, context/fundamentals/risk/synthesis | PASS workflow; diễn giải model PARTIAL |
| So sánh | /compare | ba kênh cùng generation, overlap, latency | PASS; không có qrels mới |
| Đánh giá cũ | /evaluation | development metrics có nhãn phạm vi | PASS; không áp sang PDF mới |
| Hỏi đáp đoạn PDF | /analysis document_qa | trích đoạn gốc và citation | PASS extractive; không chứng nhận mọi số trong quote |

Không cần parent/chunk ID từ người dùng. Evidence chuyển từ search/viewer sang AI; tài liệu/bộ lọc/đoạn chọn được giữ theo phiên. Khi đổi tài liệu có thể vẫn hiển thị evidence đã chọn trước đó, luôn ghi đúng doanh nghiệp/trang và người dùng chủ động mở nó; nguồn tính toán vẫn bị ràng buộc document_ids hiện tại.

Các hợp đồng cũ không bị đổi tên/xóa. Shared historical services và kiểm thử Chat/RAG còn nguyên; general chat/media không trở lại điều hướng sản phẩm. `product_ui.py`, `streamlit_app.py` và launcher legacy được giữ; Streamlit chuyển sang requirements-legacy-ui.txt thay vì dependency mặc định. Chưa tuyên bố xóa legacy hoàn toàn vì không kiểm thử lại mọi tổ hợp tùy chọn/hardware của giao diện cũ.

SEC HTML chỉ mở URL filing + structural locator và snippet; không giả trang PDF hay tự hứa deep-link chính xác tới ô HTML. Bộ giải SEC giữ phạm vi câu hỏi tiếng Anh đã kiểm chứng; giao diện tiếng Việt không đồng nghĩa mọi câu tiếng Việt đều được bộ giải SEC hỗ trợ.
