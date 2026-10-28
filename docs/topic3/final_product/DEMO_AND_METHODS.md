# Demo và giải thích phương pháp

## Câu hỏi demo

| Nguồn | Câu hỏi | Kết quả mong đợi |
|---|---|---|
| PDF fixture tổng hợp `C_financial_statement.pdf` | `Tổng tài sản` | BM25, Dense, Hybrid trả chunk trang 1; viewer tô đúng cụm trên PDF. Các số trong fixture chỉ dùng để thử UI. |
| SEC P&G | `What were P&G's net sales for the three months ended September 30, 2026?` | Financial AI có nguồn SEC, 23,276,000,000 USD, ô `NET SALES` 23,276 × 1,000,000, duration 2026-07-01 đến 2026-09-30. Đây là ca đã được nguồn xác minh, không phải cam kết cho câu hỏi tùy ý. |
| SEC HD | `HD total assets` | So sánh BM25/Dense/Hybrid trên cùng generation; mở hàng Total assets của 10-Q và filing chính thức. |
| SEC COST | `What was Costco operating cash flow in 2031?` | Từ chối `NEEDS_CLARIFICATION`, không trả số. |

## Phương pháp

**BM25** chấm mức khớp từ trong parent/chunk. **Dense** biến câu hỏi và đoạn tài liệu thành vector Nomic 768 chiều, rồi truy xuất cosine từ Qdrant. Prefix query là `search_query: `; prefix tài liệu là `search_document: `. **Hybrid** hợp nhất danh sách theo Reciprocal Rank Fusion với `k=60`, dựa trên canonical chunk ID. Điểm RRF là điểm thứ hạng, không phải xác suất đúng.

Trang So sánh cho biết rank B/D và độ trễ đo theo từng request HTTP. Không hiển thị Recall/MRR/nDCG nếu không có bộ qrels phù hợp. Bộ P11 vẫn là nghiên cứu development có nhãn provisional; không phải chứng nhận Hybrid vượt BM25.

## Ảnh giao diện thực

Các ảnh trong [`screenshots/`](screenshots/) là kết quả trình duyệt trên dịch vụ cục bộ; [`../ui_references/`](../ui_references/) là mock UI có số liệu minh họa, không phải bằng chứng. Ảnh [PDF highlight](screenshots/pdf-highlight-desktop.jpg) hiển thị tài liệu fixture tổng hợp, trang 1, tô vàng đúng hàng. Ảnh [Financial AI](screenshots/financial-ai-desktop.jpg) hiển thị câu trả lời SEC P&G và nguồn. Ảnh [upload READY](screenshots/library-upload-ready.jpg) ghi lại upload qua Streamlit.
