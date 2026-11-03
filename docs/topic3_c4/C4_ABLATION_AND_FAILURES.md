# C4 ablation và nguyên nhân thất bại

Read-only scan trên index B xác nhận 8.670 payload thuộc 47 accessions; không sửa index. Trong 93 câu proxy hợp lệ, 47 câu A4 có filing đích trong Top-20 và metadata của đích vượt qua bộ lọc. **46 câu còn lại có target payload không thể vượt qua bộ lọc fiscal hiện tại:** 26 câu không có dòng hit trong log (24 câu 10-Q, 2 câu TSM 20-F), 20 câu có hit nhưng toàn bộ Top-20 là filing khác. Chỉ khi nhìn riêng 26 dòng trống, ta không thể chứng thực runner đã ghi từng lượt trả về rỗng; mã chạy khẳng định tổng 1.692 lượt và nguồn metadata cho thấy filing đích bị loại. [Chẩn đoán máy đọc](C4_FAILURE_DIAGNOSIS_V1.json).

`safe_filters` đặt `fiscal_period = FY<year>` cho câu chỉ nêu một năm. Nhưng 10-Q trong index mang `Q-YYYY-MM`. Với hai câu TSM 20-F FY2022, payload đích ở B lại mang `FY2023`; đây là một lỗi metadata còn sót. Khi tồn tại 10-K cùng công ty/năm, bộ lọc có thể chọn sai filing thay vì trả rỗng. Vấn đề này giải thích việc target bị loại; nó không chứng minh mọi thứ hạng còn lại do đúng một nguyên nhân. Sau khi đã xem kết quả G2, **không sửa thuật toán rồi chạy lại cùng holdout để tuyên bố chiến thắng độc lập**. Cần phiên bản thực nghiệm mới, công bố mức lộ và tập đánh giá độc lập.

| Bước | Proxy Top-5 trên cùng câu có dòng | Kết quả |
| --- | --- | --- |
| A0 (A) → A1 (B) | 93 cặp | 0 thắng, 93 hòa, 0 thua |
| A1 → A2 | 67 cặp | 9 thắng, 40 hòa, 18 thua; 26 câu không có dòng A2 |
| A2 → A3 | 67 cặp | 0 thắng, 67 hòa, 0 thua |
| A3 → A4 | 67 cặp | 0 thắng, 67 hòa, 0 thua |

Trong khi đó Stage-2 tác giả trên B đạt 90/93 Top-5, nhưng dùng 60 ứng viên nội bộ và có p50 khoảng 1.082 ms so với khoảng 676 ms của A4 trên 67 lượt có dòng. Không suy ra ưu thế chi phí từ mẫu số khác nhau hoặc từ số đo cold/warm trộn. A2 dùng lọc issuer/fiscal, nên bất kỳ tăng Top-1 nào cũng là hiệu ứng hệ thống có lọc, không phải thứ hạng thuần. A3 sidecar làm thêm quét payload; A4 reranking của ứng viên đó không thay đổi proxy Top-5 trong 67 ca còn lại.

Ca minh họa thắng `05_01` và thua `03_01` có dữ liệu Top-5 + chunk ID thật trong gói riêng tư C4. Cả hai không có nhãn original-single-chunk EXACT; không chấm chúng như đúng đáp án. Các nhóm lỗi cần tách khi có qrels thật: nguồn có nhưng corpus thiếu (3 AMD), thiếu retrieval, reranker chọn sai, sai filing/kỳ, sai metric/đơn vị, mệnh đề chưa đủ và OCR không chắc chắn.
