# Bằng chứng live SEC độc lập — 24/10/2026

Baseline: `de01cbd4157fcbfdcac3201aed7e2f89ba3b3044`; mã kiểm thử: `7a6bbd9593f229cbb14ba9e49b6a24aa0c1083f4`.

Phân biệt: các kết quả 620 chunks/hash trong master prompt là báo cáo của chủ dự án. Các giá trị bên dưới được đo lại bằng mạng trực tiếp trên máy cộng tác; không kiểm tra được corpus/manifest gốc vì không được chuyển giao.

| Thuộc tính | Đo độc lập |
|---|---|
| Retrieved UTC | 2026-10-24T13:59:51.889039+00:00 |
| Công ty / CIK / ticker | Apple Inc. / 0000320193 / AAPL |
| Form / accession | 10-Q / 0000320193-26-000020 |
| Filing date / report date | 2026-07-31 / 2026-06-27 |
| Fiscal year / period | 2026 / Q3, explicit dei facts trong raw |
| HTTP / bytes | 200 / 1018317 |
| Dataset | independent-20261024-final |
| Filing status | PARTIAL_EXTRACTION |
| Chunks / raw snapshots trong final root | 620 / 1 |
| Snapshot | v1-4fdd48e73cfb3930 |
| Parser / chunker / ingestion | sec-html-v2 / financial-structure-v2 / topic3-milestone-b-v1 |
| Raw SHA256 | `d2fa42061d517dc6fd528f32a09197553f0d70214405f6fc09497829c95e8b8c` |
| Normalized SHA256 | `5e21f8e6d25a18734ed49f887258b6e64af5b297ec03124fdb0312f5ef412f12` |
| Manifest SHA256 | `b66d24f907c4c926f472187cbebc1ab9a305bdd901dbf1649dda99edfdbb1f53` |

Nguồn chính: https://www.sec.gov/Archives/edgar/data/320193/000032019326000020/aapl-20260627.htm

Metadata được đối chiếu bằng một request giới hạn tới https://data.sec.gov/submissions/CIK0000320193.json: company_name, cik, ticker membership, form, accession, filing date, report date, primary_document đều khớp. FY/Q3 lấy từ `dei:DocumentFiscalYearFocus` và `dei:DocumentFiscalPeriodFocus` bằng BeautifulSoup độc lập trên bytes raw. Không suy FY từ report date.

Đã tải filing hai lần tổng cộng vào hai root tách biệt trong phiên xác minh: root đầu kiểm bản sửa text, root `*-final` sau sửa đánh dấu extraction chưa đầy đủ. Không ghi đè corpus gốc; không coi hai lần thử là một dataset gốc đã được xác minh. Sau đó audit lặp lại dùng raw cục bộ, không tải thêm. Job COMPLETED nghĩa ingestion đã chạy hết; filing PARTIAL_EXTRACTION vẫn là không đủ chất lượng bảng.

Normalized hash khác báo cáo v1 của chủ dự án vì sửa thứ tự inline text; raw hash trùng. Manifest khác vì dataset/version/parser/chunker khác, không gán snapshot mới thành snapshot cũ.

Yêu cầu SEC đối chiếu ngày thực hiện: https://www.sec.gov/about/developer-resources — tổng không quá 10 requests/giây/người, dùng công cụ có định danh và chỉ tải dữ liệu cần thiết. Cấu hình 6 req/s và các thử nghiệm tuần tự, không bypass 403. Định dạng contact hợp lệ, giá trị riêng tư không ghi ở đây.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-verification.txt
.\.venv\Scripts\python.exe -m pip check
$env:FINANCIAL_CORPUS_DIR='./financial_corpus/independent-20261024-final'
$env:FINANCIAL_REGISTRY_DB='./financial_corpus/independent-20261024-final/registry.sqlite3'
$env:SEC_TIMEOUT_SECONDS='15'
$env:SEC_MAX_RETRIES='0'
.\.venv\Scripts\python.exe scripts/sec_live_smoke.py --cik 320193 --limit 1 --dataset-id independent-20261024-final
.\.venv\Scripts\python.exe scripts/verify_milestone_b.py --root financial_corpus/independent-20261024-final --dataset-id independent-20261024-final --output tmp/milestone_b_verification/audit-final.json
.\.venv\Scripts\python.exe -m pytest tests/test_sec_connector.py tests/test_sec_parser.py tests/test_financial_ingestion.py tests/test_financial_corpus_api.py -q
.\.venv\Scripts\python.exe -m pytest -q -rs
.\.venv\Scripts\python.exe -m compileall -q app scripts main.py client.py streamlit_app.py
```

