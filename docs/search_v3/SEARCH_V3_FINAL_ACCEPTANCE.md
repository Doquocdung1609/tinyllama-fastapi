# Nghiệm thu Search V3 — 29/10/2026

**Đề xuất: SEARCH_V3_PARTIAL. Không đề xuất SEARCH_V3_LOCK_CANDIDATE;không tuyên bố LOCKED.** Chủ dự án giữ quyền nghiệm thu cuối. Không merge PR23/24 hoặc nhánh V3.

|Điều kiện|Kết quả|Bằng chứng|
|---|---|---|
|Chức năng/bảo vệ dữ liệu|PASS trong phạm vi kiểm tra|651backend,7frontend,build,pip,17ca nguồn,3Decimal,4ca doanh nghiệp;inventory gốc byte-identical|
|Nguồn/câu hỏi chưa dùng để sửa|PASS bounded|24câu REE/SEM sau freeze V3.2;36câu FOX/Samsung đã hạ thành retest|
|Issuer/period/basis nghiêm trọng|PASS bounded / PARTIAL tổng quát|Ca Apple đã tái hiện và sửa;không chứng nhận mọi alias/ngôn ngữ/cột|
|False abstention|MEASURED / PARTIAL|Tách rỗng kết quả và quyền trả lời số;2positive reviewed dev PASS;unseen positives chưa được chứng nhận quyền trả lời|
|Provenance tái lập|PASS bounded|SHA nguồn/nhãn/policy,8arms,splits,từng câu,21ảnh nguồn và hướng dẫn replay|
|Trích xuất đủ chỉ tiêu nguồn mới|FAIL|7chỉ tiêu SEM có trong ảnh gốc nhưng thiếu trong checkpoint;READY không chứng minh đầy đủ|
|Hiệu năng và độ bao phủ|PARTIAL|Warm V3 p95=1940.6ms;cold UI23.3s;còn miss SEC và nguồn mới|
|Gói rà soát độc lập|READY / AUDIT PENDING|84câu,giá trị/trang/tọa độ/ảnh,phương pháp dẫn đầu và tranh chấp;0human adjudications|

Final24câu source-unseen:V3 MRR@5=0.333,Recall@5=0.315;B2 tương ứng0.011/0.056. Đây là đo truy nguồn,không phải accuracy trả lời tài chính. Nhãn do Codex tạo,không phải human review độc lập. Một lần freeze đầu đã bị vô hiệu vì lỗi thật;policy/nhãn cũ được giữ lại,không giấu quy trình reset. Tập cuối không được dùng để sửa policy sau test.

Windows Prebuilt:PASS mở đúng CEO PDF/trang2,tô sáng ô đã đối chiếu;dòng ứng viên chưa xác minh có nhãn riêng;truy vấn thiếu kỳ chỉ giữ đoạn liên quan;so sánh baseline/candidate cùng câu hỏi/phạm vi;phản hồi cũ sau đổi truy vấn bị bỏ qua. 6ảnh thật ở screenshots/. Ca chính PASS36.6s,ca Candidate Row PASS3.5s. Giữ nguyên B0/B1/B2 và C1/C2/C3/C4,API cũ mặc định baseline;UI có lựa chọn rollback.

Ứng dụng đang chạy tại http://127.0.0.1:8110/app/ . Lệnh thực tế từ thư mục repository:

```powershell
.\scripts\run_financial_studio.ps1 -Mode Prebuilt -Workspace .\studio_workspace\search-v2-v3-20261029
```

Giới hạn cần nói rõ khi trình bày:chưa đủ để demo tuyên bố tìm đúng mọi bảng/mọi câu hỏi;SEM mixed-image hiện thất bại,query đầu xây index chậm,cột KRW chưa hỗ trợ xác minh/tính số trong dịch vụ VND/USD hiện tại. Chỉ dùng ca nguồn đã kiểm tra và gắn nhãn đúng mức. Cần sửa phát hiện bảng ảnh rồi dùng nguồn mới và owner audit trước khi xem xét LOCK. Không có model/framework/dịch vụ trả phí mới;không thay Nomic digest,vector SEC lịch sử,PDF gốc hoặc workspace của chủ máy.

Đọc SEARCH_V3_EVALUATION_REPORT.md,SEARCH_V3_FAILURE_REPAIR_LOG.md và SEARCH_V3_OWNER_AUDIT_PACKET.md để kiểm tra bằng chứng. CI trên đúng commit cuối sẽ được liên kết trong Draft PR;không dùng CI của commit cũ làm bằng chứng.
