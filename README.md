# Financial Intelligence Studio

Ứng dụng nghiên cứu tài chính chạy cục bộ với hai luồng chính: **Hybrid Search** trên hồ sơ SEC/PDF cá nhân và **Financial AI** chỉ trả lời số liệu khi có ô nguồn được xác minh. Giao diện Streamlit có đúng sáu trang: Tổng quan, Tìm kiếm tài chính, Phân tích tài chính AI, Kho tài liệu, So sánh truy xuất, Hệ thống & cài đặt.

## Chạy trên Windows

Cài dependency bằng Python 3.13 trong `.venv` và giữ sẵn các snapshot nghiên cứu SEC/P10 đã xác minh. Tạo biến môi trường cục bộ theo [hướng dẫn khởi động](docs/topic3/final_product/WINDOWS_STARTUP.md); không commit token hoặc đường dẫn dữ liệu riêng. Sau đó chạy:

```powershell
.\scripts\start_financial_studio.ps1
```

Script kiểm tra model `nomic-embed-text:latest` đúng digest đã chấp nhận, khởi động Ollama đã cài nếu cần, rồi mở FastAPI, Research API và Streamlit. Mặc định UI ở `http://127.0.0.1:8501`. Script không tải model hay thay đổi corpus SEC/Qdrant lịch sử.

## Luồng sử dụng

1. **Kho tài liệu:** xem hồ sơ SEC, tải PDF tối đa 20 MiB vào workspace riêng, chờ BM25 và Dense hoàn tất trước trạng thái READY.
2. **Tìm kiếm tài chính:** chọn nguồn, BM25/Dense/Hybrid RRF, bộ lọc và mở chứng cứ. PDF được tô sáng trên trang thật; SEC HTML dùng đúng filing URL, đoạn trích và locator cấu trúc.
3. **Phân tích tài chính AI:** hỏi về số tài chính SEC được hỗ trợ. Câu trả lời dùng `Decimal`, ô nguồn, kỳ, đơn vị và trích dẫn; nếu thiếu chứng cứ sẽ từ chối.
4. **So sánh truy xuất:** chạy cùng truy vấn trên ba kênh và xem thứ hạng, phần giao nhau cùng độ trễ đo thực. Chỉ hiển thị Recall/MRR/nDCG khi có qrels hợp lệ.

PDF demo trong `tests/fixtures/pdfs/` là **dữ liệu tổng hợp**, không phải công bố SEC. Không dùng các con số minh họa trong ảnh UI làm dữ liệu sản phẩm.

## Bảo toàn nguồn và giới hạn

- SEC Research dùng generation P7/P10 cô lập đã READY, cùng identity với Financial AI. Kết quả truy xuất được đối chiếu source hash; nó không xác nhận mọi ô tài chính.
- PDF cá nhân được lưu trong workspace riêng, có hash nguồn, tọa độ trang và Qdrant riêng. Không trộn với SEC hay tự đánh dấu READY khi thiếu index.
- Giao diện SEC không hứa mở đúng ô trong trình duyệt khi không có anchor ổn định. Financial AI không chứng nhận độ đúng cho câu hỏi tài chính tùy ý.
- Không có kết luận Hybrid tốt hơn BM25 trên dữ liệu mới. Các nghiên cứu D2–P11 và kết quả lịch sử nằm trong `docs/topic3/`.

Xem [hướng dẫn người dùng](docs/topic3/final_product/USER_GUIDE.md), [báo cáo E2E](docs/topic3/final_product/END_TO_END_TEST_REPORT.md) và [báo cáo khóa học](docs/topic3/final_product/VIETNAMESE_COURSE_REPORT.md).

## Kiểm thử

```powershell
.\.venv\Scripts\python.exe -m compileall -q app scripts product_ui.py main.py
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pytest -q -m "not integration"
```

Đây là nguyên mẫu cục bộ opt-in, không phải hệ thống tài chính được chứng nhận cho vận hành sản xuất.
