# 30 lượt hội thoại tự nhiên trên Apple FY2025

Đối chiếu trên NASDAQ_AAPL_2025.pdf. Cả hai lượt chạy gọi API cục bộ với năm phiên riêng. Các lượt trong mỗi kịch bản giữ chung phiên.

Trước sửa có ba HTTP 409 tại 1.5, 2.4 và 5.5. Sau sửa có 30 HTTP 200, trong đó 4.5 và 4.6 là từ chối có căn cứ. HTTP 200 được ghi riêng với kết quả chấm nội dung.

Chấm thủ công theo thứ tự đúng trọng tâm, đầy đủ, chính xác, nguồn, tự nhiên và ngữ cảnh. Mỗi tiêu chí tối đa hai điểm. PASS yêu cầu cả năm tiêu chí đạt hai điểm.

| Kịch bản | PASS | PARTIAL | Điểm |
| --- | ---: | ---: | ---: |
| 1. Cơ cấu doanh thu | 6 | 0 | 60/60 |
| 2. Greater China | 6 | 0 | 60/60 |
| 3. Hai phép so sánh biên | 6 | 0 | 60/60 |
| 4. Phản biện và thiếu nguồn | 6 | 0 | 60/60 |
| 5. Tóm tắt và diễn giải | 6 | 0 | 60/60 |
| Tổng | 30 | 0 | 300/300 |

Kiểm tra React riêng cho kịch bản 1 đã mở hai citation của lượt 6 trên trang PDF 32 và xác nhận hai vùng highlight khác nhau.

Đây là bộ hồi quy do người dùng cung cấp và đã được dùng để phát triển, nên điểm không đo khả năng khái quát trên câu hỏi mới.

## Bản ghi sau sửa

### 1.1 · PASS · 2/2/2/2/2

Apple năm 2025 kiếm tiền chủ yếu từ bán sản phẩm hay dịch vụ?

Sản phẩm mang về nhiều doanh thu hơn. FY2025, sản phẩm mang về 307.003 triệu USD [1], còn dịch vụ mang về 109.158 triệu USD [2].

HTTP trước và sau sửa 200 → 200.

- [1] Trang PDF 32 · Products 2025 · `cellv2_f0fb89e95e40fd972cb3cb8b72d7`
- [2] Trang PDF 32 · Services 2025 · `cellv2_9f570609f2c663fbe4508accfcdd`

### 1.2 · PASS · 2/2/2/2/2

Vậy cứ 100 đô doanh thu của Apple thì có khoảng bao nhiêu đô từ dịch vụ?

Trong mỗi 100 USD doanh thu năm tài chính 2025, khoảng 26,23 USD đến từ dịch vụ. [1][2] Tôi lấy doanh thu dịch vụ 109.158 triệu USD [1] chia tổng doanh thu 416.161 triệu USD [2], rồi nhân 100.

HTTP trước và sau sửa 200 → 200.

- [1] Trang PDF 32 · Services 2025 · `cellv2_9f570609f2c663fbe4508accfcdd`
- [2] Trang PDF 32 · Total net sales 2025 · `cellv2_cc16f54065bce239f5e0fad95209`

### 1.3 · PASS · 2/2/2/2/2

Thế năm trước thì sao?

Trong mỗi 100 USD doanh thu năm tài chính 2024, khoảng 24,59 USD đến từ dịch vụ. [1][2] Tôi lấy doanh thu dịch vụ 96.169 triệu USD [1] chia tổng doanh thu 391.035 triệu USD [2], rồi nhân 100.

HTTP trước và sau sửa 200 → 200.

- [1] Trang PDF 32 · Services 2024 · `cellv2_9aef27e2c60777264a1decc9e41e`
- [2] Trang PDF 32 · Total net sales 2024 · `cellv2_7f1fcea611bce77e0db246ae826f`

### 1.4 · PASS · 2/2/2/2/2

Như vậy mảng dịch vụ đang quan trọng hơn đúng không?

Tỷ trọng dịch vụ tăng: từ 24,59% năm tài chính 2024 đến 26,23% năm tài chính 2025, chênh 1,64 điểm phần trăm sau khi làm tròn. [1][2][3][4] Điều này cho biết dịch vụ đóng góp nhiều hay ít hơn vào doanh thu, chưa đủ để kết luận doanh nghiệp phụ thuộc vào dịch vụ.

HTTP trước và sau sửa 200 → 200.

- [1] Trang PDF 32 · Services 2024 · `cellv2_9aef27e2c60777264a1decc9e41e`
- [2] Trang PDF 32 · Total net sales 2024 · `cellv2_7f1fcea611bce77e0db246ae826f`
- [3] Trang PDF 32 · Services 2025 · `cellv2_9f570609f2c663fbe4508accfcdd`
- [4] Trang PDF 32 · Total net sales 2025 · `cellv2_cc16f54065bce239f5e0fad95209`

### 1.5 · PASS · 2/2/2/2/2

Giải thích đơn giản hơn được không, tôi không rành tài chính.

Nói dễ hiểu, cứ thu 100 đô thì năm trước có khoảng 24,59 đô từ dịch vụ, còn năm sau là 26,23 đô. [1][2][3][4]

HTTP trước và sau sửa 409 → 200.

- [1] Trang PDF 32 · Services 2024 · `cellv2_9aef27e2c60777264a1decc9e41e`
- [2] Trang PDF 32 · Total net sales 2024 · `cellv2_7f1fcea611bce77e0db246ae826f`
- [3] Trang PDF 32 · Services 2025 · `cellv2_9f570609f2c663fbe4508accfcdd`
- [4] Trang PDF 32 · Total net sales 2025 · `cellv2_cc16f54065bce239f5e0fad95209`

### 1.6 · PASS · 2/2/2/2/2

Tôi muốn xem chính xác hai con số bạn dùng để tính ở câu trước.

Đây là hai số dùng để tính tỷ trọng mới nhất: doanh thu dịch vụ 109.158 triệu USD [1] và tổng doanh thu 416.161 triệu USD [2]. Chia số thứ nhất cho số thứ hai rồi nhân 100. Để so với FY2024, tôi dùng 96.169 triệu USD [3] chia 391.035 triệu USD [4].

HTTP trước và sau sửa 200 → 200.

- [1] Trang PDF 32 · Services 2025 · `cellv2_9f570609f2c663fbe4508accfcdd`
- [2] Trang PDF 32 · Total net sales 2025 · `cellv2_cc16f54065bce239f5e0fad95209`
- [3] Trang PDF 32 · Services 2024 · `cellv2_9aef27e2c60777264a1decc9e41e`
- [4] Trang PDF 32 · Total net sales 2024 · `cellv2_7f1fcea611bce77e0db246ae826f`

### 2.1 · PASS · 2/2/2/2/2

Trong năm 2025, Apple có khu vực kinh doanh nào bị sụt doanh thu không?

Greater China giảm 2.575 triệu USD, tương đương 3,85% so với FY2024. [1][2]

HTTP trước và sau sửa 200 → 200.

- [1] Trang PDF 25 · Greater China 2025 · `cellv2_10a5b7cfe338a19ae9310c1f7274`
- [2] Trang PDF 25 · Greater China 2024 · `cellv2_6b73b70dbb458cd5f74adeda25ea`

### 2.2 · PASS · 2/2/2/2/2

Sụt nhiều không? Tính thử cả số tiền lẫn phần trăm cho tôi.

Greater China giảm từ 66.952 triệu USD [2] xuống 64.377 triệu USD [1]. Lấy số năm trước trừ số năm sau, mức giảm là 2.575 triệu USD. Chia mức giảm đó cho doanh thu năm trước, kết quả khoảng 3,85%. [1][2]

HTTP trước và sau sửa 200 → 200.

- [1] Trang PDF 25 · Greater China 2025 · `cellv2_10a5b7cfe338a19ae9310c1f7274`
- [2] Trang PDF 25 · Greater China 2024 · `cellv2_6b73b70dbb458cd5f74adeda25ea`

### 2.3 · PASS · 2/2/2/2/2

Tôi nhớ hình như giảm đến 5%, có đúng không?

Không đúng. Tính từ báo cáo, mức giảm là 3,85%. [1][2]

HTTP trước và sau sửa 200 → 200.

- [1] Trang PDF 25 · Greater China 2025 · `cellv2_10a5b7cfe338a19ae9310c1f7274`
- [2] Trang PDF 25 · Greater China 2024 · `cellv2_6b73b70dbb458cd5f74adeda25ea`

### 2.4 · PASS · 2/2/2/2/2

Vì sao khu vực này lại giảm?

Tại Greater China, báo cáo cho biết doanh thu iPhone giảm, được bù một phần nhờ doanh thu Mac tăng. [1]

HTTP trước và sau sửa 409 → 200.

- [1] Trang PDF 25 · Đoạn giải thích  · `paragraph_b83be0eb225f57f53675f71c7631`

### 2.5 · PASS · 2/2/2/2/2

Vậy doanh thu toàn Apple cũng giảm theo à?

Doanh thu toàn công ty tăng 6,43% so với FY2024. [1][2]

HTTP trước và sau sửa 200 → 200.

- [1] Trang PDF 32 · Total net sales 2025 · `cellv2_cc16f54065bce239f5e0fad95209`
- [2] Trang PDF 32 · Total net sales 2024 · `cellv2_7f1fcea611bce77e0db246ae826f`

### 2.6 · PASS · 2/2/2/2/2

Tóm tắt lại giúp tôi trong ba câu để đưa vào bài thuyết trình.

Doanh thu toàn công ty tăng 6,43% so với FY2024. [1][2] Greater China giảm 2.575 triệu USD, tương đương 3,85% so với FY2024. [3][4] Tại Greater China, báo cáo cho biết doanh thu iPhone giảm, được bù một phần nhờ doanh thu Mac tăng. [5]

HTTP trước và sau sửa 200 → 200.

- [1] Trang PDF 32 · Total net sales 2025 · `cellv2_cc16f54065bce239f5e0fad95209`
- [2] Trang PDF 32 · Total net sales 2024 · `cellv2_7f1fcea611bce77e0db246ae826f`
- [3] Trang PDF 25 · Greater China 2025 · `cellv2_10a5b7cfe338a19ae9310c1f7274`
- [4] Trang PDF 25 · Greater China 2024 · `cellv2_6b73b70dbb458cd5f74adeda25ea`
- [5] Trang PDF 25 · Đoạn giải thích  · `paragraph_b83be0eb225f57f53675f71c7631`

### 3.1 · PASS · 2/2/2/2/2

Biên lợi nhuận gộp mảng dịch vụ của Apple có cao hơn mảng sản phẩm nhiều không?

Biên lợi nhuận gộp dịch vụ là 75,4%, còn sản phẩm là 36,8%. Khoảng cách là 38,60 điểm phần trăm. [1][2]

HTTP trước và sau sửa 200 → 200.

- [1] Trang PDF 27 · Services 2025 · `cellv2_4f0cb65190a04c47482d27286917`
- [2] Trang PDF 27 · Products 2025 · `cellv2_96d358005561642d2b19cb12ddec`

### 3.2 · PASS · 2/2/2/2/2

Vậy cao hơn chính xác bao nhiêu?

Chênh 38,60 điểm phần trăm: 75,4% − 36,8%. [1][2]

HTTP trước và sau sửa 200 → 200.

- [1] Trang PDF 27 · Services 2025 · `cellv2_4f0cb65190a04c47482d27286917`
- [2] Trang PDF 27 · Products 2025 · `cellv2_96d358005561642d2b19cb12ddec`

### 3.3 · PASS · 2/2/2/2/2

Có nghĩa dịch vụ cao hơn sản phẩm 38,6% đúng không?

Không. 38,60 điểm phần trăm là kết quả của phép trừ trực tiếp 75,4% − 36,8%. Nếu muốn nói cao hơn bao nhiêu phần trăm so với sản phẩm, chia chênh lệch cho 36,8% rồi nhân 100. Kết quả là 104,89%. [1][2]

HTTP trước và sau sửa 200 → 200.

- [1] Trang PDF 27 · Services 2025 · `cellv2_4f0cb65190a04c47482d27286917`
- [2] Trang PDF 27 · Products 2025 · `cellv2_96d358005561642d2b19cb12ddec`

### 3.4 · PASS · 2/2/2/2/2

Nếu tính cao hơn theo tỷ lệ tương đối thì ra bao nhiêu?

Lấy mức biên của sản phẩm làm gốc, dịch vụ cao hơn khoảng 104,89%. [1][2]

HTTP trước và sau sửa 200 → 200.

- [1] Trang PDF 27 · Services 2025 · `cellv2_4f0cb65190a04c47482d27286917`
- [2] Trang PDF 27 · Products 2025 · `cellv2_96d358005561642d2b19cb12ddec`

### 3.5 · PASS · 2/2/2/2/2

Hai kết quả khác nhau như vậy thì nên dùng kết quả nào khi thuyết trình?

Khi trình bày hai mức biên cạnh nhau, dùng 38,60 điểm phần trăm vì người nghe có thể lấy 75,4% trừ 36,8% ngay. Dùng 104,89% nếu muốn diễn đạt mức chênh so với mức biên của sản phẩm làm gốc. [1][2]

HTTP trước và sau sửa 200 → 200.

- [1] Trang PDF 27 · Services 2025 · `cellv2_4f0cb65190a04c47482d27286917`
- [2] Trang PDF 27 · Products 2025 · `cellv2_96d358005561642d2b19cb12ddec`

### 3.6 · PASS · 2/2/2/2/2

Ghi rõ cả hai công thức và số liệu gốc để tôi kiểm tra.

Số gốc là 75,4% cho dịch vụ và 36,8% cho sản phẩm. [1][2]

Chênh lệch trực tiếp: 75,4 − 36,8 = 38,60 điểm phần trăm.

Chênh lệch tương đối: (75,4 − 36,8) ÷ 36,8 × 100 ≈ 104,89%. [1][2]

HTTP trước và sau sửa 200 → 200.

- [1] Trang PDF 27 · Services 2025 · `cellv2_4f0cb65190a04c47482d27286917`
- [2] Trang PDF 27 · Products 2025 · `cellv2_96d358005561642d2b19cb12ddec`

### 4.1 · PASS · 2/2/2/2/2

Tôi thấy Greater China năm 2025 đạt 69.377 triệu USD. Vậy tôi ghi vào slide như thế có đúng không?

Không đúng. FY2025, Greater China — doanh thu là 64.377 triệu USD [1]. Số bạn nêu chênh 5.000 triệu USD.

HTTP trước và sau sửa 200 → 200.

- [1] Trang PDF 25 · Greater China 2025 · `cellv2_10a5b7cfe338a19ae9310c1f7274`

### 4.2 · PASS · 2/2/2/2/2

Apple có lợi nhuận ròng bằng 416.161 triệu USD năm 2025 à?

Không đúng. FY2025, lợi nhuận sau thuế là 112.010 triệu USD [1]. Số bạn nêu chênh 304.151 triệu USD. Con số bạn nêu là doanh thu thuần [2].

HTTP trước và sau sửa 200 → 200.

- [1] Trang PDF 32 · Net income 2025 · `cellv2_25f617189ef25e8f66d0435486be`
- [2] Trang PDF 32 · Total net sales 2025 · `cellv2_cc16f54065bce239f5e0fad95209`

### 4.3 · PASS · 2/2/2/2/2

Doanh thu tại Mỹ với Americas là cùng một chỉ tiêu đúng không?

Hai phạm vi khác nhau. Mỹ là một quốc gia và Americas là một khu vực báo cáo. FY2025, Mỹ ghi nhận 151.790 triệu USD [1], Americas ghi nhận 178.353 triệu USD [2]. Chênh lệch là 26.563 triệu USD. [2][1]

HTTP trước và sau sửa 200 → 200.

- [1] Trang PDF 51 · U.S. 2025 · `cellv2_6c4ad85e0a38ea5b32b819976083`
- [2] Trang PDF 25 · Americas 2025 · `cellv2_efcea0b6ba623ac81e5550ebdad1`

### 4.4 · PASS · 2/2/2/2/2

Vậy hai con số đó chênh nhau khoảng bao nhiêu?

Chênh lệch là 26.563 triệu USD. [1][2] Hai phạm vi khác nhau. Mỹ là một quốc gia và Americas là một khu vực báo cáo. FY2025, Mỹ ghi nhận 151.790 triệu USD [2], Americas ghi nhận 178.353 triệu USD [1].

HTTP trước và sau sửa 200 → 200.

- [1] Trang PDF 25 · Americas 2025 · `cellv2_efcea0b6ba623ac81e5550ebdad1`
- [2] Trang PDF 51 · U.S. 2025 · `cellv2_6c4ad85e0a38ea5b32b819976083`

### 4.5 · PASS · 2/2/2/2/2

Đọc trong báo cáo này thì doanh thu cả năm 2026 của Apple là bao nhiêu?

Tài liệu đang chọn là báo cáo FY2025. [1] Tôi chưa có doanh thu cả năm FY2026 từ tài liệu này. Bạn có thể chọn báo cáo FY2026 để tôi kiểm tra đúng kỳ.

HTTP trước và sau sửa 200 → 200.

- [1] Trang PDF 32 · Total net sales 2025 · `cellv2_cc16f54065bce239f5e0fad95209`

### 4.6 · PASS · 2/2/2/2/2

Đổi doanh thu Services 2025 sang tiền Việt cho tôi, dùng tỷ giá hôm nay nhé.

Doanh thu dịch vụ FY2025 là 109.158 triệu USD [1]. Để đổi sang VND theo tỷ giá hôm nay, tôi cần một nguồn USD/VND có ngày áp dụng. Báo cáo này chỉ cung cấp số doanh thu bằng USD.

HTTP trước và sau sửa 200 → 200.

- [1] Trang PDF 32 · Services 2025 · `cellv2_9f570609f2c663fbe4508accfcdd`

### 5.1 · PASS · 2/2/2/2/2

Nếu chỉ có một phút đọc báo cáo Apple năm 2025, bạn thấy ba điểm đáng chú ý nhất là gì?

Doanh thu toàn công ty tăng 6,43% so với FY2024. [1][2]

Tỷ trọng dịch vụ tăng: từ 24,59% năm tài chính 2024 đến 26,23% năm tài chính 2025, chênh 1,64 điểm phần trăm sau khi làm tròn. [3][2][4][1] Điều này cho biết dịch vụ đóng góp nhiều hay ít hơn vào doanh thu, chưa đủ để kết luận doanh nghiệp phụ thuộc vào dịch vụ.

Greater China giảm 2.575 triệu USD, tương đương 3,85% so với FY2024. [5][6]

HTTP trước và sau sửa 200 → 200.

- [1] Trang PDF 32 · Total net sales 2025 · `cellv2_cc16f54065bce239f5e0fad95209`
- [2] Trang PDF 32 · Total net sales 2024 · `cellv2_7f1fcea611bce77e0db246ae826f`
- [3] Trang PDF 32 · Services 2024 · `cellv2_9aef27e2c60777264a1decc9e41e`
- [4] Trang PDF 32 · Services 2025 · `cellv2_9f570609f2c663fbe4508accfcdd`
- [5] Trang PDF 25 · Greater China 2025 · `cellv2_10a5b7cfe338a19ae9310c1f7274`
- [6] Trang PDF 25 · Greater China 2024 · `cellv2_6b73b70dbb458cd5f74adeda25ea`

### 5.2 · PASS · 2/2/2/2/2

Trong những điểm đó, điều nào liên quan đến tăng trưởng doanh thu?

Doanh thu toàn công ty tăng 6,43% so với FY2024. [1][2]

HTTP trước và sau sửa 200 → 200.

- [1] Trang PDF 32 · Total net sales 2025 · `cellv2_cc16f54065bce239f5e0fad95209`
- [2] Trang PDF 32 · Total net sales 2024 · `cellv2_7f1fcea611bce77e0db246ae826f`

### 5.3 · PASS · 2/2/2/2/2

Có phải Apple đang phụ thuộc ngày càng nhiều vào dịch vụ không?

Tỷ trọng dịch vụ tăng: từ 24,59% năm tài chính 2024 đến 26,23% năm tài chính 2025, chênh 1,64 điểm phần trăm sau khi làm tròn. [1][2][3][4] Điều này cho biết dịch vụ đóng góp nhiều hay ít hơn vào doanh thu, chưa đủ để kết luận doanh nghiệp phụ thuộc vào dịch vụ.

HTTP trước và sau sửa 200 → 200.

- [1] Trang PDF 32 · Services 2024 · `cellv2_9aef27e2c60777264a1decc9e41e`
- [2] Trang PDF 32 · Total net sales 2024 · `cellv2_7f1fcea611bce77e0db246ae826f`
- [3] Trang PDF 32 · Services 2025 · `cellv2_9f570609f2c663fbe4508accfcdd`
- [4] Trang PDF 32 · Total net sales 2025 · `cellv2_cc16f54065bce239f5e0fad95209`

### 5.4 · PASS · 2/2/2/2/2

Tôi chưa hiểu vì sao dịch vụ có tỷ suất lợi nhuận cao hơn sản phẩm. Báo cáo có giải thích cụ thể không?

Bảng cho thấy dịch vụ đạt 75,4% và sản phẩm đạt 36,8%. [1][2] Phần tôi đối chiếu chưa giải thích riêng vì sao có toàn bộ khoảng cách giữa hai mảng. Báo cáo giải thích biên dịch vụ tăng so với năm trước chủ yếu vì cơ cấu dịch vụ thay đổi, và chi phí cao hơn bù bớt phần tăng đó. [3]

HTTP trước và sau sửa 200 → 200.

- [1] Trang PDF 27 · Services 2025 · `cellv2_4f0cb65190a04c47482d27286917`
- [2] Trang PDF 27 · Products 2025 · `cellv2_96d358005561642d2b19cb12ddec`
- [3] Trang PDF 27 · Đoạn giải thích  · `paragraph_c7dcce83d3700489478021ba06c0`

### 5.5 · PASS · 2/2/2/2/2

Hãy giúp tôi giải thích điều đó cho người không học tài chính, không dùng thuật ngữ khó.

Cứ bán được 100 đô dịch vụ thì còn khoảng 75,4 đô sau chi phí trực tiếp. Nếu bán 100 đô sản phẩm thì còn khoảng 36,8 đô. [1][2] Hai con số này chưa trừ các chi phí khác của công ty. Báo cáo nói việc bán các loại dịch vụ khác nhau giúp công ty giữ lại nhiều tiền hơn so với năm trước, dù chi phí cao hơn làm giảm bớt mức tăng. [3]

HTTP trước và sau sửa 409 → 200.

- [1] Trang PDF 27 · Services 2025 · `cellv2_4f0cb65190a04c47482d27286917`
- [2] Trang PDF 27 · Products 2025 · `cellv2_96d358005561642d2b19cb12ddec`
- [3] Trang PDF 27 · Đoạn giải thích · `paragraph_c7dcce83d3700489478021ba06c0`

### 5.6 · PASS · 2/2/2/2/2

Giờ viết cho tôi đoạn kết luận 4 câu, có nguồn để tôi kiểm tra.

Biên gộp dịch vụ đạt 75,4%, sản phẩm đạt 36,8%, chênh 38,60 điểm phần trăm. [1][2] Dịch vụ đóng góp 26,23% doanh thu FY2025. [3][4] Doanh thu toàn công ty tăng 6,43% so với FY2024. [4][5] Báo cáo giải thích mức tăng so với năm trước bằng sự thay đổi cơ cấu dịch vụ và tác động bù trừ của chi phí cao hơn, còn nguyên nhân của toàn bộ khoảng cách với sản phẩm chưa được xác định trong đoạn này. [6]

HTTP trước và sau sửa 200 → 200.

- [1] Trang PDF 27 · Services 2025 · `cellv2_4f0cb65190a04c47482d27286917`
- [2] Trang PDF 27 · Products 2025 · `cellv2_96d358005561642d2b19cb12ddec`
- [3] Trang PDF 32 · Services 2025 · `cellv2_9f570609f2c663fbe4508accfcdd`
- [4] Trang PDF 32 · Total net sales 2025 · `cellv2_cc16f54065bce239f5e0fad95209`
- [5] Trang PDF 32 · Total net sales 2024 · `cellv2_7f1fcea611bce77e0db246ae826f`
- [6] Trang PDF 27 · Đoạn giải thích · `paragraph_c7dcce83d3700489478021ba06c0`
