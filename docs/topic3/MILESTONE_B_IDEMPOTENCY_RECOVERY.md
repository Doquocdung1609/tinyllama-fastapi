# Idempotency, recovery và amendments

## Live corpus, lặp không phá dữ liệu

Dataset `independent-20261024-final`; không cleanup trước hoặc sau để tạo kết quả giả.

| Chỉ số | Trước | Sau |
|---|---|---|
| Filing records | 1 | 1 |
| Raw snapshot trong final root | 1 | 1 |
| Chunk records | 620 | 620 |
| IDs | 620 duy nhất | Tập IDs giống hệt |
| Manifest hash | `b66d24f907c4c926f472187cbebc1ab9a305bdd901dbf1649dda99edfdbb1f53` | Giữ nguyên |
| Snapshot | `v1-4fdd48e73cfb3930` | Giữ nguyên |

`ingest_one` trả idempotent_reuse=true, không cần network client; raw, normalized hashes và manifest kiểm lại. Staging chỉ là metadata/chunks JSON, không có vector index Qdrant cho financial corpus. Không tuyên bố 620 chunks = 620 vectors.

## Recovery: fixture, chưa thử kill live process

`test_job_checkpoint_resume_and_recovery`: stop_after=1, checkpoint giữ next_index, resume hoàn tất; trạng thái PARSING/RUNNING phục hồi INTERRUPTED. `test_failed_job_item_is_retried_without_duplicate_rows`: lỗi mạng giả một lần, lần retry hoàn tất không trùng filing/chunks.

Test mới `test_checkpoint_resumes_in_new_pipeline_and_registry_instances`: tạo lại pipeline và registry từ SQLite đã lưu; chỉ tải filing còn lại; raw filing đã xong giữ bytes, IDs cũ vẫn tồn tại, không trùng chunk IDs. Đây là restart đối tượng qua persistent DB, không giả nhận đã kill/reboot hệ điều hành.

## Amendment: fixture-only

10-K/A có accession riêng, filing_id riêng và amendment_of trỏ base; raw snapshots cũ giữ nguyên khi source bytes đổi. Amendment thật và consistency staging/vector dưới lỗi thực tế NOT_TESTED.

Chạy `python -m pytest tests/test_financial_ingestion.py -q` trong .venv; chi tiết lệnh full và số PASS tại báo cáo tổng. Không can thiệp corpus/Qdrant chủ dự án.
