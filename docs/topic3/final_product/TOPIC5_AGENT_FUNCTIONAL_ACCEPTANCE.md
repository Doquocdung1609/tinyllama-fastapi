# Topic 5 — Financial RAG và công cụ nghiên cứu

| Tiêu chí | Bằng chứng | Kết quả |
|---|---|---|
| Câu hỏi tiếng Việt / đúng công ty & kỳ | HPG riêng 2025; BIDV hợp nhất điều chỉnh 2024 | PASS |
| Đọc giá trị đã xác minh | 7 ô đã đọc ảnh nguồn, record gắn hash và geometry | PASS xác minh cục bộ |
| Tính toán có nguồn | HPG chênh lệch, accounting identity; BIDV restatement check | PASS Decimal |
| Từ chối thiếu bằng chứng | sai năm, sai metric, sai scope, sai công ty | PASS 4/4 ca cụ thể |
| Quy trình nhiều công cụ | 8 event thực, job persisted; retrieval độc lập context/fundamentals/risks | PASS |
| Báo cáo tiếng Việt có nguồn | quotes, verified facts, 2 phép tính, nguồn và giới hạn | PASS document-only |
| Diễn giải local LLM | Qwen đã chạy 4 stage; hai draft qua guard, hai draft bị từ chối; trạng thái từng stage có thể thay đổi giữa các lượt, xem RUNTIME_EVIDENCE | PARTIAL chất lượng diễn giải |
| Nguồn giá/tin tức | chưa có connector; UNAVAILABLE kèm timestamp; báo cáo vẫn hoàn tất | PASS xử lý vắng nguồn; dữ liệu trực tiếp NOT_TESTED |
| Định giá / khuyến nghị giao dịch | không đủ market inputs, không sinh BUY/SELL | ngoài phạm vi |

Đây là orchestration có giới hạn, không phải các chuyên gia tự trị độc lập. Synthesis luôn tổng hợp các mục đã truy xuất và nguồn thực. Khi LLM draft không hợp lệ, dùng trích đoạn và kết luận giới hạn thay vì nhận bừa một đoạn văn trôi chảy. Các draft không có chữ số và có citation vẫn cần người đọc kiểm tra nội dung; guard không chứng minh entailment.

Phép tính trong báo cáo HPG: tài sản tăng 16.877.702.175.961 đồng; nợ/tài sản 4,2969…% (API giữ Decimal đầy đủ; UI rút phần lẻ và ghi dấu …). Không suy ra mức rủi ro, giá trị cổ phiếu hoặc độ chính xác tài chính tổng quát từ hai phép tính này. Không lấy số liệu trong OCR quote chưa đối chiếu làm toán hạng.

Financial QA SEC hiện hữu tiếp tục xác thực raw iXBRL/header/period/scale/parent trước trả số: HD 109.384.000.000 USD; PG 23.276.000.000 USD. Câu HD năm 2031 từ chối. Điều này không chứng nhận mọi câu hỏi tài chính.
