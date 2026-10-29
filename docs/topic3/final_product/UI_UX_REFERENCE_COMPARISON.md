# Đối chiếu giao diện tham chiếu

Đã đọc README và bảy PNG 1600×1000 trong docs/topic3/ui_references trước thiết kế. Screenshots giao hàng trong screenshots/react là ảnh Chromium thật, không mock và không chỉnh sửa.

| Tham chiếu | React thực tế | Khác biệt có chủ đích |
|---|---|---|
| Navy sidebar / header trắng / nền sáng | giữ nhận diện, icon Lucide, sáu mục tiếng Việt | số liệu readiness thật |
| Overview cards / pipeline | CTA hai luồng, số PDF/SEC/chunks/OCR | không chép tài sản/biểu đồ minh họa |
| Search filters & results | mode, top-k, market/company/period/doc, rank & score thật | bố cục kết quả + context hai cột thay vì ép ba cột |
| Analysis | ba tab QA/numeric/research, source facts cạnh câu hỏi | form kỳ/scope/basis rõ ràng; từ chối hiển thị nổi bật |
| Library | drag-drop, progress, table, source/retry | không ước lượng tiến độ giả, không coi reconstruction là verified |
| Comparison | ba cột cùng snapshot, Recharts latency/overlap | không tự tạo Recall/MRR/nDCG cho truy vấn mới |
| PDF viewer | native/OCR layers, zoom/page/rotation, annotation màu | SEC HTML mở nguồn+locator riêng, không giả PDF |
| System | service/index/OCR/models/RAM từ API | phần kỹ thuật nằm trong chi tiết/chẩn đoán |

Đã kiểm tra ảnh đủ sáu trang, OCR HPG3/5, native BIDV6, kết quả Decimal, abstention, company report và SEC. Viewport thực 1600×1000, 1366×768, 390×844; kiểm tra không tràn ngang trang ở màn hình hẹp. Viewer trang rộng có vùng cuộn riêng. Headings, filename ellipsis, status nowrap và khoảng cách đã sửa sau visual QA. Research report dài vì giữ trích đoạn và nguồn đọc được; không dựng một đoạn tổng hợp tự tin khi LLM bị guard từ chối.

Danh mục ảnh: 01–06 sáu trang; 07 PDF scan; 08 mobile; 09 ô đối chiếu; 10 trang xoay; 11 Decimal; 12 từ chối; 13–14 BIDV; 15 research; 16–18 SEC; 19 màn hình 1366; 20 prebuilt (nếu kiểm tra thành công).
