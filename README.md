# Financial Intelligence Studio

Ứng dụng React tiếng Việt chạy cục bộ, kết hợp **Hybrid Search** và **Financial RAG nhiều công cụ**. Tìm kiếm báo cáo Việt Nam/SEC bằng BM25, Dense và RRF; mở PDF gốc có highlight; chỉ tính số tài chính từ các ô nguồn đủ điều kiện.

## Chạy Windows

```powershell
npm ci --prefix frontend
.\scripts\run_financial_studio.ps1 -Mode Development -Workspace .\studio_workspace\react-product-20261028 -OpenBrowser
```

UI http://127.0.0.1:5173. Khóa đăng nhập nằm tại `tmp/studio-runtime/access-token.txt`, không chia sẻ/commit. Cài backend trong `.venv` theo requirements.txt nếu máy chưa có. Muốn bản đã đóng gói: build frontend, dừng phiên bằng -Stop rồi chạy -Mode Prebuilt (http://127.0.0.1:8110/app/). Launcher không tự tải model/SEC hoặc thay dữ liệu lịch sử.

Xem [hướng dẫn Windows đầy đủ](docs/topic3/final_product/WINDOWS_QUICKSTART.md), [demo10 phút](docs/topic3/final_product/DEMO_SCRIPT_10_MINUTES.md), [nghiệm thu](docs/topic3/final_product/FINAL_PRODUCT_ACCEPTANCE.md), [đối chiếu paper](docs/topic3/final_product/PAPER_ALIGNMENT_MATRIX.md), [báo cáo khóa học](docs/topic3/final_product/FINAL_COURSE_REPORT_VI.md).

## Hai luồng chính

1. Kho tài liệu → upload PDF → native/OCR theo trang → BM25/Nomic/Qdrant → so sánh3kênh cùng snapshot → PDF.js nguồn có tọa độ thật.
2. AI → đối chiếu ô theo ảnh/kỳ/unit/scope → Decimal extract/period-change/ratio → trích dẫn, hoặc từ chối; nghiên cứu doanh nghiệp qua công cụ context/fundamentals/risks/calculations/synthesis, localLLM tùy chọn.

Hai PDF thật Hòa Phát/BIDV là nguồn kiểm tra chính, không commit raw hoặc số vào logic app. Bảng OCR còn là ứng viên đến khi đối chiếu. SEC/iXBRL có bộ xác thực riêng; không gán chứng thực SEC cho PDF thông thường. Nguồn thị trường/tin tức chưa cấu hình được ghi UNAVAILABLE. Không khuyến nghị mua/bán.

## Kiểm thử và bảo toàn

```powershell
.\.venv\Scripts\python.exe -m pytest -q
npm run test --prefix frontend
npm run build --prefix frontend
```

Live Chromium theo hướng dẫn Windows; GitHub CI chạy core deterministic và frontendunit/build. Development metrics lịch sử giữ nguyên và có nhãn riêng; không suy ra chất lượng truy vấn mới. Streamlit còn là rollback explicit qua -Legacy và requirements-legacy-ui.txt. Shared Chat/RAG/history tests giữ nguyên. Nguyên mẫu học tập cục bộ, chưa được chứng nhận cho tư vấn tài chính hoặc vận hành đa người dùng.

## Search V2 — ứng viên chưa khóa chất lượng

Xem [nghiệm thu Search V2](docs/search_v2/SEARCH_OWNER_ACCEPTANCE.md) và [benchmark có giới hạn](docs/search_v2/SEARCH_EVALUATION_REPORT.md). Baseline BM25/Dense/RRF được giữ nguyên; V2 bổ sung chỉ mục dòng và kiểm tra ngữ cảnh. Nhãn hiện chưa được rà soát độc lập; không tuyên bố SEARCH_V2_LOCKED.

## Search V3 — kiểm định nguồn mới, chưa khóa chất lượng

Xem [nghiệm thu V3](docs/search_v3/SEARCH_V3_FINAL_ACCEPTANCE.md), [kết quả tám phương pháp](docs/search_v3/SEARCH_V3_EVALUATION_REPORT.md) và [gói kiểm tra cho người rà soát](docs/search_v3/SEARCH_V3_OWNER_AUDIT_PACKET.md). V3 tách tìm đoạn liên quan khỏi quyền trả lời số; 84 câu mới có provenance và phân tách development/retest/test. Tập nguồn mới vẫn phát hiện lỗi mất bảng ảnh; trạng thái **SEARCH_V3_PARTIAL**, không tuyên bố LOCKED. PR23/24 và các baseline được giữ nguyên.
