# Financial Intelligence Studio — sản phẩm và kiến trúc

## Phạm vi

Sản phẩm demo cục bộ có hai năng lực: (1) tìm chứng cứ tài chính bằng BM25, Dense Nomic và Hybrid RRF; (2) trả lời số tài chính SEC bằng ô nguồn và phép tính Decimal đã kiểm chứng. Sáu trang điều hướng là Tổng quan, Tìm kiếm tài chính, Phân tích tài chính AI, Kho tài liệu, So sánh truy xuất, Hệ thống & cài đặt. Viewer là ngữ cảnh mở từ Search, AI hoặc Library.

## Dòng dữ liệu

`SEC/PDF → xác thực nguồn → trích xuất → chunk/parent → SQLite BM25 + Qdrant Dense → RRF → chứng cứ → D1 phạm vi + D2 ô nguồn + D4 Decimal → câu trả lời hoặc từ chối`.

SEC Search đọc snapshot P7/P10 READY với 1.781 parent và 3 filing PG/HD/COST; Financial AI đọc cùng generation và manifest. `app/product/sec_search.py` kiểm tra membership, model digest, 768 chiều, cosine và prefix trước khi tìm, rồi xác minh lại nguồn của kết quả. PDF người dùng dùng workspace sở hữu riêng, FTS5 và Qdrant riêng, không đưa vào SEC generation. PDF chỉ READY sau khi cả BM25 lẫn Dense đều hoàn chỉnh; khi restart, source/hash/chunk/vector được kiểm tra lại.

Giao diện `product_ui.py` gọi FastAPI sản phẩm và Research API thật. Các nút Search/Compare/AI không chứa số liệu mẫu. Giá trị trong `tests/fixtures/pdfs/` là dữ liệu tổng hợp được ghi nhãn. Financial AI không dùng LLM để chọn số; một câu hỏi ngoài phần bảng được ánh xạ sẽ từ chối. API vẫn giữ các route RAG/tài liệu cũ cho tương thích, nhưng không còn general chat hoặc media UI.

## Giới hạn

SEC HTML chỉ được mở tại filing chính thức. Locator cấu trúc và đoạn trích giúp định vị; không có bảo đảm browser nhảy tới ô. PDF ảnh/scan thiếu lớp chữ có thể thiếu tọa độ chính xác. Hiện chỉ một số family số liệu SEC được ánh xạ; không có tuyên bố độ đúng cho mọi câu hỏi hay Hybrid vượt BM25. Các báo cáo nghiên cứu và held-out cũ được giữ nguyên.
