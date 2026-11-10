# V7P demo RC — thay đổi có giới hạn

Ngày kiểm tra: 2026-11-03, Windows/Python 3.13.2, Node 24.22.1, Chromium 147.0.7727.15. Tiếp tục Draft [PR35](https://github.com/Doquocdung1609/tinyllama-fastapi/pull/35) từ `53a1ab2d7722438912e4d1b13b5329b00af8ee29`; code kiểm thử: `209faf9988490ec9f8f6979f304b4e3852724d5a`. Đây là lượt kiểm tra mới bằng Codex, không phải đánh giá độc lập của con người.

- Home Depot hiển thị `109.384 triệu USD`; giữ riêng chuỗi gốc `109,384`, multiplier `1000000`, giá trị chuẩn hóa `109384000000 USD`. Formatter dùng chuỗi, giữ dấu và toàn bộ phần thập phân, không tính lại bằng floating point. Dấu âm iXBRL lấy từ Decimal đã xác minh, không suy luận chỉ từ chữ in trong ô.
- Đổi nhãn sai “Kỳ filing” thành kỳ báo cáo kết thúc; ngày nộp SEC, năm tài chính metadata, instant và duration được trình bày riêng. Backend chỉ bổ sung hai trường metadata đã có, không đổi kỳ hoặc verifier.
- Giải thích xác minh bytes gốc, bảng dẫn xuất giới hạn và giới hạn trích xuất bằng tiếng Việt. SHA/generation/manifest/locator/mã cảnh báo vẫn có trong phần mở rộng.
- Hàng vàng nhạt, cột xanh lam nhạt, ô chính xác xanh lá/viền đậm; giữ colspan/rowspan và tọa độ nguồn.
- Sửa lỗi thực tế khi trở lại từ SEC Viewer: scope lưu câu trả lời SEC chứa các trường PDF không được gửi trong HTTP SEC. Thay đổi lựa chọn PDF làm mất câu trả lời SEC dù câu hỏi không đổi. Scope nay bám đúng question/operation/ticker của SEC; thay ticker hoặc phép tính vẫn vô hiệu hóa kết quả cũ. PDF vẫn ràng buộc document ID.
- Bổ sung hồi quy metadata: re-upload trùng bytes không ghi đè hiệu chỉnh người dùng.

Ledger thay đổi: backend `app/product/sec_viewer.py`; UI `Studio.tsx`, `SecSourceViewer.tsx`, `api.ts`, `studio.css`; helpers `source-display.ts`, `analysis-scope.ts`; test `sec-source-viewer.test.tsx`, `test_v7p_metadata_chat.py`, `test_v7p_sec_viewer.py`; smoke driver `frontend/v7p_demo_rc_smoke.cjs`; sáu tài liệu RC, một JSON kết quả và bốn ảnh thật. Không xóa module/dependency, không đổi ranking/financial arithmetic, không thêm dịch vụ hoặc mô hình.

Ảnh: [SEC desktop](screenshots/rc-sec-viewer-desktop.png), [SEC mobile](screenshots/rc-sec-viewer-mobile.png), [chat](screenshots/rc-financial-chat.png), [upload READY](screenshots/rc-upload-ready.png).
