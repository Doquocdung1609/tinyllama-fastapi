# Financial Metadata Schema

## Định danh

`filing_id = sec:{10-digit CIK}:{canonical accession number}`.

- CIK định danh pháp nhân tại SEC và là khóa công ty chính.
- Accession number định danh filing cụ thể và giữ cả phiên bản amendment.
- Ticker chỉ là thuộc tính tìm kiếm vì có thể đổi theo thời gian.
- `10-K/A` hoặc `10-Q/A` là filing riêng và có `amendment_of`; không ghi đè bản gốc.

## FilingMetadata

| Trường | Nguồn/quy tắc |
|---|---|
| company_name | submissions JSON; không được rỗng |
| cik | chỉ chữ số, chuẩn hóa 10 ký tự |
| ticker | input/source mapping hoặc NULL có lý do |
| form_type | một trong 10-K, 10-Q và hai amendment |
| accession_number | 18 chữ số, định dạng `##########-##-######` |
| filing_date/report_date | submissions JSON hoặc NULL |
| fiscal_year/fiscal_period | explicit iXBRL facts hoặc NULL có lý do |
| primary_document/source_url | archive filename và canonical SEC URL |
| retrieved_at | UTC tại response download |
| source_type | `SEC_EDGAR` |
| raw_content_hash | SHA-256 exact bytes |
| normalized_content_hash | SHA-256 canonical structured text/table stream |
| parser_version/ingestion_version | version code xử lý |
| document_status | state machine hiện tại |
| amendment_of | filing ID gốc nếu tìm được |
| response_metadata | HTTP status, ETag, Last-Modified, type, length, final URL |

Mọi trường chưa xác định được giữ NULL và giải thích trong `unknown_reasons`.

## SourceLocation

Locator hỗ trợ `section`, `html_anchor`, `structural_path`, `table_id`, row/column, text offsets và tùy chọn PDF page/bbox. SEC HTML chỉ điền locator thực sự tồn tại; `pdf_page` và `bbox` luôn NULL, không tạo số trang giả.

```json
{
  "section": "Financial Statements",
  "structural_path": "/document[1]/html[1]/body[1]/table[1]",
  "table_id": "table_<stable-hash>",
  "row_index": 1
}
```

## Chunk identity

`document_version = filing_id@raw_content_hash`.

Chunk ID là SHA-256 rút gọn của document version, kind, canonical source locator và chunker version. Vì vậy rerun cùng bytes tạo cùng ID; cùng accession nhưng raw bytes thay đổi tạo chunk IDs mới. Mỗi chunk mang accession, URL, hash, parser/ingestion version và source locator.
