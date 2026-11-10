# FAITH-R V6 · kiểm kê và đối chiếu liên trang

Đối chứng là checkpoint `548f85b77b5892426325fc34d94fef0fefc0f3f3`.
[Hai câu hỏi nguyên văn và ca vốn góp](queries.json) được chạy qua
HTTP trên cùng PDF HPG SHA-256
`4a92af827aaf1e73e017544d0ff20d0d14ae4d368bd9c90d5d6d60a28af8b447`.
[Bản ghi trước/sau](before-after.json) giữ phản hồi thật, Top-5 của
đối chứng, phạm vi, kế hoạch, các ô tham gia từng phép đối chiếu và
tọa độ. Các nhãn hình ảnh nằm riêng trong [visual-gold.json](visual-gold.json).

## Nguyên nhân và kết quả

| Kiểm thử | Đối chứng V5 | V6 |
|---|---|---|
| Kiểm kê | Ba trích dẫn PDF 13, 4, 6, không có dòng kiểm kê | Đủ 24/24 dòng, mỗi trang có trạng thái và citation, sau bảng có ô vốn góp |
| Sáu nhóm | Một thông báo thiếu xác minh và nguồn trang 5 | Sáu nhóm có kết quả riêng, 5 PASS sơ bộ và 1 PARTIAL |
| Vốn góp 01/01/2024 | Nguồn trang 4, không có giá trị | 58.147.857.000.000 đồng, đúng hàng ngày và cột vốn góp tại PDF 20, trang in 19, trạng thái ứng viên OCR |
| Tổng vốn và vốn góp | Không có quan hệ cha/con riêng trong câu hỏi | Cuối 2025: tổng vốn 94.430.926.468.210 đồng và vốn góp 76.754.658.550.000 đồng, hai ô riêng |

Đối chứng dùng một kế hoạch ngữ nghĩa và kết luận dựa trên các ứng viên
retrieval. Top-5 là danh sách ứng viên, không chứng minh từng trang đã
được đọc để kiểm kê hoặc từng yêu cầu đã được xử lý. Bản đối chứng không
ghi trace riêng cho từng trang đã duyệt. Ở V6, một lượt tuần tự đi qua
mọi checkpoint của PDF. Trang lỗi vẫn có dòng riêng. [Bản đồ 24 trang](page-map.json)
ghi loại trang, dữ liệu tiêu biểu, hướng OCR, chất lượng, vùng OCR yếu
và citation. Số trang in chỉ lấy từ ký tự nhận diện đủ chắc ở chân trang.
Có 3 trang nhận diện được folio theo quy tắc này, các trang khác để trống.

Trang 20 đã có chữ và tọa độ đúng trong OCR V3, gồm hướng đọc hiệu chỉnh 90°.
Bộ tái dựng cũ bỏ cột vốn góp do thiếu neo đơn vị phía trái và xếp ngày
vào sai nhóm dòng. V6 gắn trực tiếp từ tiêu đề cột, ngày trên hàng, độ lệch
của bảng xoay và vùng chữ số. Trang 18 có hai cột con dưới mỗi ngày.
Bộ tái dựng cũ bỏ cột phải nộp và còn giữ phải thu. V6 dùng đồng thời
neo ngày và tiêu đề con “Số phải nộp”, nên không phát sinh chênh lệch thuế
giả. Các sửa đổi này đọc checkpoint, không chạy lại OCR HPG hoặc tạo fact
đã được người dùng xác nhận.

## Sáu nhóm đối chiếu

| Nhóm | Kết quả | Nguồn PDF |
|---|---|---|
| Phương trình kế toán | Khớp sơ bộ tại 31/12/2025 | 3, 4 |
| Tiền và tương đương tiền | Cả ba nguồn cùng đọc 481.464.857.088 đồng | 2, 7, 12 |
| Doanh thu và giá vốn | Giá vốn, doanh thu dịch vụ và lợi nhuận gộp đối chiếu được. Giảm trừ in dấu gạch nên phép trừ này bị chặn | 5, 22 |
| Vốn góp và cổ phiếu | Khớp sơ bộ vốn cuối kỳ với số cổ phiếu nhân mệnh giá. Có riêng ô vốn đầu 2024 | 20, 21, chính sách tiền tệ trang 9 |
| Tài sản, thuế và phải trả khác | Khớp sơ bộ năm cặp ô cuối kỳ. Phải trả khác là chỉ tiêu con | 3–4, 15–19 |
| Giải trình lợi nhuận | Công ty nêu lợi nhuận công ty con chuyển về tăng. Tách số nguyên đồng khỏi mức tỷ đồng trong văn bản | 5, 24 |

Các phép dùng ứng viên đều mang `CANDIDATE_RECONCILIATION`. Một phép
chỉ có thể mang `VERIFIED_CALCULATION` khi tất cả toán hạng đã được đối
chiếu theo sổ hiện hành, đúng kỳ, phạm vi và đơn vị. Dấu gạch không biến
thành số 0. Mỗi phép đối chiếu ghi danh sách citation của toán hạng.
Không thay đổi bản ghi người dùng đã xác nhận.

## Đánh giá

- **Page coverage:** 24/24 HPG, 8/8 trong câu kiểm kê BIDV bổ sung
  dùng làm ca chuyển tài liệu. Các trang chưa phân loại trên BIDV vẫn có
  dòng và citation. Đây là kiểm tra độ phủ, không phải xác nhận độ đúng
  của mọi tiêu đề BIDV.
- **Subtask completion:** 6/6 có kết quả và lý do, gồm 5 mục PASS về
  bằng chứng và 1 PARTIAL. PASS ở đây không xác minh các số OCR.
- **Exact Row/Cell:** câu vốn góp của V5 không có ô đích ở Top-1 hay
  Top-5. Bộ định vị V6 chọn đúng ô ở lần chọn đầu tiên. Trên 5 ô
  [đối chiếu ảnh](source-matrix.csv), lần chọn đầu của V6 khớp 5/5 hàng,
  cột, kỳ, đơn vị và giá trị. Không suy rộng chỉ số này thành benchmark
  ranking Top-K của Search. Hộp ứng dụng nằm trong vùng ảnh đánh dấu
  thủ công ở cả 5 ô. Các vùng ảnh thủ công là gần đúng nên IoU được
  ghi riêng.
- **Chất lượng OCR và tổng hợp:** đọc lại 54 ô hồi quy từ checkpoint
  HPG. V6 sửa liên kết nguồn, không huấn luyện hoặc thay engine OCR.
  Các giới hạn SHS và nhãn nhiễu của V3 vẫn còn. Câu giải trình được đọc
  từ đoạn công bố, không dùng phép tính để suy ra nguyên nhân.
- **Thời gian tại máy thử:** ba ca V5 lần lượt mất 2,41 / 2,82 / 1,40
  giây. Lượt V6 ghi 0,34 / 0,32 / 0,31 giây. Đây là lượt đo cục bộ,
  không phải benchmark tải. Peak working set API V6 khoảng 253 MiB
  trong lượt đo, gồm runtime sẵn có. Đối chứng chỉ có RAM khả dụng của
  hệ thống, không đủ dữ liệu để so sánh peak RSS của hai tiến trình.
- **Phạm vi còn lại:** bộ điều phối nhận diện danh mục tác vụ đã hỗ trợ
  và giữ từng mục đánh số độc lập. Bảng có cấu trúc khác hoặc mục chưa
  nhận diện có thể trả PARTIAL/BLOCKED. V5 tiếp tục xử lý hội thoại thông
  thường, so sánh nhiều PDF và nhiều filing SEC.

## Tái lập

```powershell
python -m scripts.fis_chat_v6_probe
node scripts/fis_chat_v6_browser.cjs
node scripts/fis_chat_v5_browser.cjs
node scripts/fis_ocr_v3_browser.cjs
```

Cổng 18112 dùng workspace HPG V3 sẵn có. Cổng 18113 dùng đối chứng
Apple/BIDV và SEC PG từ hai generation. Log và ảnh ở `tmp/chat-v6/`.
Tiến trình UI lấy số trang/mục thực từ API, phân biệt trang đã kiểm tra
với trang đọc được. Rollback bằng triển khai checkpoint V5 trên cùng
workspace. Không có migration OCR, PDF, index hay sổ review.
