# Bàn giao C4 cho buổi trình bày 04/11/2026

**Sẵn sàng demo có giới hạn:** React PR #35 đang chạy được ở `http://127.0.0.1:18110/app/` với HPG/BIDV trong bản sao workspace, Ollama Nomic đã có, OCR READY. Lệnh mở, kịch bản và ảnh dự phòng ở [runbook](C4_DEMO_RUNBOOK.md), [một lệnh](C4_ONE_COMMAND_START_OR_COLAB.md), [bằng chứng](C4_BACKUP_DEMO_EVIDENCE.md). Không đưa local access token lên slide. Kiểm tra service và model trước giờ lên lớp; trạng thái hiện tại không bảo đảm laptop sẽ còn mở qua đêm.

**Nghiên cứu trình bày được:** [scorecard](C4_SCORECARD_VI.md) là kết quả proxy thực của pool một lần chạy, 93 câu hợp lệ, 18 arm×index, Top-1/5/10, Win/Tie/Loss và p50/p95 có giới hạn. Cả ca thắng và thua có lệnh xuất Top-5 original chunk. Hãy nói ngay rằng FAITH-R A4 chưa thắng tổng thể và 46 câu bị target loại bởi mismatch fiscal metadata/filter. Không gọi kết quả 67 câu là toàn 94. Bảng phủ qrels theo K chỉ là AI-provisional; không có nDCG/MRR/Recall.

**Nguồn và review:** log 102 event chain hợp lệ nhưng reviewer identity tự khai. 67 release-preview, 19 cấu trúc nguồn bị chặn, 7 cần sửa, 1 loại; 0 original-single-chunk EXACT/human qrels. File CSV trạng thái đính kèm có hash cũ ở `25_02`; dùng log JSONL 102 sự kiện. Giữ toàn bộ dữ liệu riêng tư và token ngoài Git.

**Phần chưa được chứng minh live trong C4:** Apple PDF của PR #35 3/3 không còn trên máy tại lần kiểm 85 đường dẫn PDF; SEC research roots không bật trong worktree sản phẩm. Các minh họa Apple SEC dùng log nghiên cứu riêng, không phải PDF sản phẩm. Đừng hứa Apple chat 3/3 live trừ khi file nguồn đúng SHA được cung cấp và chạy xác minh trước.

**Việc thực tế kế tiếp:** dùng phiên demo HPG/BIDV đã chạy, in [9 slide](C4_SLIDE_OUTLINE_VI.md) và [hỏi đáp](C4_TEACHER_QA_VI.md). Sau buổi trình bày, thiết kế sửa fiscal filter/metadata như một phiên bản mới với tập câu độc lập và thêm human qrels, thay vì chạy lại holdout G2 đã lộ.
