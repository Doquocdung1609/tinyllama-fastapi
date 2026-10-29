# Báo cáo khóa học — Financial Intelligence Studio

## Mục tiêu và cách giải quyết

Sản phẩm phục vụ tìm và đối chiếu thông tin tài chính tiếng Việt, có SEC làm minh chứng quốc tế thứ cấp. Hai năng lực chính là Hybrid Search và Financial RAG nhiều công cụ có giới hạn. React không viết lại engine; API tái sử dụng BM25, Nomic/Qdrant, RRF và xác thực nguồn/Decimal đã có. Nguồn cá nhân và snapshot lịch sử được tách riêng.

Topic3 thực nghiệm trên hai PDF chủ dự án: Hòa Phát scan24 trang và BIDV mixed8 trang. Page OCR có checkpoint, giữ dấu tiếng Việt, hình học nguồn và trạng thái không chắc chắn. Ba kênh lexical/dense/fusion chạy trên cùng tập hợp tài liệu; comparison trình bày độ trễ và giao nhau đo thực. Không có qrels cho các câu mới nên không vẽ chất lượng giả. Các development measurements cũ chỉ hiển thị với nhãn riêng.

Topic5 dùng bộ công cụ kiểm tra metadata, truy xuất bối cảnh/nền tảng/rủi ro, lấy facts đủ điều kiện, tính Decimal và tổng hợp báo cáo. LLM cục bộ chỉ diễn giải tùy chọn, không phải nguồn số liệu. Mỗi ô dùng tính toán được người đọc kiểm tra ảnh, hàng/cột/kỳ/scale/scope và gắn hash; câu sai năm/công ty/metric/scope được từ chối. Kết quả HPG tài sản tăng 16.877.702.175.961 đồng; BIDV hợp nhất restated2.760.906.964 triệu đồng và tổng original+adjustment=restated. Các công thức dẫn về nguồn thật.

## Tham chiếu và giới hạn tái hiện

Reference A financial-hybrid-search-qdrant cung cấp đối chiếu pipeline, lexical/dense/fusion/filter/evaluation; sản phẩm giữ model Nomic đã chấp nhận thay vì thay model reference. SPLADE và ba vector không bắt buộc: tăng RAM/download và đổi hợp đồng index, trong khi BM25+dense/RRF đã thể hiện nội dung khóa học. Không tuyên bố tái lập toàn bộ reference hoặc chất lượng vượt reference.

Reference B ai-agent-moat cung cấp phân rã context/value/devil-advocate/final-summary. Sản phẩm triển khai tuần tự các công cụ tương ứng trên tài liệu có nguồn, không giả các persona là chuyên gia độc lập. Thiếu connector market/news thì trả UNAVAILABLE. Không làm valuation/BUY-SELL hoặc xây agent framework mới. Nguồn và audit trước diễn giải.

## Kết quả và đánh giá

610 backend tests PASS (một cảnh báo deprecation thư viện test), 6 frontend unit PASS và build PASS; 3 real Chromium E2E PASS ở lượt ghi nhận tuần tự. Chi tiết replay trong FINAL_PRODUCT_ACCEPTANCE/RUNTIME_EVIDENCE, ảnh trong screenshots/react. Full suite, không chỉ fixture demo, bảo toàn hợp đồng cũ. Hash8 raw files và8 historical manifests được kiểm tra, filing partial không bị đổi sang verified. Dữ liệu SEC mới PG/HD do chủ dự án cho phép là profile khác frozen nghiên cứu cũ.

Giới hạn thực nghiệm: hai PDF không đủ kết luận độ chính xác OCR/tài chính tổng quát; chỉ7 ô đối chiếu, nhiều bảng vẫn ứng viên. Nomic tiếng Việt chưa có held-out benchmark mới; không suy ra hybrid luôn thắng. Hai trong bốn diễn giải Qwen bị từ chối ở lượt ghi nhận, các draft còn lại vẫn cần kiểm tra. Chưa có giá/tin tức trực tiếp; chưa test GTX1650Ti mục tiêu. Sản phẩm là nguyên mẫu cục bộ cho khóa học, chưa là dịch vụ đa người dùng hoặc hệ thống tư vấn đầu tư được chứng nhận.

Đề nghị `FINANCIAL_INTELLIGENCE_PRODUCT_READY_WITH_LIMITATIONS`, chủ repository giữ quyền nghiệm thu cuối. Không merge Draft PR và không mở nghiên cứu milestone mới.
