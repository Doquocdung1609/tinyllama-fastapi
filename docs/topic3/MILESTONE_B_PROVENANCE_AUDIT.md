# Audit provenance — bằng chứng mẫu độc lập

Dataset `independent-20261024-final`, accession `0000320193-26-000020`, snapshot `v1-4fdd48e73cfb3930`.

Raw hash được tính lại trực tiếp từ file bytes: `d2fa42061d517dc6fd528f32a09197553f0d70214405f6fc09497829c95e8b8c`. Normalized hash tính lại từ structured filing: `5e21f8e6d25a18734ed49f887258b6e64af5b297ec03124fdb0312f5ef412f12`. Không sử dụng hash chủ dự án thay cho phép đo.

Chọn 6 text chunks và 6 table chunks trải đều theo thứ tự corpus. Cả 12 trả VERIFIED khi giải locator về raw, kiểm source_text_hash và parent metadata. Đây là mẫu, không phải audit nội dung mọi chunk. Chuỗi lưu: chunk_id → filing_id → CIK/accession → source_url → structural path/table row → original disclosure. HTML không có PDF page giả.

| Loại | Chunk ID | Structural path |
|---|---|---|
| text | `fin_0a234ffacef2efd2f351efa1a350ff6a` | `/document[1]/html[1]/body[1]/div[1]` |
| text | `fin_b8a14d9fad261b3d67c3abbce2628c18` | `/document[1]/html[1]/body[1]/div[77]` |
| text | `fin_d7281ba81000921c29833c07b391da2c` | `/document[1]/html[1]/body[1]/ix:continuation[5]/div[4]` |
| text | `fin_6cb440271b047f67fcf1cc420485f277` | `/document[1]/html[1]/body[1]/div[159]` |
| text | `fin_a7bff96e0999b4e7c734d25746c23fba` | `/document[1]/html[1]/body[1]/div[242]` |
| text | `fin_c978a592e62572939b5579e77a29bcbf` | `/document[1]/html[1]/body[1]/div[294]` |
| table | `fin_851b0d0d3400c46033024594df4028f1` | `/document[1]/html[1]/body[1]/div[4]/table[1]` |
| table | `fin_48b54e159b611a4015bfb85f5f63462a` | `/document[1]/html[1]/body[1]/div[62]/table[1]` |
| table | `fin_b529f071681d535e6f7da7353c75731a` | `/document[1]/html[1]/body[1]/div[89]/table[1]` |
| table | `fin_4d1e427a2bbcc8266dcc5ef63e6efb07` | `/document[1]/html[1]/body[1]/ix:continuation[2]/ix:nonnumeric[1]/div[2]/table[1]` |
| table | `fin_bf49c068ccdf5e11394a4e10ad7e9202` | `/document[1]/html[1]/body[1]/ix:continuation[6]/ix:nonnumeric[1]/div[2]/table[1]` |
| table | `fin_3c2956bca27a3b126f7f169e7b641776` | `/document[1]/html[1]/body[1]/ix:nonnumeric[3]/ix:continuation[1]/div[3]/table[1]` |

Tests offline cũng sửa raw giả lập để chứng minh INVALID_RAW_HASH; chunk IDs khác khi raw version khác. Chưa thử thay đổi nguồn SEC thật, không sửa dữ liệu chủ dự án. Locator bảng hiện row_index theo bảng rows đã tách header; chưa chứng minh semantic period trong chunk. VERIFIED provenance không đồng nghĩa bảng đủ ý nghĩa hoặc retrieval chính xác.

Giới hạn migration: root mới dùng parser/chunker v2. Chưa force reprocess root v1 vì derived paths theo raw hash có thể thay thế structured/chunk files cùng raw; cần quản lý phiên bản derived artifacts trước khi chạy trên corpus lịch sử.
