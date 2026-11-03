# C4: kết quả thật trên log G3U một lần chạy

**Phép đo được phép:** trong Top-1/5/10 có chunk thuộc đúng SEC accession của câu hỏi hay không. Đây là **proxy nhận diện filing**, không phải độ đúng ô tài chính, đáp án hay qrels. Tập 93 câu được khóa trước khi xem thứ hạng; 1 câu đã EXCLUDE vẫn có trong bảng phủ 94 câu nhưng không chấm. Log thật có 1.588 arm×câu×index có dòng hit; **104 thiếu dòng**. Với 104 lượt đó, log không phân biệt được trả về rỗng hay thiếu ghi nhận; mẫu số từng arm chỉ gồm lượt có dòng hit. Không điền số 0 cho lượt chưa chứng thực.

Log là pool G3U v2 đã chạy trên **8.670 original chunks** ở A/B; C4 chỉ đọc lại và chấm proxy, không chạy lại câu G2. Sáu phương pháp tác giả là BM25, BGE Dense, SPLADE, hai RRF, Stage-2 heuristic. RRF trong mã chạy thực là Qdrant mặc định **k=2**; biến thể tường minh k=60 trong work order C4 **không được chạy** sau khi đã thấy kết quả, nên bảng này không được gọi là phép thử k=60. Stage-2 lấy 60 ứng viên nội bộ để xuất Top-20. Đây là tái lập mã tác giả trên corpus phục hồi 8.670 chunks, không phải corpus lịch sử 8.609 chunks.

| Chỉ mục | Arm | Lượt có hit / 93 | Top-1 | Top-5 | Top-10 | p50 / p95 ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| A | Tác giả BM25 | 93 | 37 | 76 | 84 | 449 / 530 |
| A | Tác giả BGE Dense | 93 | 39 | 81 | 85 | 62 / 101 |
| A | Tác giả SPLADE | 93 | 31 | 82 | 89 | 908 / 1088 |
| A | Tác giả BM25+BGE RRF | 93 | 44 | 77 | 88 | 497 / 577 |
| A | Tác giả SPLADE+BGE RRF | 93 | 42 | 84 | 90 | 1006 / 1146 |
| A | Tác giả Stage-2 heuristic | 93 | 60 | 88 | 92 | 1096 / 1288 |
| A | FAITH-R A0 | 93 | 44 | 77 | 88 | 495 / 568 |
| B | Tác giả BM25 | 93 | 37 | 76 | 84 | 440 / 525 |
| B | Tác giả BGE Dense | 93 | 39 | 81 | 85 | 58 / 83 |
| B | Tác giả SPLADE | 93 | 31 | 82 | 89 | 904 / 1104 |
| B | Tác giả BM25+BGE RRF | 93 | 44 | 77 | 88 | 490 / 559 |
| B | Tác giả SPLADE+BGE RRF | 93 | 42 | 84 | 90 | 991 / 1149 |
| B | Tác giả Stage-2 heuristic | 93 | 74 | 90 | 92 | 1082 / 1184 |
| B | FAITH-R A1 | 93 | 44 | 77 | 88 | 490 / 560 |
| B | FAITH-R A2 | **67; 26 chưa có dòng** | 47 | 47 | 47 | 669 / 789 |
| B | FAITH-R A3 | **67; 26 chưa có dòng** | 47 | 47 | 47 | 683 / 793 |
| B | FAITH-R A4 | **67; 26 chưa có dòng** | 47 | 47 | 47 | 676 / 834 |
| B | FAITH-R A4R* | **67; 26 chưa có dòng** | 47 | 47 | 47 | 678 / 795 |

\* A4R là phát triển **đã lộ kết quả**, không dùng để tuyên bố thắng độc lập. Thời gian gồm embedding và Qdrant trong lần pool, pha cold/warm trộn lẫn; không phải số đo sản phẩm PR #35. A và B khác payload fiscal trên 3.516 điểm thuộc 15 filing, nên A0→A1 là so sánh hệ thống, không cô lập reranking.

**Đối đầu cùng B, cùng 67 câu có dòng của hai arm, tại Top-5:**

| So sánh (arm bên phải là A4) | Tác giả đúng / 67 | A4 đúng / 67 | A4 thắng / hòa / thua |
| --- | ---: | ---: | ---: |
| BM25 → A4 | 55 | 47 | 10 / 39 / 18 |
| BM25+BGE RRF → A4 | 56 | 47 | 9 / 40 / 18 |
| Stage-2 heuristic → A4 | 66 | 47 | 0 / 48 / 19 |

Trên proxy này, **A4 không thắng tổng thể**. Trong ablation, A0→A1 có 93 hòa (77/93 Top-5 ở cả hai). A1→A2 trên 67 câu chung: 9 thắng / 40 hòa / 18 thua. A2→A3 và A3→A4 đều 67 hòa theo proxy Top-5. Bộ lọc A2 làm thay đổi mẫu số, nên không so 47/67 trực tiếp với 77/93 như thể hai phép đo cùng phủ toàn bộ.

**Minh họa công khai, chọn sau khi xem kết quả:** `05_01` Apple FY2025: chunk đúng filing ở hạng 7 của tác giả BM25+BGE, hạng 1 của A4. Đây chỉ là đúng *filing*, chunk hạng 1 của A4 nằm ở Item 5, không chứng minh đúng ô cost of sales. Ca ngược `03_01` Apple 10-Q: tác giả ở hạng 1, A4 không thấy filing đích trong Top-20. Cả hai phải được trình bày cùng nhau và gắn nhãn `ILLUSTRATIVE_CASE_NOT_INDEPENDENT_WIN_RATE`.

**Không báo cáo** EXACT@K, MRR, nDCG, Recall hoặc độ đúng đáp án tài chính: 5.792 cặp blind hiện chỉ có 124 `PARTIAL` AI tạm thời, 5.668 `UNJUDGED`, **0 EXACT/NONE và 0 human qrels**. [Bảng phủ qrels theo arm và K](C4_QREL_COVERAGE_AT_K_V1.json) ghi số ô đã/ chưa được xem, không biến `UNJUDGED` thành sai. Dữ liệu chi tiết/hashes ở [scorecard máy đọc](C4_OBJECTIVE_PROXY_SCORECARD_V1.json).
