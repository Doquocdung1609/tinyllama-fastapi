# Dàn ý 9 slide cho buổi 04/11/2026

1. **Đề tài và câu hỏi nghiên cứu.** “Hybrid Search cho báo cáo tài chính: có tìm đúng công ty, kỳ và ô không?” Không nêu một tỷ lệ thắng khi chưa đo.
2. **Vì sao tìm kiếm thông thường dễ sai.** Cùng metric qua nhiều FY/quý; đoạn đúng filing vẫn có thể sai dòng, và OCR scan có thể méo số.
3. **Phương pháp gốc.** Sáu nhánh BM25/BGE/SPLADE/hai RRF/Stage-2 heuristic. Nói rõ Stage-2 không phải ColBERT inference; pool k20, nội bộ 60.
4. **Dữ liệu và giao thức.** 47 SEC filings, 8.670 chunks phục hồi, 94 câu G2 khóa, A/B metadata; 102 event review nguồn, 93 câu proxy hợp lệ, chưa đủ qrels EXACT.
5. **FAITH-R và lỗi được phát hiện.** A0–A4R, issuer/fiscal/sidecar/rerank; sơ đồ source → chunk → qrel. Lỗi FY-filter so với 10-Q Q-period; không che 26 run thiếu dòng.
6. **Bảng điểm thật.** Chỉ số đúng filing Top-1/5/10, mỗi arm có mẫu số; A4 47/67 Top-5, BM25+BGE B 77/93, Stage-2 B 90/93. Trên 67 câu chung A4 9 thắng/40 hòa/18 thua so RRF. Không gọi là answer accuracy.
7. **Hai ca minh họa trung thực.** Apple `05_01` A4 có filing hạng 1 so baseline 7, nhưng chưa đúng ô; Apple `03_01` A4 mất filing Top-20, baseline hạng 1. Chọn hậu kiểm, không đại diện tỷ lệ.
8. **Demo React sống.** BIDV điều chỉnh 2024: PDF/trang 8 + BM25/Dense/Hybrid cùng scope; HPG scan: trang 5 OCR và từ chối số hợp nhất từ báo cáo riêng. Ảnh dự phòng có SHA.
9. **Kết luận và giới hạn.** FAITH-R chưa thắng tổng thể trên proxy; mã/nguồn/Qdrant/ứng dụng và cơ chế từ chối đã được chứng minh. Muốn kết luận khoa học cần sửa filter theo phiên bản mới, tập độc lập và human original-chunk qrels.
