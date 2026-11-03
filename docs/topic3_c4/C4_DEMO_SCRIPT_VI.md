# Lời trình bày tiếng Việt — khoảng 7 phút

**Mở đầu.** “Đề tài của nhóm là tìm kiếm lai trên tài liệu tài chính. Trong báo cáo, một từ khóa như doanh thu xuất hiện ở nhiều năm, nhiều quý và nhiều công ty. Một đoạn văn có vẻ liên quan vẫn có thể đưa sai ô. Vì vậy chúng em đo riêng việc tìm đúng *filing*, việc tìm đúng một *chunk* đủ chứng cứ, và việc trả lời đúng số.”

**Phương pháp.** “Chúng em tái lập sáu nhánh mã tác giả: BM25, BGE, SPLADE, hai phép RRF, và bộ xếp hạng Stage-2 bằng đặc trưng cố định. Stage-2 không chạy ColBERT thật. FAITH-R thêm kiểm tra công ty, kỳ tài chính, ứng viên bảng và xếp hạng chứng cứ. Corpus phục hồi có 8.670 chunks; nó không hoàn toàn trùng bản 8.609 chunks được báo cáo trong nghiên cứu gốc.”

**Ví dụ có lợi và bất lợi.** “Với câu Apple FY2025 `05_01`, baseline BM25+BGE đưa đúng filing ở hạng 7, A4 ở hạng 1. Tuy nhiên chunk hạng 1 của A4 là Item 5, chưa chứng minh ô cost of sales; chúng em chỉ gọi đây là thắng ở proxy filing. Với câu Apple 10-Q `03_01`, baseline đúng filing ngay hạng 1, A4 không thấy filing đích trong Top-20. Đây là ví dụ chọn sau khi xem kết quả, không phải tỷ lệ thắng độc lập.”

**Sản phẩm.** “Kho tài liệu hiện có báo cáo Hòa Phát scan và công bố điều chỉnh BIDV, đều đã xử lý. Cùng một câu BIDV, màn hình cho phép so BM25, Dense, Hybrid trên đúng một PDF và mở trang nguồn. Bảng BIDV có cột số đã công bố, điều chỉnh KTNN và số trình bày lại; phần mềm hiển thị đoạn nguồn nhưng chưa tự xác nhận mọi ô. Với Hòa Phát, OCR dẫn được về trang 5 nhưng ký tự méo; khi hỏi số hợp nhất từ báo cáo công ty mẹ, hệ thống từ chối thay vì bịa số.”

**Kết quả thật.** “Chúng em khóa trước 93 câu hợp lệ để đo proxy tìm đúng SEC filing. A4 chỉ có dòng kết quả ở 67 câu; 26 câu còn lại thiếu dòng. Trong 67 câu chung với BM25+BGE, A4 thắng 9, hòa 40, thua 18 ở Top-5. Tức là chưa có bằng chứng FAITH-R tốt hơn tổng thể. Chúng em truy ra bộ lọc `FY<year>` loại nhiều 10-Q vì metadata của chúng là `Q-YYYY-MM`; còn hai câu TSM có metadata sai kỳ. Chúng em không sửa rồi chạy lại tập đã lộ để báo thắng.”

**Kết luận.** “Điểm mạnh hiện có là quy trình nguồn, truy vết chunk, so sánh thật và từ chối khi phạm vi sai. Giới hạn là qrels một chunk còn 0 EXACT và chưa có human qrels; 86 phê duyệt nguồn không biến thành 86 câu có chứng cứ truy xuất đạt chuẩn. Bước tiếp theo là sửa fiscal filter theo giao thức mới và đánh giá trên câu chưa xem.”
