# Topic 3 — Hybrid Search

| Tiêu chí | Quan sát thật ngày 28/10/2026 | Kết quả |
|---|---|---|
| PDF Việt Nam thật | HPG 24 trang, BIDV 8 trang; 64 + 23 = 87 chunks | PASS |
| Lexical | FTS5 BM25, cache tiếng Việt gấp dấu; văn bản Unicode gốc còn nguyên | PASS |
| Dense | Nomic local đúng digest/768; Qdrant cô lập | PASS |
| Hybrid | RRF k=60, giữ rank kênh; cùng eligible documents | PASS |
| Truy vấn Việt Nam | 5 truy vấn × 3 phương pháp = 15 request có kết quả đúng document scope | PASS khả năng truy xuất; chưa phải đo Recall |
| Total assets HPG | Sau sửa gấp dấu, PDF trang 3 top-1 trên cả ba kênh | PASS ca cụ thể |
| Nguồn | byte hash + trang + tọa độ thật, viewer scan/native/rotate | PASS |
| Bộ lọc | source/company/period/document; SEC HD và PG kiểm tra riêng | PASS |
| So sánh | ba arms, cùng generation, latency/overlap thật, quality_metrics=None | PASS |
| SEC | nguồn chính thức mới 1.241 parents/vectors, ba kênh PG/HD | PASS phiên sản phẩm mới |
| Restart/idempotency | upload lại không tăng tài liệu/chunks, hash/87 thành viên giữ nguyên | PASS |
| Qrels mới / held-out | không tạo theo stop condition | NOT_TESTED / ngoài phạm vi |

Các câu kiểm tra: “tổng cộng tài sản”; “chính sách kế toán ghi nhận doanh thu”; “dòng tiền từ hoạt động kinh doanh” (HPG); “tổng tài sản hợp nhất điều chỉnh”; “số trình bày lại” (BIDV). Có kết quả không tự chứng minh tất cả đoạn đều liên quan. Nomic được giữ nguyên; chưa có bằng chứng đủ để tuyên bố chất lượng đa ngôn ngữ tổng quát hoặc Hybrid luôn tốt hơn BM25.

SEC: HD total assets 02/08/2026 và PG net sales quý kết thúc 30/09/2026 kiểm tra BM25/Dense/Hybrid, issuer filter và provenance. Dữ liệu product-only, không trộn benchmark P10 cũ. Xem RUNTIME_EVIDENCE.json cho ID/hashes, latencies và nguồn cụ thể.
