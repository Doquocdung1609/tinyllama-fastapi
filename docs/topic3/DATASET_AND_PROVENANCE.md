> Current evidence update: live Apple and Tesla original/amendment tests now exist; see MILESTONE_B_FINAL_GAP_AUDIT.md. Earlier blocked-live statements below describe the pre-handoff stage. Active-only derived-revision lookup remains a documented limitation.

# Dataset, Versioning và Provenance

## Vì sao cần hash và version

Accession chứng minh filing logic, còn SHA-256 chứng minh bytes đã xử lý. Raw snapshot được lưu theo `{cik}/{accession}/{raw_sha256}/{primary_document}` và không sửa tại chỗ. Structured JSON, chunks JSONL và staging metadata cũng có raw hash trong đường dẫn. Nếu cùng accession trả nội dung khác khi force refresh, cả hai raw/processed artifact vẫn tồn tại.

`normalized_content_hash` phát hiện thay đổi sau chuẩn hóa/parser, còn parser/chunker version giúp phân biệt thay đổi thuật toán với thay đổi nguồn.

## Chuỗi truy vết

```text
result/chunk_id
 -> chunks.chunk_json
 -> filing_id + document_version
 -> CIK + accession + source_url
 -> SourceLocation
 -> immutable raw bytes
 -> reparse + source_text_hash comparison
 -> original disclosure
```

Endpoint `GET /financial-corpus/evidence/{chunk_id}` kiểm tra raw SHA-256, parse lại, định vị đúng structural path/table row và so `source_text_hash`. Kết quả là `VERIFIED`, `INVALID_RAW_HASH`, `INVALID_SOURCE_LOCATOR` hoặc `SOURCE_UNAVAILABLE`.

## Immutable manifest

Mỗi snapshot lưu dataset ID, snapshot version, UTC creation time, source URLs, filing IDs, raw/normalized hashes, parser/chunker/ingestion version, embedding model (NULL trong Milestone B), chunk counts, document counts, index generation, failed/partial lists và reproduction commands.

Snapshot version bắt nguồn từ hash của trạng thái corpus. Nếu trạng thái không đổi, lệnh manifest trả đúng file cũ; không tạo manifest trùng. Manifest hash bao phủ toàn bộ payload trừ chính trường hash.

## Dữ liệu fixture và dữ liệu thật

Fixture `tests/fixtures/sec/filing_sample.htm` là tài liệu synthetic, chỉ dùng kiểm thử parser/table/idempotency; không được gọi là SEC filing thật. Fixture submissions cũng synthetic và không phải corpus nghiên cứu.

Ngày 2026-10-24 chưa có filing thật nào được tải vì `SEC_USER_AGENT` hợp lệ chưa được cấu hình. Do đó chưa có live dataset manifest và Milestone B tổng thể là **PARTIAL**.

## Trả lời ngắn cho giảng viên

1. EDGAR cung cấp lịch sử filing, primary documents và API XBRL facts.
2. CIK định danh công ty; accession định danh từng filing/phiên bản.
3. HTML/iXBRL có hierarchy, anchors và machine-readable facts; PDF thiên về trang và tọa độ. Không thể giả page cho HTML.
4. Bảng phải giữ hàng/cột, unit, period và footnote để số liệu không mất ngữ cảnh.
5. Hash chứng minh bytes; version chứng minh code/parser nào tạo artifact.
6. Chunk chứa document version và locator, rồi được xác minh ngược đến raw disclosure.
7. Amendment được lưu như filing riêng và liên kết `amendment_of`.
8. Source URL + accession + raw hash + locator verification là bằng chứng dữ liệu thật; trong phiên này phần live vẫn bị chặn nên chưa tuyên bố VERIFIED.
