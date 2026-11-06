# Kiểm định OCR V3 cho báo cáo tài chính tiếng Việt

## Dữ liệu và phương pháp

HPG dùng đúng PDF SHA-256 `4a92af827aaf1e73e017544d0ff20d0d14ae4d368bd9c90d5d6d60a28af8b447`.
Tesseract baseline, V2, Paddle và [gold V2](../hpg_ocr/visual_gold.json) được giữ nguyên.
Các trang HPG 12–13 là mẫu sửa lỗi V3. Các trang HPG còn lại dùng kiểm tra hồi quy.
Báo cáo kiểm toán SHS dạng scan là một tài liệu độc lập. [Gold SHS](shs_visual_gold.json)
được chép từ ảnh hai trang PDF vật lý 12 và 13 trước khi chạy OCR lên SHS.
Bộ chấm không truy cập sổ review và không gửi giá trị vào API review.

CER và WER là khoảng cách Levenshtein của nhãn dòng OCR nguyên văn so với
nhãn gốc, chia cho số ký tự hoặc từ. Chữ thừa tính là lỗi, nên tỷ lệ có thể
vượt 100%. Một ô chỉ khớp nếu đúng chuỗi, dấu âm, dấu phân cách và cột
trên hàng mục tiêu. Mọi ô bỏ sót vẫn tính vào tổng mẫu.
[Ma trận từng ô](cell_comparison.csv) ghi kết quả trước/sau và tọa độ V3.

## Kết quả OCR

| Trang PDF | Khớp V2 | Khớp V3 | Kỳ/đơn vị V3 | CER/WER V3 |
|---|---:|---:|---:|---:|
| HPG 3 | 20/20 | 20/20 | 20/20 | 16,2% / 22,2% |
| HPG 4 | 6/6 | 6/6 | 6/6 | 125,0% / 181,8% |
| HPG 5 | 8/8 | 8/8 | 8/8 | 18,6% / 18,8% |
| HPG 6 | 4/4 | 4/4 | 4/4 | 5,3% / 10,0% |
| HPG 12 | 3/4 | 4/4 | 4/4 | 11,5% / 50,0% |
| HPG 13 | 4/8 | 8/8 | 8/8 | 0,0% / 0,0% |
| HPG 24 | 4/4 | 4/4 | 4/4 | 2,6% / 11,1% |
| **HPG tổng** | **49/54** | **54/54** | **54/54** | |
| SHS 12 | 6/8 | 6/8 | 7/8 | 13,8% / 33,3% |
| SHS 13 | 4/6 | 4/6 | 5/6 | 13,3% / 28,6% |
| **SHS tổng** | **10/14** | **10/14** | **12/14** | |

HPG tìm đủ 54/54 ô và 23/23 dòng mẫu. V3 đọc được 4/4 dấu gạch dự
phòng được chấm, gồm những dấu từng bị mất khi chuyển sang V2.
V3 đo riêng vùng ảnh gắn với cột và giữ hộp tọa độ dấu in. Dấu gạch
không được chuyển thành số 0. Các trạng thái ô trống, không đọc được và
không xác định cấu trúc được lưu riêng.

SHS tìm được 12/14 ô và 7/7 dòng. Độ chính xác trên ô tìm thấy là
10/12, độ phủ là 12/14, và độ chính xác toàn mẫu là 10/14.
Hai dấu gạch SHS vẫn bỏ sót. Hai ô số còn sai dù tìm thấy.
Các dấu gạch này nằm ngoài cột dự phòng đã được kiểm tra hình học
trên HPG. Kết quả SHS chưa cho thấy cải thiện khi chuyển sang V3.

Ở trang HPG 12, OCR toàn trang đọc `46.014.571.676`. Hai lần Tesseract
đọc crop ở 330 DPI và 420 DPI cùng cho `46.074.571.676`.
Chạy thật PaddleOCR PP-OCRv6 Small trên crop cũng trả cùng chuỗi.
Giá trị cũ vẫn nằm trong bản ghi và trạng thái mới là ứng viên OCR
đã đọc đối chiếu, chờ xác nhận ảnh nếu cần sử dụng trong Chat.
Quy tắc cần ít nhất hai kết quả crop hợp lệ nhất trí. Mâu thuẫn chưa
giải quyết giữ nguyên bản đọc ban đầu và gắn cảnh báo. Công thức kế toán
in trên giấy chỉ tạo cảnh báo và ưu tiên đọc lại.

Trên hai trang SHS, Tesseract V2 mất 4,4–7,9 giây/trang, V3 mất
7,8–8,1 giây/trang. Peak working set của tiến trình Python đo SHS
khoảng 180 MiB, không gồm subprocess Tesseract. HPG trang 13 mất
2,9 giây cho lượt đo riêng. Trang 12 với Paddle crop CPU mất 29 giây
tính cả khởi tạo mô hình. Chưa đo peak RSS cả cây tiến trình ở lượt crop
này. Bản Paddle toàn trang V2 đã đo khoảng 1,52 GiB.

## Luồng sản phẩm

- HPG được lập chỉ mục trong generation riêng với 24 trang và 64 chunk.
  Search kết hợp ứng viên Hybrid RRF với hàng OCR có provenance.
  Tổng tài sản được nhận dạng từ tiêu đề bảng và quan hệ mã mục in
  trên dòng, không dựa trên tên HPG hoặc số gold.
- Search có thể dẫn tới một ô ứng viên đã định vị. Chat mở được ô
  OCR đúng vị trí ngay cả khi chưa đủ điều kiện công bố giá trị.
  Q4 và FY có ngày bắt đầu khác nhau và giữ citation riêng.
- Giao diện Review hiển thị OCR ban đầu, ứng viên sau đọc lại, Paddle
  khi có, và giá trị người duyệt. Chọn ô cập nhật kỳ, đơn vị và chỉ tiêu.
  Đối chiếu sai chỉ tiêu hoặc kỳ bị chặn cả ở UI lẫn API. Desktop
  điều chỉnh được độ rộng khung, mobile thử ở 390 px.
- Trạng thái máy đọc và máy đọc đối chiếu không được dùng làm fact.
  Chỉ fact người duyệt gắn với PDF, checkpoint, hàng, cột, kỳ, đơn vị và
  phạm vi mới đi vào đường trả lời số từ OCR. Unit test xác nhận Chat
  từ chối câu hỏi hai kỳ nếu chỉ một kỳ có review.
- Test SEC không khả dụng đã được sửa tại đường chọn chỉ mục. Chat
  dùng chỉ mục đã phân giải hoặc trả nguồn không khả dụng, thay vì rơi
  sang bằng chứng từ cấu hình SEC thật khi test đang giả lập nguồn lỗi.

## Chạy lại

```powershell
python -m scripts.fis_ocr_v2_reindex BASELINE TARGET DOCUMENT_ID --adaptive
.\scripts\run_financial_studio.ps1 -Mode Prebuilt -ApiPort 18112 -Workspace TARGET -RuntimeName ocr-v3-runtime
python -m scripts.fis_ocr_v3_evaluate SHS_PDF TARGET
python -m scripts.fis_ocr_v3_live
node scripts/fis_ocr_v3_browser.cjs
```

Tesseract cần bộ ngôn ngữ `vie+eng`. Có thể chỉ định Python Paddle
đã cài sẵn qua `STUDIO_OCR_PADDLE_PYTHON` trước lúc lập chỉ mục để
chạy thêm crop CPU trên các vùng bất đồng. Khi bỏ cấu hình này, chỉ
Tesseract và kiểm tra hình ảnh nhẹ chạy. Mỗi trang có tối đa sáu
vùng đọc lại. Live harness không gọi API review. Ảnh và log cục bộ
nằm tại `tmp/ocr-v3/`. Workspace gốc và V2 vẫn có thể mở riêng.

## Truy xuất và nghiệm thu trình duyệt

[Ma trận truy xuất](retrieval_summary.csv) dùng 9 câu có hàng và cột
mục tiêu. Exact Target@1 và @5 cùng tăng từ 7/9 lên 9/9. Exact Cell@1
và @5 cùng tăng từ 0/9 lên 9/9. Một ô chỉ được tính nếu hit chứa định
danh ô và hộp đúng, không chỉ mở đúng trang. Các giá trị gold chỉ được
dùng để chấm. Chúng không tham gia xây chỉ mục hoặc xếp hạng.

- **PASS, chưa có review:** 11 ca Chat HPG giữ nguồn nhưng trả 0 giá
  trị đã xác minh. Các nguồn trỏ đến ô tương ứng, kể cả hai ô Q4/FY
  riêng trong câu hỏi hai kỳ.
- **PASS, có review từ người dùng:** Trước khi đối chiếu, câu hỏi nợ
  phải trả ngày 31/12/2025 chỉ có nguồn OCR. Sau khi người dùng lưu từ
  UI, Chat trả 4.239.852.223.395 VND và citation trỏ tới hộp ô trang 4.
  Bộ kiểm thử đọc sổ review và kiểm tra lại kết quả. Bộ kiểm thử không
  tạo bản review. OCR thô và review nằm ở các lớp dữ liệu riêng.
- **PASS, kiểm soát native:** Chromium chạy với workspace đối chứng
  được lập lại từ hai PDF gốc, dùng mã V3. Apple Services FY2025 trả
  109.158 triệu USD, trang 32. BIDV trả chênh lệch điều chỉnh 1.114 triệu
  VND với hai nguồn trang 4 và 7. Browser mở nguồn và tô sáng.
- **PARTIAL:** Doanh thu, lợi nhuận và dòng tiền HPG đã dẫn đúng từng
  ô, nhưng chưa có người duyệt các giá trị này trong lượt live.
  Bằng chứng về ranh giới năm kế toán là điều kiện riêng khi lưu
  review các kỳ Q4/FY. Một tiêu đề năm không đủ xác minh ngày bắt đầu.
- **PARTIAL:** SHS cho thấy chất lượng OCR tổng quát vẫn cần cải thiện.
  Kết quả HPG 54/54 chỉ áp dụng cho mẫu hồi quy đã công bố.

Các bằng chứng cục bộ gồm `evaluation-final-code.json`, `live.json`,
`human-before-after.json`, `browser.json`, `native-browser.json`
và ảnh chụp màn hình trong `tmp/ocr-v3/`.
