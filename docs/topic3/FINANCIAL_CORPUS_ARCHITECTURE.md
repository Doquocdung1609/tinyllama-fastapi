# Kiến trúc Financial Corpus — Milestone B

## Phạm vi và trạng thái

**IMPLEMENTED:** một pipeline staging độc lập cho SEC EDGAR, chạy CPU, không ghi vào collection Qdrant `knowledgebase` và không thay đổi luồng PDF hiện hữu.

**PARTIAL:** pipeline đã được kiểm chứng end-to-end bằng fixture HTML/iXBRL cố định, nhưng chưa được xác minh với nguồn SEC trực tiếp vì `SEC_USER_AGENT` chưa có tên ứng dụng và email liên hệ hợp lệ.

## Luồng dữ liệu

```text
SEC submissions JSON
  -> discovery (CIK + accession)
  -> bounded download (.incoming)
  -> immutable raw/{cik}/{accession}/{sha256}/file
  -> HTML/iXBRL validation
  -> structured text + table model
  -> version-aware stable chunks
  -> SQLite registry + JSON staging index
  -> immutable dataset manifest
  -> source-evidence verification
```

Các thành phần chính:

- `sec_client.py`: discovery/download, User-Agent bắt buộc, giới hạn tốc độ, retry/backoff, conditional request và allowlist host SEC.
- `html_parser.py`: parser HTML/iXBRL CPU-only, giữ hierarchy, bảng và locator.
- `chunker.py`: chunk theo phần tử cấu trúc và từng hàng bảng.
- `registry.py`: registry SQLite WAL cho filing, chunk, job và manifest.
- `pipeline.py`: state machine, raw snapshot bất biến, resume, amendment và lineage.
- `financial_corpus.py`: REST API cho discovery, job, status, manifest và evidence.

## Isolation contract

Financial corpus dùng `financial_corpus/` và mặc định `financial_corpus/registry.sqlite3`. Staging index chỉ chứa JSON metadata/chunk IDs và trường `qdrant_collection: null`. Không có đoạn code Milestone B nào gọi upsert/delete collection production. Việc đưa corpus tài chính vào lexical/vector index thuộc Milestone C và cần phê duyệt riêng.

## Ranh giới tài nguyên

- Không dùng GPU, Ollama hoặc embedding trong ingestion.
- Download streaming từng khối 1 MiB, giới hạn mặc định 100 MiB/filing.
- Batch discovery tối đa 200 filing/lệnh API; CLI ingest mặc định 3.
- Parser hiện dựng cây HTML trong RAM; filing rất lớn cần benchmark trước khi mở rộng.
- Không tải model hoặc corpus tự động khi khởi động ứng dụng.

## API/CLI

```powershell
python scripts/financial_corpus.py discover --cik 320193 --forms 10-K --limit 1 --dry-run
python scripts/financial_corpus.py ingest --dataset-id sec-pilot --cik 320193 --ticker AAPL --limit 1
python scripts/financial_corpus.py status --dataset-id sec-pilot
python scripts/financial_corpus.py resume --job-id <job-id>
python scripts/financial_corpus.py manifest --dataset-id sec-pilot
python scripts/financial_corpus.py evidence --chunk-id <chunk-id>
```

REST tương ứng nằm dưới `/financial-corpus`. Backend đang chạy phải được restart để nạp router mới; không cần thay đổi Streamlit.

## Giới hạn đã biết

- Chưa parse toàn bộ taxonomy/contexts XBRL; Milestone B chỉ đọc fiscal focus và giữ `unitRef`/`contextRef` tại cell.
- Không suy diễn fiscal year từ report date.
- Không tạo page number/bbox cho HTML.
- Chưa đưa staging chunks vào BM25/Qdrant; đây là chủ ý để bảo vệ 1.947 vectors cũ.
- Registry hiện quản lý một active dataset membership cho mỗi filing ID; manifest cũ vẫn bất biến, nhưng multi-snapshot membership đồng thời cần schema ở Milestone C.
