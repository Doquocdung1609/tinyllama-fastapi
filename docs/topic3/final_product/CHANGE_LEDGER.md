# Sổ thay đổi sản phẩm cuối

Base: `ecd81627c3714e96c9e386fd06ce4e25757ce283` (P11). Nhánh: `codex/topic3-final-product-redesign`. Đây là thay đổi giao diện và luồng sản phẩm, không phải sửa kết quả khoa học trước đây.

## Thêm mới

| Đường dẫn | Mục đích |
|---|---|
| `app/product/api.py` | API sản phẩm có xác thực cho tài liệu cá nhân, tìm kiếm, viewer và SEC catalog |
| `app/product/workspace.py` | PDF workspace cô lập, trích xuất có tọa độ trang, BM25, Dense, RRF, trạng thái và phục hồi |
| `app/product/sec_search.py` | Bộ đọc tìm kiếm SEC read-only trên snapshot P7/P10 đã xác thực |
| `product_ui.py`, `.streamlit/config.toml` | Sáu trang sản phẩm và giao diện responsive |
| `scripts/start_financial_studio.ps1` | Khởi động FastAPI, Research API, Streamlit bằng môi trường và snapshot có sẵn |
| `tests/test_product_pdf_workspace.py`, `tests/test_product_api_security.py` | Kiểm thử ingest, restart, tamper, tìm kiếm và quyền truy cập |
| `docs/topic3/ui_references/` | Bảy ảnh tham chiếu do người dùng cung cấp và README đi kèm |
| `docs/topic3/final_product/` | Hướng dẫn, kiến trúc, ánh xạ ảnh, báo cáo E2E, ảnh chụp thật và báo cáo môn học |

## Chỉnh sửa

| Đường dẫn | Thay đổi |
|---|---|
| `main.py` | Giữ API tài chính, tài liệu, RAG và conversation dùng chung; thêm API sản phẩm; bỏ route media/chat chung |
| `streamlit_app.py` | Điểm vào duy nhất của sáu trang tài chính |
| `start_genai.ps1` | Dẫn sang script khởi động sản phẩm hiện tại |
| `README.md`, `scripts/smoke_test.py` | Hướng dẫn và smoke test theo sản phẩm mới |
| `app/config.py`, `app/services/system_service.py`, `app/services/inference_manager.py` | Bỏ cấu hình/status media, giữ phần hạ tầng inference được dùng |
| `requirements.txt` | Bỏ phụ thuộc TTS không còn dùng |
| `tests/test_api.py` | Bảo vệ route còn lại và xác nhận route media/chat đã bỏ |
| `.gitignore`, `.gitattributes` | Bỏ qua workspace cục bộ; cố định LF cho artifact P11 lịch sử trên Windows |

## Xóa khỏi Git

`app/services/image_service.py`, `app/services/tts_service.py`, `app/services/video_service.py`, `client.py`, `tts.py`, `requirements-image.txt`, `requirements-video.txt`, `scripts/benchmark.py`, `tests/test_media_integration.py`.

Đây là mã cho media và trình khách chat chung. Việc xóa không đụng tệp người dùng, model weights, SEC snapshots, Qdrant collections hay Git history. `scripts/verify_local_integration.py` là trình kiểm chứng Milestone B lịch sử còn nhắc `/chat`; giữ nguyên làm chứng cứ lịch sử, không dùng làm smoke test sản phẩm hiện tại.

## Ranh giới dữ liệu

PDF tải lên được lưu ngoài Git trong research workspace riêng; ảnh và báo cáo trong Git dùng PDF fixture tổng hợp. SEC snapshot P7/P10 chỉ được đọc. Kết quả C/D5/P11 và held-out trước đây không được sửa trong diff có nội dung.
