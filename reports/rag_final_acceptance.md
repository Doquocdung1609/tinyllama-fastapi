# General-purpose RAG final acceptance

## Chứng cứ thực thi

- P0 regression qua FastAPI thật: 5/5 PASS; Recall@5 100%, MRR 0.8667, evidence-in-prompt 100%, citation accuracy 100%, trung bình 22652.4 ms.
- Development: 9/15 PASS, 1 PARTIAL, 5 FAIL.
- Holdout chạy sau khóa: 11/20 PASS, 3 PARTIAL, 6 FAIL.
- Refusal ngoài tài liệu: D15, H19, H20 đúng về nội dung; H20 có citation không hỗ trợ và bị ghi lỗi citation.
- Application hashes sau holdout: **OK**.

## Quyết định

**P0 được chấp nhận; mục tiêu RAG tổng quát chưa được chấp nhận.** Holdout full-pass 55.0% thấp hơn ngưỡng 85% của master prompt. Hệ thống đã có evidence diagnostics, context budget xác định, citation validation và hỗ trợ modality, nhưng chưa đủ tin cậy để tuyên bố sẵn sàng dùng trực tiếp trong lớp học mà không có giám sát.

Các CSV giữ cả điểm tự động và `manual_assessment`/`manual_note`, giúp tái kiểm tra từng quyết định mà không dùng LLM tự chấm chính nó.
