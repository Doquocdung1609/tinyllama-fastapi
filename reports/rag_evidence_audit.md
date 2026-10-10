# RAG evidence audit

## Phương pháp

Mỗi câu được kiểm tra ở bốn lớp: candidate retrieval, evidence thực sự vào prompt, câu trả lời cuối và citation sau ánh xạ E-ID. Kiểm tra tự động bằng expected elements chỉ dùng để sàng lọc; trạng thái cuối trong cột `manual_assessment` được đối chiếu với trang nguồn. H20 được chạy riêng sau khi mã đã khóa và chỉ được ghép vào CSV sau khi chạy xong.

## Kết quả

| Tập | PASS | PARTIAL | FAIL | BLOCKED | Full pass | PASS + PARTIAL |
|---|---:|---:|---:|---:|---:|---:|
| Development (15) | 9 | 1 | 5 | 0 | 60.0% | 66.7% |
| Holdout (20) | 11 | 3 | 6 | 0 | 55.0% | 70.0% |
| P0 regression (5) | 5 | 0 | 0 | 0 | 100% | 100% |

Holdout không đạt ngưỡng 85%. Các lỗi tập trung ở câu tổng hợp nhiều cơ chế (H02, H03, H07, H10, H12, H17). Hai câu ngoài tài liệu H19 và H20 đều được từ chối về mặt nội dung; H20 vẫn gắn citation trang 235 không hỗ trợ tuyên bố, vì vậy citation của H20 bị chấm FAIL riêng.

## Tính toàn vẹn sau khóa

- Application lock: **OK**.
- Tệp khác hash: không có.
- Qdrant tài liệu chính vẫn dùng 971 vector hiện có; benchmark multimodal chạy bằng collection và thư mục tạm riêng.
