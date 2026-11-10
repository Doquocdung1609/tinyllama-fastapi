# Quyết định RC demo

**V7P_PRODUCT_DEMO_RELEASE_CANDIDATE_WITH_EXTERNAL_SEC_LIMITATION**

Phạm vi: demo cục bộ có xác minh nguồn cho các câu hỏi đã hỗ trợ. Không thay historical `V7P_NOT_ACCEPTED`, không tuyên bố `V7P_PRODUCT_ACCEPTED` theo A0–A11 cũ. A7-LOCAL giữ PASS; A7-EXTERNAL giữ EXTERNAL_ACCESS_BLOCKED. Không merge, không production certification, không kết luận thuật toán tổng quát.

PR35 vẫn Draft/open/unmerged, base PR34. Code mới `209faf9988490ec9f8f6979f304b4e3852724d5a`; evidence commit thêm sáu tài liệu RC, bốn ảnh, một JSON và điều chỉnh driver đợi sidebar mobile đóng trước khi chụp. Không đổi accepted application code sau các lượt regression. Final delivery SHA và exact-head CI được ghi trong checks/body PR35 và bàn giao, tránh tự tạo SHA tự tham chiếu trong chính commit.

## Bằng chứng nghiệm thu

- Real Chromium147 + authenticated HTTP: **10/10**; page_errors=[]; [JSON](V7P_RELEASE_CANDIDATE_RESULTS.json), [QA](V7P_FINAL_USER_JOURNEY_QA.md).
- Frontend Node24: `tsc -b`, `vitest run --config vitest.config.ts`, `vite build`: **30 tests/3 files PASS**, typecheck/build PASS. Previous15 tests giữ nguyên; tăng thêm15 case hiển thị/scope/sign/precision.
- Code-head CI [core41495835003](https://github.com/Doquocdung1609/tinyllama-fastapi/actions/runs/41495835003) trên `209faf9988490ec9f8f6979f304b4e3852724d5a`: completed SUCCESS. Exact final evidence-head CI được kiểm tra riêng trong PR35 trước bàn giao.
- Python `python -m pytest -q`: **818 PASS**, 0 FAIL/SKIP, 1 cảnh báo Starlette có sẵn, 99,62s. `python -m pytest -q -m "not integration"`: **818 PASS**, 0 FAIL/SKIP, 1 cảnh báo, 89,09s. `python -m compileall -q app scripts` và `git diff --check`: PASS. Trường `regression` trong JSON RC ghi chính xác lệnh/tổng số; CI exact final HEAD phải hoàn tất trước bàn giao.
- Windows Prebuilt launcher restart thật, cùng workspace giữ dữ liệu READY. Không dừng owner Ollama. [Hướng dẫn + kịch bản](V7P_DEMO_SCRIPT_FOR_PROFESSOR.md).
- 843 frozen blobs khớp, original A7 không đổi, HD bytes giữ hash. [Audit](V7P_RESEARCH_ISOLATION_FINAL_CHECK.md).
- Security regressions giữ trong full/frontend tests: signed-reference/hash/membership/auth/locator, escaped HTML/unsafe links/stale source. Lượt RC không tái chạy mọi clone-only live fault injection cũ; bằng chứng live fault trước đó vẫn ở báo cáo A7, không gắn nhãn thành lượt live mới.

## Giới hạn và quyết định tiếp theo

Cho phép nhóm sử dụng demo với kịch bản đã ghi và dữ liệu local đúng cấu hình. Chưa hỗ trợ mọi statement/layout/metric; HPG OCR numeric vẫn từ chối. Metadata hiệu chỉnh chỉ là nhãn người dùng, không thay bytes hay chứng minh issuer của nguồn. Viewer là bảng dẫn xuất có giới hạn, không full filing renderer; official SEC exact-cell navigation chưa xác minh và site chặn automation. Máy mới cần dữ liệu và dependencies thực; không commit snapshot bí mật/token hay tải model tự động.

Không có HIGH/CRITICAL mới được tái hiện còn mở trong phạm vi sửa UX này. Rủi ro nguồn upstream/storage local và giới hạn tài chính cũ vẫn có. Bước tiếp theo là owner review PR35/demo; nghiên cứu FAITH-R tiếp tục ở workstream riêng, không khởi động milestone mới trong task này.
