# Bằng chứng dự phòng từ phiên demo C4 thật

Phiên sản phẩm dùng PR #35 commit `b5c6e1b43e7526bcebd8289fc85b580f4a4c1eef`, React/FastAPI tại `127.0.0.1:18110`, bản sao workspace riêng. Sáu ảnh dưới đây được chụp **sau đăng nhập local và sau các thao tác thực**, lưu ngoài Git tại `C:\Users\Admin\Downloads\C4_PRIVATE_20261103_V1\screenshots\`. [Manifest SHA đầy đủ](C4_PRIVATE_ARTIFACTS_MANIFEST.json) ghi bytes/hash từng ảnh; không có token trong ảnh hoặc Git.

| Ảnh máy chủ dự án | Điều chứng minh | SHA-256 |
| --- | --- | --- |
| `01_financial_assistant.png` | React trợ lý mở, kết nối FastAPI/Ollama | `2954e4d722c6b48bf5f40c17e6ed6e2895b90e7069e06a6f72889e1ef380a549` |
| `02_library_ready.png` | BIDV + HPG đều READY | `33dd3cca0028b6513f919a3e4151a2b771fd6d006f35351be1c7244e49ee6935` |
| `03_bidv_search_evidence.png` | Truy vấn BIDV, bằng chứng ứng viên trang 8 | `65c610df0123e2c4499cc0f72eb753d8673e227b85ca1e4291e751c3bd8cc476` |
| `04_bidv_three_method_live.png` | BM25/Dense/Hybrid chạy cùng câu hỏi, cùng PDF trên React | `f42bd01d3c954a25eeed2daa8e7e241bf4710c41fca9415ff10f14ed63accb29` |
| `05_hpg_scanned_search.png` | HPG Q4/2025 scan tìm ra trang 5, OCR có lỗi ký tự | `0e64ac4d0a270ccb618e79e47e4c52a214aea2f17b64fba2a3259e70ee7d4487` |
| `06_hpg_pdf_viewer.png` | Viewer PDF trang 5/24 và lớp OCR/Tesseract | `327ea6eb320432d662704c98dc6d6477b6bb74796226504f76d528f48e875274` |

API smoke riêng tư SHA-256 `9a0ce8f70d5e97fe70114a6e32b8ed775e2213426d46ab11530b038eef4fbaa8`: hai PDF đúng bytes, sáu tổ hợp 2 câu × 3 phương pháp đều HTTP 200/5 kết quả. HPG: Top-1 trang 24 cho BM25/Dense/Hybrid trong lần API; trên React lượt sau Top-1 trang 5 do pipeline/config và cache có thể khác, không ghép hai lượt thành một thước đo. BIDV API Top-1 BM25 trang 1, Dense/Hybrid trang 8. Câu hỏi số **hợp nhất** trên PDF **công ty mẹ** HPG trả HTTP 200 với `QUERY_CONTEXT_CONFLICT`, không giá trị/citation; đây là từ chối đúng phạm vi, không phải trả lời số.

Sản phẩm SEC status là `UNAVAILABLE` trong worktree PR #35 vì không cấu hình research roots; màn hình Research Lab có một số kết quả lịch sử nên khi trình bày phải tách khỏi ba cột PDF live. Apple PDF dùng cho kiểm thử 3/3 trước đó không có trong bộ file hiện tại; không khẳng định Apple live. Nếu dùng ảnh thay live, công bố rõ đây là ảnh phiên C4.
