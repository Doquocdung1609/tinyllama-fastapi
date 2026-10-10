# RAG reliability: root cause và bản sửa

## Nguyên nhân trực tiếp của lỗi P0

Pipeline cũ trộn điểm dense và lexical ở hai thang đo khác nhau, rồi mở rộng hàng xóm trước khi phân bổ context. Candidate đứng đầu ở trang 73 được đưa vào trước; các chunk kề 74–75 chiếm phần lớn ngân sách ký tự. Candidate trực tiếp trang 155–156 vẫn hiện trong reranked candidates nhưng bị cắt khỏi final prompt. Vì vậy E1–E8 đều trỏ vào vùng 73–75 và Qwen chỉ có thể kết luận rằng tài liệu không nêu số loại.

Các điểm mã liên quan trong bản hiện tại:

- `app/services/rag_service.py:81`: tách query facets cho câu hỏi tổng hợp.
- `app/services/rag_service.py:594`: chọn context theo ngân sách xác định, direct evidence trước.
- `app/services/rag_service.py:733`: diagnostic ngân sách direct/neighbor và lý do loại.
- `app/services/rag_service.py:276`: audit citation theo đúng included evidence.
- `app/services/rag_service.py:336`: grounding từng claim sau generation.
- `app/services/rag_service.py:895`: luồng query thật; retrieval facets bắt đầu ở dòng 942.

## Bản sửa tối thiểu

1. Weighted reciprocal-rank fusion thay cho cộng raw score không đồng nhất.
2. Direct candidates được cấp ngân sách trước; neighbor chỉ được thêm khi còn chỗ và đủ liên quan.
3. Deduplicate overlap theo nội dung và chunk ID; không để một candidate cùng hàng xóm độc chiếm context.
4. Mỗi E-ID được tạo từ đúng `included_prompt_context`; mọi chunk bị loại có reason máy đọc được.
5. Citation cuối chỉ được ánh xạ từ E-ID hợp lệ, sau đó audit từng claim và giảm phần không có nguồn thành thông báo giới hạn.
6. Không hardcode câu trả lời, trang 155/156 hay ngoại lệ theo query.

## Kết quả P0

R04 “Đổi mới tài chính có mấy loại?” trả lời cả hai hệ phân loại: ba loại theo loại hình ở trang 155 và tám nhóm chức năng ở trang 156. R05 vẫn trả lời đúng ba loại ở trang 155. R01–R03 cũng PASS và câu ngoài tài liệu trong development/holdout được từ chối. Prompt chính xác trước sửa được lưu ở `rag_prompt_before_complete.txt`; prompt sau sửa gồm cả bước generation và deterministic repair ở `rag_prompt_after_complete.txt`.

Kết quả này sửa đúng regression P0. Holdout tổng quát đạt 11/20 PASS, thêm 3 PARTIAL; do đó chưa thể suy rộng thành độ tin cậy phổ quát.
