# V3R2 — Phiếu đối chiếu nguồn độc lập

Trạng thái: **CHƯA CÓ NGƯỜI DUYỆT**. Các nhãn tham chiếu đều do agent chuẩn bị, cần đối chiếu ảnh gốc. Không dùng phiếu để tự nâng trạng thái số liệu trong ứng dụng.

Mở `V3R2_HUMAN_AUDIT_RESULTS.xlsx`, điền các cột vàng B–E. Giữ thư mục `source_images/` cạnh bảng; cột M là đường dẫn ảnh tương đối. Với mỗi ca, xem cả cột hiện tại/kỳ trước, tiền tệ, đơn vị, dấu và dấu phân cách. Đánh dấu ĐÚNG/SAI/CHƯA RÕ và ghi người/ngày duyệt. Không suy ra số 0 từ dấu gạch hoặc ô trống.

Phiên bản `production_v3r2`; generation `2033a0cf0d057fdf36f5ec6e894a639c283cbc4b562b6823abf973acfea7d8dc`. Toàn bộ quyết định người thật để trống trong JSON/XLSX. Kiểm thử công thức bằng Artifact Tool và cấu trúc tệp xuất; chưa chạy Microsoft Excel bản địa.

| Đã đối chiếu | Mã ca | Câu hỏi | Nguồn |
|---|---|---|---|
| [ ] | SEM-assets | Total assets Samsung Electro-Mechanics consolidated December 31, 2025 | [Ảnh 1](source_images/SEM-p7.png) |
| [ ] | SEM-liabilities | Tìm tổng nợ phải trả hợp nhất Samsung Electro-Mechanics cuối năm 2025 | [Ảnh 1](source_images/SEM-p8.png) |
| [ ] | SEM-equity | Total equity Samsung Electro-Mechanics consolidated December 31, 2025 | [Ảnh 1](source_images/SEM-p8.png) |
| [ ] | SEM-cash_equivalents | Tiền và các khoản tương đương tiền Samsung Electro-Mechanics hợp nhất ngày 31/12/2025 | [Ảnh 1](source_images/SEM-p7.png) |
| [ ] | SEM-inventory | Inventories Samsung Electro-Mechanics consolidated December 31, 2025 | [Ảnh 1](source_images/SEM-p7.png) |
| [ ] | SEM-pretax_income | Profit before tax from continuing operations Samsung Electro-Mechanics year 2025 | [Ảnh 1](source_images/SEM-p9.png) |
| [ ] | SEM-net_income | Lợi nhuận sau thuế cả năm Samsung Electro-Mechanics hợp nhất năm 2025 | [Ảnh 1](source_images/SEM-p9.png) |
| [ ] | ACB-v3r-acb-06 | Owners equity ACB consolidated December 31, 2022 | [Ảnh 1](source_images/ACB-p8.png) |
| [ ] | ACB-v3r-acb-07 | Profit before tax ACB consolidated full year 2022 | [Ảnh 1](source_images/ACB-p10.png) |
| [ ] | ACB-v3r-acb-08 | Profit after tax ACB consolidated full year 2022 | [Ảnh 1](source_images/ACB-p10.png) |
| [ ] | PNJ-v3r-pnj-01 | Tổng tài sản PNJ hợp nhất ngày 31/12/2025 | [Ảnh 1](source_images/PNJ-p3.png) |
| [ ] | PNJ-v3r-pnj-03 | Tiền và các khoản tương đương tiền PNJ hợp nhất cuối năm 2025 | [Ảnh 1](source_images/PNJ-p3.png) |
| [ ] | PNJ-v3r-pnj-08 | Lợi nhuận sau thuế PNJ hợp nhất lũy kế cả năm 2025 | [Ảnh 1](source_images/PNJ-p5.png) |
| [ ] | REVIEWED-1 | Tổng tài sản công ty mẹ Hòa Phát ngày 31/12/2025 | [Ảnh 1](source_images/HPG-p3.png) |
| [ ] | REVIEWED-2 | Tổng tài sản công ty mẹ Hòa Phát ngày 01/01/2025 | [Ảnh 1](source_images/HPG-p3.png) |
| [ ] | REVIEWED-5 | Tổng tài sản hợp nhất BIDV số trình bày lại ngày 31/12/2024 | [Ảnh 1](source_images/BIDV-p6.png) |
| [ ] | REVIEWED-6 | Tổng tài sản hợp nhất BIDV số đã công bố ngày 31/12/2024 | [Ảnh 1](source_images/BIDV-p6.png) |
| [ ] | NEG-v3r-pnj-09 | Total assets PNJ consolidated year 2037 | [Ảnh 1](source_images/PNJ-p3.png) |
| [ ] | NEG-v3r-pnj-10 | Total assets ACME consolidated 2025 | [Ảnh 1](source_images/PNJ-p3.png) |
| [ ] | NEG-v3r-pnj-11 | Total assets PNJ consolidated 2025 in USD | [Ảnh 1](source_images/PNJ-p3.png) |
| [ ] | NEG-v3r-pnj-12 | Total assets PNJ separate 2025 | [Ảnh 1](source_images/PNJ-p3.png) |
| [ ] | MULTI-HPG | Kiểm tra phương trình kế toán công ty mẹ Hòa Phát ngày 31/12/2025 | [Ảnh 1](source_images/HPG-p3.png), [Ảnh 2](source_images/HPG-p4.png) |
| [ ] | MULTI-SEM | Phương trình kế toán Samsung Electro-Mechanics hợp nhất ngày 31/12/2025 | [Ảnh 1](source_images/SEM-p7.png), [Ảnh 2](source_images/SEM-p8.png) |
| [ ] | NEGATIVE-AMOUNT | Operating expenses ACB consolidated 2022 | [Ảnh 1](source_images/ACB-p10.png) |
| [ ] | BLANK-NOT-ZERO | Chứng khoán kinh doanh PNJ hợp nhất đầu năm 2025 | [Ảnh 1](source_images/PNJ-p3.png) |
| [ ] | FORMAT-SEM | Total assets Samsung Electro-Mechanics consolidated December 31, 2025 | [Ảnh 1](source_images/SEM-p7.png) |

File/SHA256, trang, chỉ tiêu, kỳ, đơn vị, giá trị chép từ ảnh và Top-10 truy xuất: [HUMAN_AUDIT_CASES.json](HUMAN_AUDIT_CASES.json). Có thể mở lại ảnh toàn trang; các box SEM là vùng bảng để người kiểm định tự định vị ô, không phải tọa độ ô đã được chứng nhận.

Lỗi nhãn ACB net income: tọa độ tham chiếu cũ nằm phía trên dòng thực; xem [SOURCE_ANNOTATION_CORRECTIONS.json](SOURCE_ANNOTATION_CORRECTIONS.json). Điểm cũ được giữ riêng. Không coi điều chỉnh do agent là xác nhận độc lập.
