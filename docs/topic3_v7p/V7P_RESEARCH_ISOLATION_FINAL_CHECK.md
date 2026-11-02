# Kiểm tra cách ly nghiên cứu — RC

Checkpoint `53a1ab2d7722438912e4d1b13b5329b00af8ee29`; code mới `209faf9988490ec9f8f6979f304b4e3852724d5a`. Dùng manifest `V7P_FREEZE_BLOB_AUDIT.json`, so từng Git blob HEAD và working file qua `git ls-tree -r HEAD` + `git hash-object --stdin-paths`: **843/843 khớp**, changed=[]; không đọc nội dung sealed labels để chạy câu hỏi. Không chỉnh manifest lịch sử để hợp thức hóa kết quả.

Manifest có trường lịch sử `manifest_sha256=739a81d…ce28`; đó không được coi là SHA256 raw JSON có whitespace/line endings hiện tại. Lượt này xác minh trực tiếp từng blob trong files[]; SHA256 canonical Git bytes của chính JSON là `8ecd09222e8ca57f11c1bd83651f1facdc0d3c5cf48fc38084e1a402e6ad08ec`, raw checkout CRLF là `526c5b1a85348827044b6edc28b12837f62c9f71a5a9ea3495fd0cf53b7fab5a`. Khác serialization không phải thay đổi scientific artifact.

- Không thay 8.670 chunks, Qdrant A/B, V6 freeze/sealed30, G2 94, F10 qrels, PolicyB, author results hay cấu hình FAITH-R. Không chạy sealed benchmark, không merge/copy PR36.
- Main remote giữ `ceaa8acfcfaea8056e45b859a0fc44d6381fb22a`; PR34 base `codex/topic3-v7a-g2-sec47-question-freeze` giữ `cd8deb96cb8c147ca5c090e9c0a323de511c65bd`. Chỉ cập nhật source branch PR35.
- Hai working-tree entries qrels/V6 CSV có từ trước, không có content diff; không stage, reset hay ghi đè chúng.
- Original A7 ledger/browser/failure và verdict V7P_NOT_ACCEPTED không sửa. RC dùng tên file mới.
- Research Lab browser vẫn nêu kết quả lịch sử không phải truy vấn vừa chạy, nhãn provisional không phải đánh giá con người. Không chạy benchmark trong smoke.
- HD raw bytes sau kiểm thử giữ SHA `3d638bc025ef9643317d539f63c3891c8db9b47e35a8edd8040928704d0703f1`. Nguồn SEC đọc tại chỗ, không download/re-embedding/rebuild Qdrant research.
- Upload tạm chỉ ghi workspace user riêng; hai trang dẫn xuất, năm chunks mới, cleanup đúng ID sau kiểm thử. Apple/HPG gốc giữ READY. Không chứng nhận byte-for-byte toàn ổ đĩa: bằng chứng là code diff, frozen blob audit, HD hash và scoped runtime operations.

Đây là nghiệm thu kỹ thuật demo, không hoàn thành FAITH-R, không nghiên cứu retrieval mới, không human qrel adjudication và không bằng chứng Hybrid superiority.
