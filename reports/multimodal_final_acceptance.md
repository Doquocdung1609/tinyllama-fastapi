# Multimodal PDF RAG final acceptance

## Kết quả API thật

| Metric | Kết quả |
|---|---:|
| Test cases | 20 |
| PASS | 15 (75.0%) |
| PARTIAL | 1 (5.0%) |
| FAIL | 3 (15.0%) |
| BLOCKED | 1 (5.0%) |
| PASS + PARTIAL | 80.0% |
| Citation accuracy trên câu supported | 88.9% |
| End-to-end trung bình | 7670.2 ms |

Các lỗi còn lại: T02 không tính tăng trưởng 25%; T06 bỏ chuỗi B; T14 không so sánh được chart với nhãn text. T07 chọn đúng nhóm nhưng bỏ tỷ lệ 50%. T11 bị chặn đúng do thiếu OCR engine. T15 là refusal đúng theo đối chiếu thủ công dù bộ dò từ khóa ban đầu đánh FAIL.

## Quyết định

**Chưa đạt full acceptance.** Mục tiêu citation 90% bị hụt một trường hợp, OCR scan chưa chạy được, và ba câu hỏi chart/table có đủ evidence vẫn FAIL. Fixture hiện chứng minh text + table và text + chart riêng; chưa chứng minh một trang duy nhất kết hợp đồng thời text + table + chart.

Tiny-SD và 971 vector Qdrant chính được giữ nguyên. Benchmark multimodal dùng collection/thư mục tạm riêng.
