# Two-PDF before and after

Exact original queries are in [questions.json](questions.json). Full reply text, reported plans and citation fields are in [baseline](api-baseline.json) and [V7](api-v7.json). Status is scored against the question and source, independently of the API status.

The default BIDV runs used one selected PDF. Multi-PDF comparison used the new replay workspace and V3 HPG extraction checkpoints.

## C01

So sánh tổng tài sản của BIDV theo báo cáo riêng năm 2024 sau điều chỉnh và Hòa Phát theo báo cáo riêng cuối năm 2025. Quy đổi về tỷ đồng, tính chênh lệch và cho biết BIDV lớn hơn bao nhiêu lần.

**Before**

> Tôi đối chiếu từng PDF theo kỳ, đơn vị và phạm vi của chính tài liệu. Chỉ tính chênh lệch giữa các file khi xác nhận được các điều kiện so sánh.
>
> ### 20251023+-+BID+-+CBTT+Dieu+chinh+BCTC+2024+theo+ket+qua+KTNN.pdf
> Doanh nghiệp trong câu hỏi chưa khớp danh tính được xác nhận từ nội dung tài liệu.
>
> ### 20260130-hpg-bao-cao-tai-chinh-rieng-cong-ty-me-va-giai-trinh-q4-2025.pdf
> Doanh nghiệp trong câu hỏi chưa khớp danh tính được xác nhận từ nội dung tài liệu.

**After**

**Đối chiếu sơ bộ.** Các phép tính có dùng ô OCR ứng viên được đánh dấu trong bảng.

| Doanh nghiệp | Chỉ tiêu · báo cáo riêng | Kỳ | Giá trị nguồn | Tỷ đồng | Đối chiếu | Nguồn |
| --- | --- | --- | --- | --- | --- | --- |
| BIDV | TỔNG TÀI SẢN | 2024-12-31 | 2,709,397,390 triệu đồng | 2.709.397,39 | Đối chiếu lớp chữ PDF | [1] |
| HPG | Tổng tài sản | 2025-12-31 | 98.670.778.691.605 đồng | 98.670,7787 | Ứng viên OCR | [2] |

Quy đổi sang tỷ đồng: số gốc × hệ số đơn vị nguồn ÷ 1.000.000.000 (hệ số 1 đối với đồng, 1.000.000 đối với triệu đồng).

Chênh lệch: 2.709.397,39 − 98.670,7787 = **2.610.726,6113 tỷ đồng**. [1][2]

Quy mô lớn hơn **27,459 lần**, tính bằng giá trị lớn chia giá trị nhỏ. [1][2] Hai số thuộc hai doanh nghiệp, ở các ngày và ngành khác nhau.

## C02

So sánh quy mô vốn của BIDV và Hòa Phát. Phân biệt chỉ tiêu “Vốn và các quỹ” của BIDV với “Vốn chủ sở hữu” và “Vốn góp của chủ sở hữu” của Hòa Phát. Những chỉ tiêu nào không nên coi là đồng nhất?

**Before**

> Tôi đối chiếu từng PDF theo kỳ, đơn vị và phạm vi của chính tài liệu. Chỉ tính chênh lệch giữa các file khi xác nhận được các điều kiện so sánh.
>
> ### 20251023+-+BID+-+CBTT+Dieu+chinh+BCTC+2024+theo+ket+qua+KTNN.pdf
> Doanh nghiệp trong câu hỏi chưa khớp danh tính được xác nhận từ nội dung tài liệu.
>
> ### 20260130-hpg-bao-cao-tai-chinh-rieng-cong-ty-me-va-giai-trinh-q4-2025.pdf
> Doanh nghiệp trong câu hỏi chưa khớp danh tính được xác nhận từ nội dung tài liệu.

**After**

**Đối chiếu sơ bộ.** Các phép tính có dùng ô OCR ứng viên được đánh dấu trong bảng.

| Doanh nghiệp | Chỉ tiêu · báo cáo riêng | Kỳ | Giá trị nguồn | Tỷ đồng | Đối chiếu | Nguồn |
| --- | --- | --- | --- | --- | --- | --- |
| BIDV | Vốn và các quỹ | 2024-12-31 | 136,350,642 triệu đồng | 136.350,642 | Đối chiếu lớp chữ PDF | [1] |
| HPG | Tổng vốn chủ sở hữu | 2025-12-31 | 94.430.926.468.210 đồng | 94.430,9265 | Ứng viên OCR | [2] |
| HPG | Vốn góp của chủ sở hữu | 2025-12-31 | 76.754.658.550.000 đồng | 76.754,6586 | Ứng viên OCR | [3] |

Quy đổi sang tỷ đồng: số gốc × hệ số đơn vị nguồn ÷ 1.000.000.000 (hệ số 1 đối với đồng, 1.000.000 đối với triệu đồng).

“Vốn và các quỹ” và “Vốn chủ sở hữu” là các nhóm tổng hợp theo cách trình bày của từng báo cáo. “Vốn góp của chủ sở hữu” là một thành phần của vốn chủ sở hữu. Cần đọc các dòng cấu thành trước khi coi hai nhóm tổng hợp có cùng phạm vi.

## C03

Tính tỷ lệ nợ phải trả trên tổng tài sản của Hòa Phát và BIDV báo cáo riêng. Với BIDV, nếu không có dòng tổng nợ riêng, hãy suy ra từ phương trình kế toán và ghi rõ đó là giá trị tính toán. Có nên dùng hai tỷ lệ để khẳng định doanh nghiệp nào an toàn hơn không?

**Before**

> Tôi đối chiếu từng PDF theo kỳ, đơn vị và phạm vi của chính tài liệu. Chỉ tính chênh lệch giữa các file khi xác nhận được các điều kiện so sánh.
>
> ### 20251023+-+BID+-+CBTT+Dieu+chinh+BCTC+2024+theo+ket+qua+KTNN.pdf
> Doanh nghiệp trong câu hỏi chưa khớp danh tính được xác nhận từ nội dung tài liệu.
>
> ### 20260130-hpg-bao-cao-tai-chinh-rieng-cong-ty-me-va-giai-trinh-q4-2025.pdf
> Doanh nghiệp trong câu hỏi chưa khớp danh tính được xác nhận từ nội dung tài liệu.

**After**

**Đối chiếu sơ bộ.** Các phép tính có dùng ô OCR ứng viên được đánh dấu trong bảng.

| Doanh nghiệp | Chỉ tiêu · báo cáo riêng | Kỳ | Giá trị nguồn | Tỷ đồng | Đối chiếu | Nguồn |
| --- | --- | --- | --- | --- | --- | --- |
| BIDV | TỔNG TÀI SẢN | 2024-12-31 | 2,709,397,390 triệu đồng | 2.709.397,39 | Đối chiếu lớp chữ PDF | [1] |
| BIDV | Vốn và các quỹ | 2024-12-31 | 136,350,642 triệu đồng | 136.350,642 | Đối chiếu lớp chữ PDF | [2] |
| HPG | Tổng tài sản | 2025-12-31 | 98.670.778.691.605 đồng | 98.670,7787 | Ứng viên OCR | [3] |
| HPG | Nợ phải trả | 2025-12-31 | 4.239.852.223.395 đồng | 4.239,8522 | Người duyệt đã đối chiếu | [4] |
| HPG | Tổng vốn chủ sở hữu | 2025-12-31 | 94.430.926.468.210 đồng | 94.430,9265 | Ứng viên OCR | [5] |

Quy đổi sang tỷ đồng: số gốc × hệ số đơn vị nguồn ÷ 1.000.000.000 (hệ số 1 đối với đồng, 1.000.000 đối với triệu đồng).

Nợ phải trả BIDV (tính từ phương trình kế toán) = tổng tài sản − vốn và các quỹ = 2.573.046,748 tỷ đồng. [1][2]

**BIDV**: 2.573.046,748 ÷ 2.709.397,39 × 100 = **94,9675%**. [1][2]

**HPG**: 4.239,8522 ÷ 98.670,7787 × 100 = **4,297%**. [4][3]

Hai tỷ lệ không đủ để kết luận doanh nghiệp nào an toàn hơn. Cần xét cấu trúc nguồn vốn và chuẩn an toàn phù hợp với từng ngành.

## C04

So sánh lợi nhuận sau thuế năm 2024 sau điều chỉnh của BIDV riêng với lợi nhuận sau thuế quý IV/2025 của Hòa Phát riêng. Đổi về cùng đơn vị nhưng giải thích tại sao không thể gọi chênh lệch này là tăng trưởng.

**Before**

> Tôi đối chiếu từng PDF theo kỳ, đơn vị và phạm vi của chính tài liệu. Chỉ tính chênh lệch giữa các file khi xác nhận được các điều kiện so sánh.
>
> ### 20251023+-+BID+-+CBTT+Dieu+chinh+BCTC+2024+theo+ket+qua+KTNN.pdf
> Doanh nghiệp trong câu hỏi chưa khớp danh tính được xác nhận từ nội dung tài liệu.
>
> ### 20260130-hpg-bao-cao-tai-chinh-rieng-cong-ty-me-va-giai-trinh-q4-2025.pdf
> Doanh nghiệp trong câu hỏi chưa khớp danh tính được xác nhận từ nội dung tài liệu.

**After**

**Đối chiếu sơ bộ.** Các phép tính có dùng ô OCR ứng viên được đánh dấu trong bảng.

| Doanh nghiệp | Chỉ tiêu · báo cáo riêng | Kỳ | Giá trị nguồn | Tỷ đồng | Đối chiếu | Nguồn |
| --- | --- | --- | --- | --- | --- | --- |
| BIDV | Lợi nhuận sau thuế TNDN | Năm 2024 | 24,579,917 triệu đồng | 24.579,917 | Đối chiếu lớp chữ PDF | [1] |
| HPG | Lợi nhuận sau thuế | Quý IV/2025 | 5.597.856.806.673 đồng | 5.597,8568 | Ứng viên OCR | [2] |

Quy đổi sang tỷ đồng: số gốc × hệ số đơn vị nguồn ÷ 1.000.000.000 (hệ số 1 đối với đồng, 1.000.000 đối với triệu đồng).

Chênh lệch: 24.579,917 − 5.597,8568 = **18.982,0602 tỷ đồng**. [1][2]

Chênh lệch này so sánh hai doanh nghiệp và các kỳ được ghi trong bảng. Không thể diễn giải nó như tăng trưởng qua các năm.

## C05

Hãy chỉ ra những điểm khác biệt về phạm vi báo cáo, kỳ kế toán, đơn vị số liệu, loại báo cáo và phương pháp trích xuất dữ liệu giữa BIDV và Hòa Phát trước khi thực hiện bất kỳ phép so sánh nào.

**Before**

> Tôi đối chiếu từng PDF theo kỳ, đơn vị và phạm vi của chính tài liệu. Chỉ tính chênh lệch giữa các file khi xác nhận được các điều kiện so sánh.
>
> ### 20251023+-+BID+-+CBTT+Dieu+chinh+BCTC+2024+theo+ket+qua+KTNN.pdf
> Doanh nghiệp trong câu hỏi chưa khớp danh tính được xác nhận từ nội dung tài liệu.
>
> ### 20260130-hpg-bao-cao-tai-chinh-rieng-cong-ty-me-va-giai-trinh-q4-2025.pdf
> Doanh nghiệp trong câu hỏi chưa khớp danh tính được xác nhận từ nội dung tài liệu.

**After**

| PDF | Loại báo cáo | Phạm vi | Năm trong nguồn | Đơn vị | Trích xuất | Nguồn |
| --- | --- | --- | --- | --- | --- | --- |
| 20251023+-+BID+-+CBTT+Dieu+chinh+BCTC+2024+theo+ket+qua+KTNN.pdf | Bảng điều chỉnh báo cáo tài chính | riêng và hợp nhất | 2024 | triệu đồng | lớp chữ PDF, OCR | [1] [2] |
| 20260130-hpg-bao-cao-tai-chinh-rieng-cong-ty-me-va-giai-trinh-q4-2025.pdf | Báo cáo tài chính | riêng | 2025 | đồng | OCR | [3] |

## C06

Tôi chỉ chọn PDF BIDV. Hãy cho biết tổng tài sản của công ty mẹ Hòa Phát tại ngày 31/12/2025.

**Before**

> Tôi đối chiếu từng PDF theo kỳ, đơn vị và phạm vi của chính tài liệu. Chỉ tính chênh lệch giữa các file khi xác nhận được các điều kiện so sánh.
>
> ### 20251023+-+BID+-+CBTT+Dieu+chinh+BCTC+2024+theo+ket+qua+KTNN.pdf
> Doanh nghiệp trong câu hỏi chưa khớp danh tính được xác nhận từ nội dung tài liệu.
>
> ### 20260130-hpg-bao-cao-tai-chinh-rieng-cong-ty-me-va-giai-trinh-q4-2025.pdf
> Doanh nghiệp trong câu hỏi chưa khớp danh tính được xác nhận từ nội dung tài liệu.

**After**

Chưa tìm thấy nguồn cho HPG trong các PDF đang chọn. Hãy thêm tài liệu của doanh nghiệp được hỏi hoặc đổi nguồn trong bộ chọn PDF.

## C07

Theo PDF điều chỉnh BIDV tôi đang chọn, lợi nhuận sau thuế quý IV/2025 của BIDV là bao nhiêu?

**Before**

> PDF có lớp chữ gốc, nhưng bộ phân tích chưa hỗ trợ chỉ tiêu hoặc cấu trúc ô này; đây không phải lỗi OCR. [1][2]

**After**

PDF đang chọn có bảng điều chỉnh cho năm 2024. Tôi chưa thấy cột theo quý 2025 trong các bảng này.

## C08

Có đúng lợi nhuận sau thuế hợp nhất BIDV 2024 trình bày lại là 25.212.049 triệu đồng không? Hãy xác nhận.

**Before**

> PDF có lớp chữ gốc, nhưng bộ phân tích chưa hỗ trợ chỉ tiêu hoặc cấu trúc ô này; đây không phải lỗi OCR. [1][2]

**After**

**Không**. Báo cáo ghi **25.677.118 triệu đồng** cho dòng “Lợi nhuận sau thuế TNDN”. [1]

Số 25.212.049 thuộc dòng “Lợi nhuận thuần của cổ đông Ngân hàng”. [2]

| Chỉ tiêu | Phạm vi | Kỳ | Cột nguồn | Giá trị | Nguồn |
| --- | --- | --- | --- | --- | --- |
| Lợi nhuận sau thuế TNDN | Hợp nhất | 2024 | Trình bày lại | 25.677.118 triệu đồng | [1] |
