# C4R: kết quả truy hồi và trả lời tài chính có nguồn

**Nguồn:** 16 sự kiện iXBRL thuộc 16 hồ sơ SEC khác nhau, 8 hồ sơ 10-K và 8 hồ sơ 10-Q. Bốn sự kiện dùng phát triển; 12 sự kiện còn lại được khóa trước khi chạy. Tham chiếu được máy đọc từ SEC HTML nguyên gốc, kiểm tra SHA, context không phân khúc, kỳ và đơn vị USD triệu, sau đó đối chiếu nhãn hàng hiển thị. **Chưa có người kiểm định ký duyệt**; đây là tập thăm dò nhỏ, câu hỏi mới nhưng không phải hồ sơ/công ty chưa từng thấy. [Manifest công khai](C4R_NEW_EVALUATION_MANIFEST.json) chỉ chứa hash và mẫu số; giá trị đáp án ở gói riêng tư.

## English, 12 sự kiện giữ lại, cùng chỉ mục B, Top-5

| Phương pháp | Đúng filing Top-1 /12 | Top-5 /12 | Trả lời đúng /12, nguồn iXBRL | Từ chối /12 | p50 ms |
| --- | ---: | ---: | ---: | ---: | ---: |
| Tác giả BM25 | 7 | 9 | 9 | 3 | 1065 |
| Tác giả Dense | 5 | 9 | 9 | 3 | 89 |
| Tác giả SPLADE | 5 | 10 | 10 | 2 | 1144 |
| Tác giả BM25+BGE RRF | 7 | 11 | 11 | 1 | 577 |
| Tác giả SPLADE+BGE RRF | 5 | 9 | 9 | 3 | 1262 |
| Tác giả Stage-2 heuristic | 8 | 11 | 11 | 1 | 1343 |
| A5_BASE, tối đa 60 ứng viên | **12** | **12** | **12** | 0 | 887 |
| A5_FALLBACK | 12 | 12 | 12 | 0 | 816 |
| A5_SIDECAR v1 | 12 | 12 | 12 | 0 | 885 |

Mỗi phương pháp có **12/12 dòng thực thi** và Top-20 tối đa; không có dòng lỗi. A5_BASE và Stage-2 đều sử dụng tối đa 60 ứng viên nội bộ cho Top-20, nhưng mô hình truy hồi, bộ lọc và chi phí tính toán khác nhau. A5 dùng issuer/form và sắp xếp kỳ từ manifest nguồn công khai cho **mọi** ứng viên; Stage-2 tác giả chạy nguyên gốc không áp bộ lọc đó. Đây là so sánh **hệ thống**, không cô lập riêng reranker. `A5_FALLBACK` không phải phát truy vấn thứ hai trong 12 câu vì lượt đầu đã đủ 60 ứng viên. `A5_SIDECAR v1` quét thêm 8.670 payload/câu nhưng các hàng thêm bị cắt ở ngưỡng 60; số liệu giữ lại này không chứng minh tác dụng sidecar. Các p50 là thời gian thực đo theo **thứ tự phương pháp cố định** và cache nguồn chung được làm ấm dần; không dùng chúng để tuyên bố phương pháp nào nhanh hơn trong phép đo latency công bằng.

**Cặp Stage-2 vs A5_BASE:** 1 thắng, 11 hòa, 0 thua ở Top-5 và trả lời có nguồn. Ca thắng là AMD 10-Q accession `0000002488-25-000108`: Stage-2 không đưa filing nguồn vào Top-5; A5 đưa vào và bộ trả lời trích ô iXBRL. Không có ca A5 thua trong 12 sự kiện; không tự tạo ca thua. Wilson 95% cho 12/12 là khoảng **0,757–1,000**, cho 11/12 là **0,646–0,985**; khoảng chồng lấn mạnh, nên **không chứng minh vượt trội tổng quát**.

## Hai ranh giới về độ đúng

`ORIGINAL_CHUNK_ONLY`: **0/12 trả lời xác minh**, 12/12 từ chối ở cả Stage-2 và A5. Chunk gốc đã làm phẳng bảng, không giữ đủ context iXBRL/quan hệ cột; bộ trả lời không đoán số từ dấu `|` và chữ số gần nhau.

`SOURCE_ENRICHED_V1`: chỉ sau khi một original chunk đưa **accession** vào Top-5, cùng một bộ trả lời cho mọi phương pháp đọc SEC HTML đã xác minh của accession đó, kiểm tra concept + context + kỳ + USD triệu + phạm vi không phân khúc và ghi locator `#f-...`. Phần này là **nguồn bổ sung**, không phải original-chunk `EXACT` qrel. Bộ tạo tham chiếu và bộ trả lời cùng dùng bộ phân tích iXBRL, nên kết quả trả lời có phụ thuộc quy tắc máy chung; chưa được xác nhận độc lập bởi con người. Không báo cáo Recall/MRR/nDCG của corpus.

## Tiếng Việt, 12 cách diễn đạt ghép cặp với cùng sự kiện

| Phương pháp | Top-5 /12 | Trả lời có nguồn /12 | Từ chối /12 | p50 ms |
| --- | ---: | ---: | ---: | ---: |
| Tác giả BM25 | 9 | 9 | 3 | 1055 |
| Tác giả Dense | 6 | 6 | 6 | 72 |
| Tác giả SPLADE | 4 | 4 | 8 | 952 |
| Tác giả BM25+BGE RRF | 10 | 10 | 2 | 544 |
| Tác giả SPLADE+BGE RRF | 6 | 6 | 6 | 1085 |
| Tác giả Stage-2 | 10 | 10 | 2 | 1187 |
| A5_BASE | **12** | **12** | 0 | 761 |

Tiếng Việt được mở rộng thành từ khóa tiếng Anh một cách xác định và truy vấn trên **chính 8.670 chunk tiếng Anh**; không trộn vector của mô hình đa ngữ khác vào BGE. Cùng 12 sự kiện với English, tạo **sau** khi English đã chấm, nên không được cộng thành 24 sự kiện độc lập. Sau lượt đầu, bộ định dạng được sửa để trả lời bằng tiếng Việt; lượt ghép cặp thứ hai vẫn cho 12/12 A5_BASE, và **12/12 literal** bắt đầu bằng `Giá trị được xác minh:`. Đây là kiểm thử lặp sau lộ, không phải holdout mới. 40 trường hợp đối chứng từ vựng tách `doanh thu`/`giá vốn`, lợi nhuận gộp/biên lợi nhuận, công ty mẹ/hợp nhất, 3/6/9 tháng và các từ gần nghĩa sai. Trên sản phẩm PDF PR #35, C4R cũng chạy [12 lượt tìm kiếm thực](C4R_HPG_BIDV_PAIRED_PDF_SMOKE.json) cho Hòa Phát/BIDV × Việt/Anh × ba mode: 12 HTTP 200 và 12 lượt có năm ứng viên. Trang Top-1 khác nhau theo ngôn ngữ/mode; không có gold số đáng tin cho OCR Hòa Phát hoặc cột điều chỉnh BIDV, nên **không chấm PDF answer accuracy**.

## G2 sau lộ kết quả

G2 A5_BASE chạy lại **94/94 câu**, một dòng trạng thái mỗi câu; 93 câu hợp lệ proxy có **91/93 Top-1** và **93/93 Top-5** filing. C4 A4 cũ chỉ có hit rows 67/93; 26 lượt cũ vẫn là `UNKNOWN_ZERO_VS_OMITTED`. Stage-2 cũ 90/93 Top-5. Đây là `POST_EXPOSURE_REGRESSION_DIAGNOSTIC`, không cộng vào benchmark mới và không làm mất kết quả C4 trước sửa.

Máy đọc: [English holdout](C4R_HOLDOUT_SCORECARD.json), [Vietnamese paired v1](C4R_VN_PAIRED_SCORECARD.json), [Vietnamese literal v2](C4R_VN_PAIRED_FORMAT_V2_SCORECARD.json), [G2 diagnostic](C4R_G2_POST_EXPOSURE_SUMMARY.json), [latency/RAM](C4R_LATENCY_RESOURCE_REPORT.json). Chi tiết 100% câu×phương pháp, bao gồm từ chối, đơn vị/kỳ, gold và mã lỗi, nằm trong gói riêng tư có SHA.
