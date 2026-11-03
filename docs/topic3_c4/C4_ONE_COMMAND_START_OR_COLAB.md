# Một lệnh mở bản demo đã kiểm thử trên máy chủ dự án

Tách rõ hai phần: **PR #36** chứa nghiên cứu G3U/C4 và log SEC phục hồi; **PR #35** chứa React/FastAPI sản phẩm. Không trộn mã hai PR. Máy này có worktree PR #35 ở commit `b5c6e1b43e7526bcebd8289fc85b580f4a4c1eef`, frontend đã build, `.venv` dùng junction tới môi trường hiện có, Ollama Nomic digest `0a109f422b47e3a30ba2b10eca18548e944e8a23073ee3f3e947efcf3c45e59f`. Bản sao workspace C4 chứa hai PDF READY; bản chủ gốc không được sửa.

Từ PowerShell, chạy lệnh đã thử thành công:

```powershell
cd C:\Users\Admin\Documents\GitHub\tinyllama-fastapi-pr35-demo
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_financial_studio.ps1 -Mode Prebuilt -ApiPort 18110 -Workspace 'C:\Users\Admin\Documents\GitHub\tinyllama-fastapi-pr35-demo\tmp\c4-demo-workspace'
```

Mở `http://127.0.0.1:18110/app/`; nhập khóa cục bộ từ `tmp/studio-runtime/access-token.txt` **riêng tư**, không chiếu hoặc sao chép vào slide. Kết quả khởi động thực tế: API và React HTTP 200, **2 PDF READY**, OCR READY, SEC trong worktree sản phẩm **UNAVAILABLE** do research root riêng chưa cấu hình. Tìm kiếm PDF không cần SEC. Phiên đã được dừng sau khi chụp sáu màn hình thật để giải phóng RAM; chạy lại lệnh trên khi cần demo. Nếu cổng đang sử dụng, kiểm tra trước khi chạy lại. Dừng đúng tiến trình do launcher tạo bằng `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_financial_studio.ps1 -Stop` trong worktree PR #35; không tắt Ollama hay các ứng dụng khác bằng lệnh này.

Lệnh demo đối đầu **không phát truy vấn G2 mới**; đọc lại Top-5 từ log G3U đã khóa. Trong worktree PR #36, thay `--question-id` bằng `V7A_G2_03_01` để cho thấy ca thua:

```powershell
cd C:\Users\Admin\Documents\GitHub\tinyllama-fastapi
.\.venv\Scripts\python.exe -m scripts.topic3_c4_demo_case --question-id V7A_G2_05_01 --results 'C:\Users\Admin\Downloads\C4_PRIVATE_20261103_V1\C4_PER_QUERY_ARM_RESULTS.jsonl' --blind-pool 'C:\Users\Admin\Downloads\G3U_ONE_SHOT_POOL_20261103_V2_APPROVED\G3U_BLIND_REVIEW_POOL.jsonl' --eligibility 'C:\Users\Admin\Downloads\C4_PRIVATE_20261103_V1\C4_JUDGED_ELIGIBILITY.json'
```

Đầu ra là ví dụ chọn **sau khi xem kết quả** và chỉ đo đúng filing, không đo đúng ô/đáp án. Đừng gọi là benchmark độc lập. Đối với Apple PDF 3/3, hồ sơ PR #35 đã ghi kiểm thử trước đó, nhưng SHA PDF Apple `3eb270b22acb7d8d8e9c32a43dc221dec3345f8e4bca02755fdbc1ee16c823de` **không hiện có** trong 85 PDF đã kiểm tra ở Downloads/repository. Không hứa chạy Apple live trên máy này nếu chưa bổ sung đúng file và lập chỉ mục có xác minh; dùng Hòa Phát/BIDV hiện có cho luồng sản phẩm. Không có lệnh Colab được kiểm thử trong C4; không trình bày một notebook chưa chạy như dự phòng sẵn sàng.
