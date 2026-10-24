# Table Extraction Contract

## Mục tiêu

Parser không flatten toàn bộ bảng thành một paragraph. Mỗi `FinancialTable` giữ:

- stable table ID, section, caption và structural path;
- grid `columns` + `rows`;
- từng cell với row/column, rowspan/colspan, header flag;
- iXBRL `unitRef` và `contextRef` nếu có;
- reporting periods tìm từ header;
- table footer/footnotes và raw text/hash;
- `OK` hoặc `PARTIAL_EXTRACTION`.

Rowspan/colspan được mở rộng vào grid nhưng cell gốc vẫn giữ span. Dấu âm ngoặc, percentage, dấu phân cách và missing marker được giữ nguyên text; parser không sửa số theo suy đoán.

## Table-aware chunk

Mỗi data row tạo một chunk với table ID, section, caption, columns, row text, units và periods. `source_text_hash` băm chính row disclosure, còn locator trỏ table + row. Điều này cho phép tìm theo row mà vẫn dựng lại quan hệ cột.

## Điều kiện PARTIAL

Đánh dấu partial khi span không hợp lệ, grid rỗng/không đủ cột hoặc cấu trúc không thể khôi phục chắc chắn. Raw table text và tọa độ cấu trúc vẫn được giữ để kiểm tra. Không tự suy diễn merged headers phức tạp hoặc đơn vị không có trong nguồn.

## Kết quả fixture thực đo

Trên `filing_sample.htm` (1.205 bytes): 1 bảng, 13 cells, 4 data rows, header 2023/2022, periods 2022/2023, units `USDm` và `millions`; 4 table chunks; không warning. Giá trị `1,250`, `(300)`, `12.5%` và footnote được giữ nguyên. Đây là fixture synthetic, không phải chứng nhận độ chính xác trên mọi SEC filing.

Thời gian một lần đo trên máy hiện tại: parse 3,203 ms và chunk 1,689 ms. Con số này chỉ mô tả fixture nhỏ, không suy rộng thành throughput production.


## Final-gap status semantics and quality diagnostic

READY is pipeline completion without parser warnings, not a financial-completeness certificate. PARTIAL_EXTRACTION and manifest partial-document membership remain conservative across all table purposes. No automatic purpose classifier was added.

GET /financial-corpus/quality/{filing_id} is a read-only diagnostic: existing document_status, per-table warnings/context flags and numeric-fact counts, plus financial_completeness=NOT_ASSESSED. It neither verifies provenance nor changes filing/manifest/derived artifacts. Financial scope must be supported by independent source review. Manual, raw-hash-bound findings for the four Apple tables are in MILESTONE_B_TABLE_GAP_CLASSIFICATION.json; full evidence is in MILESTONE_B_FINAL_GAP_AUDIT.md.
