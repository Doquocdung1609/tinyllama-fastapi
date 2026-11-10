# Kết quả chạy thật

| Nhóm | Ca | PASS | PARTIAL | FAIL | BLOCKED | p50 ms | p95 ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| [Hồi quy API](acceptance-final.json) | 54 | 42 | 12 | 0 | 0 | 2585 | 4727 |
| [Hội thoại nối tiếp](followups.json) | 7 | 7 | 0 | 0 | 0 | 2387 | 2626 |
| [SEC có kỳ đo rõ](sec-precise.json) | 8 | 6 | 2 | 0 | 0 | 10419 | 32045 |
| Tổng lượt | 69 | 55 | 14 | 0 | 0 | | |

Các nhóm dùng lại một số câu hỏi và nguồn. Thời gian đo từ client, gồm lượt có cache và lượt khởi động lạnh.

- [Apple A01–A05](core-browser.json) có 8 kiểm tra browser. PASS 8, FAIL 0.
- [SEC nhập mới và Viewer](sec-browser-viewer.json) có 4 kiểm tra browser. PASS 4, FAIL 0.
- [PDF và Search](pdf-regressions/browser-e2e.json) có 56 kiểm tra browser. PASS 56, FAIL 0.

[Pytest](pytest-final.log) có 897 PASS. [Vitest](frontend-tests.log) có 36 PASS. [Vite](build.log) build thành công.

RSS API đỉnh quan sát được 409 MiB trong cửa sổ đo lấy mẫu. [Mẫu tài nguyên](resources.json).

Audit nguồn nghiên cứu riêng ghi 47 BLOCKED do thiếu raw bytes. Nhóm này được thống kê riêng với các lượt hỏi đáp.
