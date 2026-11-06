# Kiểm định FAITH-R Chat V5

Checkpoint đối chứng `a424f2a4ab2629dfb4cde72bf7c6b726a11b06cf`.
Toàn bộ [10 câu trả lời trước/sau](responses.json) lấy từ API chạy thật.
Cả hai lượt sử dụng cùng PDF HPG, generation OCR V3 và bản xác nhận nợ
phải trả đã có từ trước. Bộ kiểm tra không gửi giá trị gold vào Chat hoặc
vào API review. Các ca ghi hội thoại kiểm thử riêng.

## Nguyên nhân và bản sửa

Kho tài liệu mở PDF qua `first-chunk` để hiển thị Viewer. Trước đây
`Studio.selected` đồng thời đi vào Chat. Chat dùng nó để khởi tạo
`inspected`, dựng tiêu đề “Đoạn đang xem” và gửi `evidence_context` ở
lượt đầu, dù người dùng chỉ mở tài liệu. Tiêu đề tiếp tục đọc `selected`
trong khi người dùng đã mở citation mới. V5 tách bộ tài liệu, nguồn người
dùng chủ động chọn cho lượt tiếp theo và citation đang xem. Chỉ hành
động “Hỏi về đoạn này” hoặc chuyển ô đang chọn từ Viewer mới gắn focus
có chủ đích. Backend lấy lại trang/hàng/ô theo định danh từ workspace.
Focus một lượt được dọn sau khi gửi thành công. Citation được khôi phục
theo đúng phiên, không lấy từ Viewer của tài liệu khác.

Hàm trả lời số OCR đã xác nhận tạo biến `kind` là cả dictionary nhãn kỳ
rồi nội suy nguyên biến vào câu. V5 lấy một nhãn theo `period_type`, dùng
đơn vị tiếng Việt và nêu phạm vi, trang và nguồn xác nhận. Lịch sử cũ
được định dạng lại khi đọc để giữ nguyên bản ghi đã lưu.

Giá trị OCR ứng viên phải khớp hàng, cột, kỳ, đơn vị, phạm vi, tọa độ
và số được phân tích lại từ chuỗi OCR. Ô có bất đồng chưa giải quyết
hoặc cảnh báo số học cùng kỳ bị chặn ở phần trả lời số. Ứng viên xuất
hiện trong câu giải thích và trích dẫn nhưng để trống `values`.
Chỉ ô đã được người dùng đối chiếu đi vào phép tính xác minh. Ca tỷ lệ
nợ trên tài sản chạy thật thiếu ô tài sản đã xác nhận, nên không tính.
Phép tính có đủ hai ô được kiểm tra bằng fixture với Decimal, không
thêm dữ kiện vào sổ review HPG.

## Ma trận nghiệm thu 10 câu

| Ca API | Correctness | Completeness | Citation | Numeric safety |
|---|---|---|---|---|
| Nợ phải trả | PASS, đúng 4.239.852.223.395 đồng | PASS, ngày và báo cáo riêng | PASS, ô trang 4 | PASS, fact đã có |
| Tổng tài sản và trạng thái | PASS, đúng chuỗi OCR | PASS, nêu chưa được duyệt | PASS, ô trang 3 | PASS, chỉ ứng viên |
| Doanh thu hai kỳ | PASS, phân biệt quý và năm | PASS, hai giá trị | PASS, hai ô trang 5 | PASS, chỉ ứng viên |
| Dòng tiền âm | PASS, giữ dấu ngoặc | PASS, kỳ cả năm | PASS, ô trang 6 | PASS, chỉ ứng viên |
| Tiền gửi, đọc lại | PASS, chỉ rõ chữ số đổi 1 → 7 | PASS, nêu hai quan sát | PASS, cùng ô trang 12 | PASS, hai bản đọc OCR |
| Dấu gạch dự phòng | PASS, không mặc định bằng 0 | PASS, phân biệt ký hiệu, ô trống và lỗi OCR | PASS, ô dự phòng trang 13 | PASS, không suy ra số |
| Giải thích dòng tiền | PASS, nghĩa của chỉ tiêu và dấu âm | PASS | PASS, dòng trang 6 | PASS, không yêu cầu số |
| Hỏi vị trí tổng tài sản | PASS, chỉ ra vị trí | PASS, ngày và phạm vi | PASS, ô trang 3 | PASS, không yêu cầu số |
| Hỏi đã kiểm duyệt chưa | PASS, xác nhận rõ | PASS, nguồn và ngày | PASS, ô trang 4 | PASS, fact đã có |
| Tỷ lệ nợ trên tài sản | PASS, nêu thiếu ô xác nhận | PARTIAL, chưa tính được vì thiếu ô | PASS, dẫn các ô cần dùng | PASS, không tính từ OCR |

Kiểm tra Chromium qua React ghi request thật ở các lượt mở Kho,
quay lại từ Viewer, đổi nguồn, tải lại và mở lại phiên. Chỉ lượt nhấn
“Hỏi về đoạn này” mang `evidence_context`. Trình duyệt mở đúng ô
trang 3, 4, 5, 6, 12, 13, gồm hai cột riêng trang 5. Lượt hỏi tiếp
về khác biệt OCR giữ đúng ô tiền gửi mà không lấy lại số từ câu trả lời
trước. Ảnh `chat-100.png` và `chat-125.png` là Chromium tại tỷ lệ
hiển thị tương ứng. `source-125.png` dùng mức 125% của PDF Viewer.

## Chạy lại và rollback

```powershell
python -m scripts.fis_chat_v5_probe
node scripts/fis_chat_v5_browser.cjs
$env:STUDIO_BROWSER_URL='http://127.0.0.1:18113'
$env:STUDIO_BROWSER_OUTPUT='tmp/chat-v5/controls'
$env:STUDIO_BROWSER_NATIVE_CONTROLS='1'
node scripts/fis_v4_browser_checks.cjs
```

Bản HPG dùng cổng 18112 và bản đối chứng Apple, BIDV, SEC dùng 18113.
Đối chứng SEC cần một PG 2026-03-31 trong thư viện sản phẩm cùng
PG 2026-09-30 của chỉ mục cơ sở. Log và ảnh nằm trong
`tmp/chat-v5/`. Rollback bằng cách triển khai lại mã tại checkpoint
trước V5 với cùng workspace. V5 không tạo migration cho OCR, PDF
hoặc sổ review. Cách giải thích OCR hiện bao phủ các chỉ tiêu có
liên kết hàng/cột đủ rõ và những loại câu hỏi trong ma trận.

## Đối chứng nhiều nguồn

- Apple Services FY2025 trả 109.158 triệu USD, nguồn trang 32. BIDV
  trả chênh lệch điều chỉnh 1.114 triệu đồng, nguồn trang 4 và 7.
  Cả hai mở được ô có highlight trong Chromium.
- Câu tìm bảng cân đối trên hai PDF trả nguồn từ cả Apple và BIDV.
  Bộ hai PDF còn nguyên sau khi tải lại trang, và mở được citation.
- So sánh doanh thu PG ba tháng kết thúc 31/03/2026 và 30/09/2026
  trả hai trích dẫn từ hai generation. Cả hai source reference mở được
  ô SEC xác thực. Hai accession là `0000080424-26-000060` và
  `0000080424-26-000256`. Fixture đối chứng sao chép riêng một filing
  sản phẩm đã có, thay đường dẫn trong bản sao và giữ nguyên hash.
- Bộ chọn hai PDF hoạt động ở chiều rộng 390 px.
