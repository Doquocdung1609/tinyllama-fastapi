# Ingestion State Machine

## Trạng thái document

```text
DISCOVERED
 -> DOWNLOADING
 -> DOWNLOADED
 -> VALIDATING
 -> PARSING
 -> CHUNKING
 -> STAGING
 -> READY | PARTIAL_EXTRACTION

Any active state -> FAILED
Process restart while active -> INTERRUPTED
```

`READY` chỉ được ghi sau raw validation, structured/chunk atomic writes, staging metadata và SQLite chunk transaction. Có parser warning thì trạng thái cuối là `PARTIAL_EXTRACTION`, không che giấu chất lượng thấp.

## Job checkpoint và resume

Job lưu `filing_ids`, `next_index`, `completed`, `failed` sau từng filing trong SQLite và JSON checkpoint. Khi startup, filing/job đang active chuyển sang `INTERRUPTED`. `resume` bỏ qua completed, tiếp tục từ checkpoint và thử lại các item trong `failed`.

Test đã xác nhận:

- dừng sau filing đầu, resume hoàn tất filing thứ hai;
- process-recovery đổi đúng active status thành `INTERRUPTED`;
- lỗi kết nối một lần tạo `COMPLETED_WITH_ERRORS`, lần chạy tiếp theo thử lại thành `COMPLETED` mà không tạo filing/chunk trùng.

## Idempotency

Nếu filing đã READY/PARTIAL, raw path còn tồn tại và SHA-256 khớp, rerun không gọi download và trả `idempotent_reuse: true`. `force=True` mới tải lại. Exact same hash tái sử dụng raw snapshot; raw hash khác tạo processed version mới.

SQLite primary/unique keys bảo vệ filing, chunk, job và manifest. Chunk replacement cho active filing xảy ra trong transaction. Production Qdrant không tham gia nên không có trạng thái half-indexed với collection học tập.

## Failure semantics

- 403/404: không retry tự động.
- 429/5xx/connection: retry hữu hạn.
- non-HTML primary document: FAILED.
- raw missing/tampered lúc evidence: SOURCE_UNAVAILABLE/INVALID_RAW_HASH.
- locator không còn khớp sau parser change: INVALID_SOURCE_LOCATOR.
- manifest liệt kê failed và partial documents rõ ràng.
