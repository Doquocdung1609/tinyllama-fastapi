# Kiến trúc sản phẩm cuối — 28/10/2026

Base tích hợp: `39cc2ed203671ca3007db859eefe7155595a16b6`, nhánh `codex/topic3-final-product-redesign` (Draft PR #22). Nhánh giao hàng `codex/final-react-vietnamese-product` kế thừa trực tiếp base này, không merge hoặc sửa nhánh main.

## Ranh giới hệ thống

React/TypeScript/Vite/Tailwind/shadcn Button/Lucide trình bày sáu trang tiếng Việt. TanStack Query quản lý request; Recharts chỉ vẽ độ trễ/giao nhau đo thực. PDF.js tải byte PDF có Bearer token, dựng canvas và text layer, ghép vùng OCR bằng tọa độ thật. Không tính toán tài chính trong JavaScript; Decimal ở Python trả về chuỗi.

`app/product/frontend_api.py` bổ sung orchestration `/studio`: tìm kiếm, so sánh, readiness, nguồn PDF, đối chiếu ô, phân tích và job nghiên cứu. Router cũ giữ nguyên; legacy UI còn nguyên để rollback. Token lưu sessionStorage, không trong URL, biến VITE hoặc bundle. Chỉ bind loopback. Đây là ứng dụng học tập cục bộ, chưa phải mô hình phân quyền đa người dùng.

`PdfWorkspace` lưu raw PDF theo SHA256, SQLite/FTS5, page checkpoints, reviewed facts/audit history và Qdrant riêng. FTS tiếng Việt bổ sung cache gấp dấu (kể cả đ), giữ Unicode gốc, ID và vector cũ. READY nghĩa là hoàn tất trích xuất được hỗ trợ và đủ thành viên lexical/vector, không có nghĩa bảng đã xác minh. Trang lỗi/gián đoạn giữ checkpoint và retry; kiểm tra hash khi đọc nguồn. OCR tuần tự, không mở nhiều mô hình nặng song song. Nghiên cứu giới hạn một job đồng thời.

`pdf_extract.py` phân loại theo trang: native, scan, mixed, signature-only; OCR vie+eng 240dpi, tối đa 12MP/trang, OSD và phép đổi ngược tọa độ. Tối đa 20MiB upload, 250 trang, 2 triệu ký tự, 3.000 chunks. Bảng tái tạo là ứng viên; ô trống có box=None. Không đoán chữ số hoặc header. Fact review phải gắn đúng metric, ngày/kỳ, scope, basis, đơn vị, quy ước số và xác nhận đọc ảnh. Audit hash, source hash, page/layout fingerprint và ô hiện tại đều được kiểm tra lại trước Decimal.

Nghiên cứu dùng công cụ tuần tự: metadata → context → fundamentals → risks → eligible facts → verified calculations → optional market/news → synthesis. Bốn lời gọi Qwen tùy chọn chỉ diễn giải có dẫn nguồn, không được sinh số hay khuyến nghị. Guard không chứng minh mọi diễn giải chính xác; người đọc phải đối chiếu. Không có connector thị trường được cấu hình, trạng thái UNAVAILABLE có timestamp là kết quả thật.

## SEC và dữ liệu lịch sử

Giữ nguyên Nomic 768 chiều, cosine, prefix search_document/search_query, digest `0a109f422b47e3a30ba2b10eca18548e944e8a23073ee3f3e947efcf3c45e59f`, RRF k=60 và xác thực iXBRL/Decimal hiện hữu. Source registry mới chỉ được chọn khi cả manifest lẫn generation khớp chính xác; mặc định cũ không đổi.

Chủ dự án đã cho phép tải SEC mới khi không có snapshot P10 trên máy này. Hai hồ sơ PG/HD tạo **phiên sản phẩm riêng**, không thay thế snapshot nghiên cứu cũ. PG tải mới khác hash cũ; không tuyên bố khôi phục freeze cũ. Cả hai filing vẫn PARTIAL_EXTRACTION. READY của index không đổi status của filing. Không tạo qrels hoặc benchmark học thuật mới.

Chế độ Development: Vite 5173 proxy FastAPI 8110. Chế độ Prebuilt: FastAPI phục vụ `/app/` và worker/assets tương đối từ frontend/dist. Launcher ghi PID và thời điểm tạo, dừng đúng tiến trình do phiên quản lý; không dừng Ollama bên ngoài. Không tự tải AI model, SEC hoặc rebuild corpus khi khởi động.
