# Milestone C — hardening baseline

## Phạm vi cố định

- Review độc lập bắt đầu từ expected HEAD `4ce6176ce0208303dc966813738acefc4879d021`; hai sửa lỗi review trước nằm ở `bb91bc50ee75688eac317634055693b97737e430`.
- Baseline của đợt hardening này là Draft PR #8 tại `bb91bc5`; PR không được merge và Milestone D không được bắt đầu.
- Môi trường đo: Windows 11 `10.0.26300`, Python `3.13.2`, SQLite `3.45.3`, Ollama `0.30.10`, qdrant-client `1.19.1`.
- Embedding pin: `nomic-embed-text:latest`, digest `0a109f…e59f`, dimension 768, document/query prefixes riêng, truncate ở 6.000 ký tự.

## Baseline đã bảo toàn

File `MILESTONE_C_MEASUREMENTS.json` không bị sửa. Frozen 14-query set giữ SHA-256 `c40d85…fc7e`; replay trước hardening đã khớp reported results: BM25/Dense/Hybrid Recall@5 lần lượt `0,911 / 0,321 / 0,714`. Đây là development evidence, không phải held-out claim.

Các thiếu sót baseline được xác nhận từ source: mutation API không auth/rate bound, embedded Qdrant không có cross-process owner, không có retention/GC, provenance parse/rechunk lại mọi request, lỗi HTTP có thể lộ path, input chưa canonicalize đủ, timeout/identity Ollama chưa đầy đủ và Windows effective-path chưa được preflight.

## Corpus cô lập

Không sửa dữ liệu lịch sử của owner. Thử nghiệm hardening dùng `C:\msch` và `C:\mscr`; corpus mới 145,08 MiB, index issuer 25,63 MiB. Hai generation issuer có 640 membership records, 634 unique vector texts. Raw corpus không nằm trong cleanup scope.

## Regression baseline

- Report trước thay đổi: 182 PASS.
- Sau hai repair độc lập trước: 184 PASS trong owner environment có real media.
- Trước hai repair cuối của hardening: `193 passed, 3 skipped` trong environment review; ba skip là real image/SAPI/ffmpeg do `RUN_REAL_MEDIA_TESTS` chưa bật.
