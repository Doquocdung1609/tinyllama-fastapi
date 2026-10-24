# Nội dung Draft PR đã chuẩn bị — chưa gửi GitHub

Target đề xuất: `codex/topic3-milestone-b-sec-corpus` sau khi xác minh remote và người đóng góp. Branch nguồn: `codex/topic3-milestone-b-independent-verification-20261024`.

Title: fix(sec): preserve source text order and report incomplete financial tables

HTML có inline tags có thể bị đảo thứ tự nhãn/số âm; redirect ngoài SEC được kiểm sau khi request đã xảy ra. Bản sửa giữ thứ tự DOM, kiểm đích HTTPS trước từng redirect và giới hạn redirect hops. Bảng có nội dung nhưng headers trống được đánh dấu PARTIAL_EXTRACTION thay vì OK. Parser/chunker nâng v2; dùng corpus kiểm tra riêng.

Bằng chứng: một Apple 10-Q tải trực tiếp, HTTP 200, raw hash khớp bàn giao, 40 bảng/4.762 cells đối chiếu độc lập, 12 provenance samples VERIFIED và idempotency 620 IDs. 123 tests passed, 4 skipped, 1 warning; compileall và pip check đạt.

Nghiệm thu PARTIAL vì semantic headers/periods/scale/footnotes chưa đủ và real model/OCR/media/amendment chưa được kiểm. Không triển khai Milestone C. Phụ thuộc Milestone A/B chưa merge trong baseline; không merge vào main hoặc gộp phạm vi ngoài ý muốn. Không merge PR này tự động.
