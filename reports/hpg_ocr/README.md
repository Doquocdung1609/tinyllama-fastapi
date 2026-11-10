# Kiểm định OCR tài chính HPG

Đối chiếu trực tiếp PDF báo cáo riêng công ty mẹ. SHA-256 nguồn
`4a92af827aaf1e73e017544d0ff20d0d14ae4d368bd9c90d5d6d60a28af8b447`.
[Gold đọc từ ảnh gốc](visual_gold.json) và [ma trận 54 ô](cell_comparison.csv) tách khỏi OCR.
Trang 3–6 dùng để phát triển. Trang 12, 13 và 24 là mẫu giữ lại trong cùng tài liệu.
Các ô khớp chính xác bao gồm dấu âm/ngoặc, chữ số, dấu phân cách và vị trí trong dòng/cột.
CER/WER chỉ đo nhãn dòng được lấy mẫu, gồm chữ thừa, nên có thể vượt 100%.

## A/B trên PDF gốc

Trong mỗi ô, thứ tự là **Tesseract cũ / Tesseract V2 / PaddleOCR PP-OCRv6 Small**.
Paddle dùng PP-OCRv6 Small det/rec CPU từ [tài liệu chính thức](https://www.paddleocr.ai/main/en/version3.x/pipeline_usage/OCR.html), trong môi trường Python riêng. Hai cấu hình ứng viên dùng chung bộ tái dựng hình học.

| Trang | Ô khớp / tổng mẫu | Dòng tìm được / tổng mẫu | Ô gán đúng kỳ và đơn vị | CER, WER |
|---|---:|---:|---:|---|
| 3 | 17 / 20 / 20 trên 20 | 10 / 10 / 10 trên 10 | 0 / 20 / 20 | 59,2%, 80,0% / 16,2%, 22,2% / 20,1%, 51,1% |
| 4 | 5 / 6 / 6 trên 6 | 3 / 3 / 3 trên 3 | 0 / 6 / 6 | 115,9%, 127,3% / 125,0%, 181,8% / 125,0%, 181,8% |
| 5 | 4 / 8 / 4 trên 8 | 2 / 2 / 1 trên 2 | 0 / 8 / 0 | 74,3%, 100,0% / 18,6%, 18,8% / 40,0%, 62,5% |
| 6 | 3 / 4 / 4 trên 4 | 2 / 2 / 2 trên 2 | 0 / 4 / 0 | 81,9%, 90,0% / 5,3%, 10,0% / 14,9%, 70,0% |
| 12 | 2 / 3 / 4 trên 4 | 2 / 2 / 2 trên 2 | 0 / 4 / 4 | 23,1%, 16,7% / 11,5%, 50,0% / 15,4%, 66,7% |
| 13 | 2 / 4 / 4 trên 8 | 2 / 2 / 2 trên 2 | 0 / 4 / 0 | 8,1%, 6,7% / 0,0%, 0,0% / 3,2%, 13,3% |
| 24 | 2 / 4 / 4 trên 4 | 1 / 2 / 2 trên 2 | 0 / 4 / 0 | 59,0%, 55,6% / 2,6%, 11,1% / 5,1%, 22,2% |
| **Tổng** | **35 / 49 / 46 trên 54** | **22 / 23 / 22 trên 23** | **0 / 50 / 30 trên 54** | |

Baseline không lưu kỳ/đơn vị ở cấp ô. Số 0 ở cột binding phản ánh thiếu
metadata. Kết quả ô và dòng được chấm độc lập với binding. Trên trang
giữ lại, V2 đúng 11/16 ô và Paddle đúng 12/16. Bốn dấu gạch dự phòng
trang 13 vẫn thiếu hộp đáng tin cậy. Nhãn dòng tổng trang 4 còn nhiễu.
Các tỷ lệ này áp dụng cho mẫu đã kiểm định, không phải toàn bộ 24 trang.

Ảnh gốc trang 3 xác nhận ba lỗi thay chữ số. Tài sản cố định hữu hình đầu
năm là **59.554.496.946** VND. Nguyên giá vô hình cuối năm là
**29.662.833.440** VND và giá trị còn lại là **6.102.000.606** VND.
Bất động sản đầu tư cuối năm là **79.481.693.590** VND. V2 đọc khớp cả ba
ô sai của baseline. Phương trình in trên báo cáo chỉ tạo cảnh báo khi mất
cân đối. Nó không tạo giá trị thay thế hoặc chứng nhận số.

Trang 5 cần hiệu chỉnh chiều đọc 90° để gắn đúng bốn cột quý và cả năm.
Trang 6 giữ ngoặc âm. Trang 3, dòng 221, cột đầu năm là ví dụ đầu ra
`GEOMETRIC_CANDIDATE` với kỳ `01/01/2025`, đơn vị `VND`, và trạng thái
`OCR_UNVERIFIED`. Ma trận lưu cả nhãn, giá trị thô và hộp nguồn cho từng engine.

Tesseract V2 mất 3,4–22,6 giây/trang trên bảy trang thử. Paddle mất
21,8–35,3 giây/trang và peak RSS khoảng 1,52 GiB. Các số thời gian là lần
chạy OCR riêng từng trang, không phải latency API. Baseline lấy từ
checkpoint lịch sử nên chưa có thời gian và peak RSS đối chứng tương đương.
Chưa đo peak RSS cùng phương pháp cho Tesseract V2. Paddle chỉ dùng để đối chiếu.

## Live và tái lập

- **PASS** API JSON strict UTF-8 trùng với checkpoint SHA-verified cho cả
  bảy trang. Hiện tượng mojibake được ghi nhận trong đường xuất PowerShell.
  Browser tải TXT BOM, giải mã strict UTF-8 và khớp từng ký tự với API.
- **PASS** Generation riêng lập chỉ mục lại 24 trang và 64 chunk trên PDF
  nguyên bản. BM25, Dense, Hybrid và FAITH-R đều trả kết quả thực. Khởi động
  lại giữ được generation và sổ xác minh. Mỗi chế độ trả 5 kết quả ở Top-5. FAITH-R vẫn chưa đưa dòng tổng tài sản lên Top-5 trong câu thử, do nhãn OCR dòng 270 sai. Chat dùng bản đối chiếu riêng của dòng này.
- **PASS** Chọn ô 59.554.496.946 trên trình duyệt làm sáng vùng trên trang 3.
  Desktop 1440 × 900 có ảnh trước/sau trang 3 và 5. Mobile 390 × 844 đọc
  trang 5 đúng chiều và không gây tràn ngang toàn trang.
- **PASS** Chat đọc tổng tài sản 98.670.778.691.605 VND trang 3 và nợ phải trả
  4.239.852.223.395 VND trang 4 sau đối chiếu ảnh gốc. Review cột đầu năm với
  kỳ cuối năm bị API từ chối HTTP 409. Từ câu trả lời về nợ, trình duyệt mở
  đúng trang 4 và highlight ô số. Giá trị/nhãn người duyệt được lưu trong
  audit riêng cùng dấu vết OCR, hash nguồn và tọa độ.
- **PARTIAL** Doanh thu, lợi nhuận, dòng tiền, tài sản cố định và bảng công
  ty con lần lượt dẫn trang 5, 5, 6, 3 và 13, ở mức trích đoạn nguồn. Việc thấy ô đúng trong
  benchmark không tự cấp quyền công bố số. Thông tin thiếu kỳ/phạm vi và
  các ô chưa đối chiếu tiếp tục bị chặn.
- **PASS** Apple Services FY2025 trả 109.158 triệu USD trang 32, BIDV
  chênh lệch điều chỉnh trả 1.114 triệu VND với nguồn trang 4 và 7, trên
  workspace gốc. Đây là đối chứng API cho luồng native.
- **BLOCKED** Chưa có kết quả kiểm định trên một PDF tài chính tiếng Việt
  dạng scan khác. Trang giữ lại của HPG chỉ đo được mức khái quát nội tài liệu.

Tạo generation riêng bằng `python -m scripts.fis_ocr_v2_reindex BASELINE TARGET DOCUMENT_ID`.
Chạy `scripts/run_financial_studio.ps1 -Mode Prebuilt -ApiPort 18111 -Workspace TARGET -RuntimeName ocr-v2-runtime`.
Để quay về bản cũ, mở workspace gốc ở cổng 18110. Chạy
`python -m scripts.fis_hpg_ocr_benchmark --reuse-candidate --compare-workspace TARGET`
khi các file A/B cục bộ đã có. Chạy `python -m scripts.fis_hpg_ocr_live` để
ghi log API và `node scripts/fis_hpg_ocr_browser.cjs` để kiểm tra trình
duyệt. Live harness ghi các bản đối chiếu vào workspace OCR thử nghiệm.
Log JSON, ảnh PNG, OCR thô và ảnh trang đầu vào nằm trong
`tmp/ocr-hpg-repair/` trên máy chạy.

Kiểm thử frontend có 36 test qua và build thành công. Bộ backend mục tiêu
có 110 test qua. Một test giả lập SEC không khả dụng thất bại trên cả
checkpoint 76749e4 và bản sửa trong môi trường đang có thư viện SEC thực.
