# Đối chiếu 7 ảnh tham chiếu UI/UX

Ảnh trong `docs/topic3/ui_references/` là concept 1600×1000. Số tài chính, số tài liệu, nhãn READY và độ trễ trong ảnh **không** được dùng làm dữ liệu sản phẩm. Bố cục triển khai bằng Streamlit ưu tiên cùng thứ tự tác vụ và hệ màu navy/blue/cyan; trên viewport hẹp các cột xếp dọc.

| Ảnh concept | Giao diện đã triển khai | Tương tác và dữ liệu thực | Giới hạn |
|---|---|---|---|
| `01_trang_chu_tong_quan.png` | Tổng quan: hai CTA, số filing/parent/PDF và trạng thái | P7/P10 catalog, PDF workspace, Research API health | Không sao chép số concept; số thay đổi theo snapshot |
| `02_tim_kiem_tai_chinh.png` | Search với nguồn, mode, top-k, issuer/kỳ, danh sách hạng và preview | `/studio/sec/search`, `/studio/search` | SEC top-k có thể xếp chứng cứ không đúng metric lên trước; không hứa chất lượng tổng quát |
| `03_xem_tai_lieu_highlight.png` | Viewer ngữ cảnh 2 cột, PDF trái và evidence phải | PNG từ PDF thật, `page.search_for`, chunk hash, source hash; [ảnh thật](screenshots/pdf-highlight-desktop.jpg) | SEC HTML không có highlight tọa độ trên tài liệu chính thức |
| `04_phan_tich_tai_chinh_ai.png` | Câu hỏi, Decimal, source cells, citation, abstention | `/research/v1/query` real SEC; [ảnh thật](screenshots/financial-ai-desktop.jpg) | Chỉ metric/period được adapter hỗ trợ |
| `05_tai_lieu_len_pipeline.png` | Library tab Upload với progress UPLOADED/PROCESSING/READY/FAILED | Upload HTTP qua UI, worker PDF riêng; [ảnh READY](screenshots/library-upload-ready.jpg) | Không có OCR bảo đảm cho PDF ảnh |
| `06_kho_tai_lieu_he_thong.png` | Library và System thành hai trang đúng yêu cầu sáu trang | Document list và health/resources thực; [ảnh System](screenshots/system.jpg) | Chỉ điều khiển reconnect, không tự xóa/chuyển generation |
| `07_danh_gia_so_sanh_bm25_dense_hybrid.png` | So sánh ba cột và nguồn giao nhau | Ba HTTP call trên cùng generation; [ảnh thật](screenshots/retrieval-comparison-desktop.jpg) | Không có metric chất lượng nếu thiếu qrels hợp lệ |

Khác concept: viewer không là top-level page vì người dùng yêu cầu **đúng sáu** trang; nó mở từ Search/AI/Library. Chúng tôi không dựng một PDF giả từ SEC HTML hay dùng fragment không được xác minh. Các số trong ảnh tham chiếu không xuất hiện cố định trong mã giao diện.
