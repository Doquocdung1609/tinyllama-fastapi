# Hỏi đáp bảo vệ — C4

1. **Phương pháp gốc của ai?** Mã tác giả được ghim ở commit `16682dd42ca9cd4887ae74935cb3526dce580c49`; chúng em chạy sáu phương pháp trong mã đó trên bản corpus phục hồi.
2. **Điểm mới của nhóm?** FAITH-R thêm logic issuer/fiscal, tìm ứng viên bảng và xếp hạng chứng cứ; ứng dụng cho phép xem nguồn PDF và từ chối số chưa xác minh.
3. **Vì sao gọi là tái lập chứ không bản gốc?** Corpus phục hồi 8.670 chunks, khác 8.609 chunks lịch sử; chỉ mục A cũng là phục hồi P3D, không chứng minh giống P3C đã mất.
4. **RRF k bao nhiêu?** Config ghi 60 nhưng đường chạy tác giả dùng Qdrant local mặc định k=2. Pool G3U v2 đã khóa k=2 sau khi công bố sai lệch. Không gán kết quả này cho thử nghiệm k=60.
5. **Stage-2 có phải ColBERT không?** Không. Nó dùng đặc trưng cố định và quy tắc sắp xếp; Top-20 cần 60 ứng viên nội bộ.
6. **A và B khác nhau thế nào?** B sửa fiscal payload của 3.516 điểm trên 15 filing. So A0→A1 là hiệu ứng hệ thống/index, không chỉ ranking.
7. **86 câu APPROVE có phải 86 gold?** Không. Hash chain nguồn hợp lệ nhưng identity reviewer tự khai; chỉ 67 qua preview cấu trúc, 19 block nguồn, 7 cần correction, 1 loại. Qrels chunk gốc vẫn chưa có EXACT/human.
8. **Vì sao không báo Recall/MRR/nDCG?** Pool còn 5.668 cặp UNJUDGED và 0 EXACT. Gán UNJUDGED là sai sẽ tạo số giả; chúng em chỉ báo proxy đúng filing với mẫu số rõ.
9. **FAITH-R có thắng không?** Không trên proxy Top-5 toàn bộ. A4 thắng BM25+BGE ở 9/67 cặp chung nhưng thua 18, hòa 40; còn 26 câu không có dòng A4.
10. **Nguyên nhân 26 câu thiếu là gì?** Target 10-Q dùng `Q-YYYY-MM` trong payload nhưng bộ lọc hỏi `FY<year>`; thêm 2 câu TSM 20-F FY2022 có payload FY2023. Log hit không có bản ghi run rỗng nên chúng em ghi rõ giới hạn provenance.
11. **Độ trễ so được không?** p50/p95 đo thật gồm embedding + Qdrant, nhưng cold/warm trộn và A4 chỉ có 67 lượt có dòng, vì vậy không kết luận ưu thế chi phí chung. Stage-2 B p50 khoảng 1.082 ms; A4 khoảng 676 ms trên mẫu quan sát.
12. **Ví dụ tốt có phải chọn sau không?** Có. Apple `05_01` và ca thua `03_01` đều được chọn hậu kiểm để minh họa; không dùng làm win rate độc lập.
13. **Hòa Phát OCR có đáng tin để trả lời số?** OCR tìm được trang 5 nhưng có ký tự méo, nên đoạn nguồn chỉ là ứng viên. Ứng dụng từ chối câu hỏi hợp nhất trên báo cáo công ty mẹ.
14. **BIDV điều chỉnh số liệu ra sao?** PDF 2024 có ba cột đã công bố, điều chỉnh KTNN, trình bày lại; demo chỉ cho thấy nguồn trang 8 và so phương pháp tìm kiếm, không phê chuẩn tự động mọi số.
15. **Nếu mất mạng hoặc SEC.gov chặn?** Demo PDF cục bộ không cần SEC web. Log SEC nghiên cứu có accession/hash đã lưu; chỉ rõ SEC trong worktree sản phẩm hiện UNAVAILABLE, không giả lập truy cập live.
16. **Có chạy Colab không?** Chưa. Lần đo C4 dùng chỉ mục Qdrant cục bộ CPU; không báo notebook hoặc GPU chưa chạy là kết quả.
