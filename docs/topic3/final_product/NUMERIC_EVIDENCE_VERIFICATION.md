# Kiểm chứng bằng chứng số

Không dùng LLM để đoán hoặc sửa chữ số. Fact chỉ đủ điều kiện sau khi đọc ảnh gốc và ràng buộc hàng/cột, label thực, ngày/kỳ, currency/scale, báo cáo riêng/hợp nhất, basis và quy ước dấu số. Header phải hiện trên nguồn và khớp vị trí cột; không tự chế header. Audit history bất biến, raw hash, page/layout hash và ô hiện tại được kiểm tra trước tính toán. Xác minh PDF là thao tác cục bộ của người đọc, khác xác thực iXBRL SEC.

| Nguồn / locator | Giá trị đọc trực tiếp | Đơn vị / kỳ / scope |
|---|---|---|
| HPG PDF 3, TỔNG CỘNG TÀI SẢN, cột 31/12/2025 | 98.670.778.691.605 | VND, riêng công ty mẹ |
| HPG PDF 3, cùng hàng, cột 01/01/2025 | 81.793.076.515.644 | VND, riêng công ty mẹ |
| HPG PDF 4, NỢ PHẢI TRẢ, cột 31/12/2025 | 4.239.852.223.395 | VND, riêng công ty mẹ |
| HPG PDF 4, VỐN CHỦ SỞ HỮU, cột 31/12/2025 | 94.430.926.468.210 | VND, riêng công ty mẹ |
| BIDV PDF 6, TỔNG TÀI SẢN, Số liệu đã công bố | 2,760,791,854 | triệu đồng, 31/12/2024 hợp nhất |
| BIDV PDF 6, cùng hàng, Điều chỉnh | +115,110 | triệu đồng, cùng kỳ/scope |
| BIDV PDF 6, cùng hàng, Số trình bày lại | 2,760,906,964 | triệu đồng, cùng kỳ/scope |

Tọa độ/row ID và hash của các ảnh nguồn đối chiếu trong SOURCE_REVIEW_FIXTURES.json. Đây là annotation kiểm chứng, không phải bảng đáp án được app import. Bản chạy thật tạo reviewed facts qua API/React, không hardcode số vào backend.

5 ca trả kết quả đúng: HPG extract; HPG current−previous = **16.877.702.175.961 VND**; HPG liabilities+equity−assets=0; BIDV restated extract=**2.760.906.964 triệu VND**; BIDV original+adjustment−restated=0. 4 ca từ chối: 2031, hỏi doanh thu nhưng assets, hỏi hợp nhất từ báo cáo riêng, hỏi BIDV nhưng chọn HPG. API giữ Decimal strings và normalization base, không đổi sang float trong React. Phép tỷ lệ nghiên cứu HPG 4,296968443561832861907895198112151720438% giữ đầy đủ trong API; UI chỉ rút gọn hiển thị có dấu ….

Regression kiểm tra dấu thập phân/nhóm, âm ngoặc, dash/blank không phải zero, hình học header, sai period/unit/scope, thiếu toán hạng, record/audit/source tamper, số từ optional LLM bị chặn. Không có kết luận “financially accurate” cho mọi câu hỏi; các ca hiện tại là bounded reproducible evidence.
