# Xác minh độc lập Milestone B — 24/10/2026

## Kết luận: PARTIAL

Dữ liệu Apple thật được tải trực tiếp từ SEC, hash gốc khớp bàn giao; kiểm thử offline và khởi động ứng dụng đạt. Chưa nghiệm thu B vì bảng tài chính mất ánh xạ tiêu đề/kỳ trong chunks, thiếu xác minh chức năng phụ thuộc model và chưa giao được nhánh/PR qua GitHub.

## 1. Trạng thái repository

- Remote: https://github.com/Doquocdung1609/tinyllama-fastapi.git
- Ban đầu: `main`, HEAD `ceaa8ac`, working tree sạch.
- Nhánh xác minh: `codex/topic3-milestone-b-independent-verification-20261024`.
- Baseline cục bộ từ remote-tracking ref `origin/codex/topic3-milestone-b-sec-corpus`: `de01cbd4157fcbfdcac3201aed7e2f89ba3b3044`.
- Commit sửa mã đã kiểm thử: `7a6bbd9593f229cbb14ba9e49b6a24aa0c1083f4`. Commit tài liệu tiếp theo xem `git log -2`.
- Các lệnh `git cat-file -t` trả về `commit` cho `47dc39439eaa5e174c2d08113e9e6d759cf2fdd9`, `4f41bcf0364e7d5485b409d2143383cc99554f78`, `bca1584ea7a936bbc8d36c039fe15f916f5c1ea6`.
- Milestone A có trong ancestry (`87360aafb024632824c12a2f0e66be6600ad573f`); B đầy đủ gồm 7 module ingestion, API, scripts, tests và docs.
- `git status`, `git branch -vv`, `git remote -v`, `git log --all --oneline --decorate -30`, `git branch -a`, `git worktree list` đã chạy trước khi sửa mã. Các remote-tracking refs có sẵn là bằng chứng cục bộ, không chứng minh trạng thái remote hiện tại.
- `git fetch origin --prune` không hoàn tất xác thực; lần thử không tương tác báo `fatal: Cannot prompt because user interactivity has been disabled.` và `fatal: unable to get password from user`.
- `git ls-remote --heads origin` cũng không xác thực được. GitHub API repo và pulls trả HTTP 404 khi không đăng nhập. Không kết luận repo bị xóa, branch chưa push, hoặc PR đã merge từ các lỗi này.
- Chưa xác nhận ahead/behind/diverged, PR #1, PR B hay người đóng góp đang hoạt động. Không ghi đè nhánh gốc.
- File ZIP đã giải nén vào `C:/Users/Admin/Downloads/btl thầy hiếu/Topic3_Handoff_extracted`. Chỉ có `.env` và hai hướng dẫn, không có Git bundle/corpus. `.env` được sao chép vào repo và được Git ignore; không đưa contact vào báo cáo.

## 2. Môi trường

- OS: Windows-11-10.0.26300-SP0; Python 3.12.10 trong `.venv`. Máy không có Python 3.13; phiên bản 3.12 chạy được bộ kiểm thử.
- Cài tất cả `requirements.txt` và `beautifulsoup4` để đối chiếu DOM độc lập; `pip check`: `No broken requirements found.`
- Phiên bản chính: fastapi 0.162.0, streamlit 1.66.1, pydantic 2.14.1, requests 2.34.2, qdrant-client 1.20.0, pytest 8.4.2, beautifulsoup4 4.15.0.
- `.env` thực sự được `app/config.py` nạp bằng `load_dotenv(ROOT_DIR / '.env')`. User-Agent vượt kiểm tra định dạng; HTTP SEC 200. Không xác minh quyền sở hữu email bằng gửi thư.
- Không có corpus/SQLite/Qdrant gốc trong handoff. Các corpus mới nằm dưới `financial_corpus/independent-*`; không gọi chúng là snapshot gốc của chủ dự án.
- Ollama không có trong PATH, cổng 11434 đóng; model chat/embedding chưa có bằng chứng khả dụng. Tesseract và FFmpeg không có trong PATH. PyTorch/media dependencies chưa cài; không tự tải model lớn theo giới hạn master prompt.
- FastAPI `http://127.0.0.1:8000/health` và `/docs`: HTTP 200. Streamlit `http://127.0.0.1:8501/_stcore/health`: HTTP 200. Đây là kiểm tra khởi động, chưa chứng minh thao tác mọi tab qua trình duyệt.
- `/system/status`: Qdrant local online ở collection `independent_verification`, 0 vectors; Ollama/embedding offline. Không dùng `knowledgebase`. QDRANT_PATH=`./qdrant_data/independent-verification`; CONVERSATION_DB=`./data/independent-verification.sqlite3`; upload/processed cũng dùng thư mục con riêng.

## 3. Ma trận xác minh

| Gate | Trạng thái | Bằng chứng | Phần còn thiếu |
|---|---|---|---|
| B1 Git/môi trường | PARTIAL | Baseline đầy đủ cục bộ; dependencies và env loader hoạt động | GitHub chưa xác thực; không kiểm chứng contributor/PR hiện hành |
| B2 SEC connector | PARTIAL | HTTP 200 thật; 6 req/s cấu hình, live giới hạn 1 req/s ở kiểm tra metadata; offline retry/conditional/403/404/redirect/size | Giới hạn rate theo client, không điều phối tổng nhiều process; không gây 429/5xx thật |
| B3 Metadata | VERIFIED | 8 trường khớp SEC submissions; FY 2026/Q3 khớp iXBRL trong raw | Chỉ một filing; không suy rộng |
| B4 Bảng tài chính | PARTIAL | 40 bảng, 4.762 ô, không sai khác text/span với BeautifulSoup; kiểm tra balance/income/cash flow/EPS | Tiêu đề đa tầng, kỳ, scale ngoài bảng và footnotes chưa gắn đầy đủ vào chunks |
| B5 Provenance | VERIFIED | Hash raw/normalized; 12 chunks mẫu (6 narrative, 6 table) truy ngược VERIFIED; tests phát hiện raw tamper | Đây là truy vết trong snapshot, không phải chất lượng retrieval |
| B6 Idempotency | VERIFIED | Lặp ingestion tại cùng root: 620 IDs không đổi, 1 raw snapshot, cùng manifest, 1 filing | Chưa indexing vector thật |
| B7 Recovery | PARTIAL | Fault fixtures, checkpoint, retry và khởi tạo lại registry/pipeline đều đạt | Chưa kill tiến trình live hay thử sự cố Qdrant thật |
| B8 Amendments | PARTIAL | Fixture 10-K/A riêng, liên kết base, version hash và historical raw được giữ | Amendment SEC thật NOT_TESTED |
| B9 Legacy | PARTIAL | Regression đạt; API/UI khởi động; local Qdrant online | Chat/RAG model, OCR, real media và UI interactions NOT_TESTED |
| B10 Regression | VERIFIED | 123 PASS, 0 FAIL, 4 SKIP, 1 warning; compileall và pip check đạt | Skips là tính năng phụ thuộc runtime, không xem là PASS |

## 4. Kiểm thử và giới hạn

Targeted: **28 passed, 0 failed, 1 warning**. Full: **123 passed, 0 failed, 4 skipped, 1 warning** (5,77 giây). Ba skip media do chưa bật `RUN_REAL_MEDIA_TESTS=1`; một skip OCR vì Tesseract chưa cài. Warning: Starlette TestClient dùng httpx bị deprecated, gợi ý httpx2; chưa sửa dependency không liên quan để làm mất cảnh báo.

Lần chạy sớm trước khi pip hoàn tất báo thiếu pytest/pydantic; đã chạy lại sau khi cài xong. Không dùng các lỗi môi trường tạm thời đó làm kết quả nghiệm thu.

## 5. Thay đổi mã

- `html_parser.py`: giữ thứ tự text và inline nodes, tránh đảo nhãn/dấu ngoặc của số âm; đánh dấu PARTIAL_EXTRACTION khi bảng có nội dung nhưng inferred headers trống.
- `sec_client.py`: tự theo chuyển hướng tối đa 5 lần, kiểm HTTPS/host trước khi gửi request tới mỗi đích; mỗi hop tuân limiter.
- Parser/chunker nâng `sec-html-v2` / `financial-structure-v2` để phân biệt nội dung/IDs với v1. Ingestion version giữ nguyên.
- Thêm 9 cases (tính parametrized): inline text, bảng thiếu headers, redirects hợp lệ/không hợp lệ, 403/404, size limit và restart qua instance mới.
- Script `scripts/verify_milestone_b.py` đối chiếu raw DOM bằng BeautifulSoup, text/spans từng ô, hashes, 12 provenance mẫu, manifest và idempotency; `requirements-verification.txt` khai báo dependency kiểm chứng.
- Ignore artifacts kiểm tra; không commit `.env`, raw corpus, SQLite, vectors, media hoặc logs.

## 6. Giao Git

Đã commit mã cục bộ. Push `git -c credential.interactive=false push origin HEAD:refs/heads/codex/topic3-milestone-b-independent-verification-20261024` bị chặn bởi thiếu xác thực. Draft PR: **chưa tạo**; đề xuất target `codex/topic3-milestone-b-sec-corpus` sau khi xác minh remote hiện hành. Không mở PR lẫn A/B vào main. Nội dung PR chuẩn bị tại `MILESTONE_B_DRAFT_PR.md`. Không merge, không force-push.

## 7. Quyết định nghiệm thu

**PARTIAL**. Raw source đáng tin, một filing được tái lập trực tiếp và kiểm chứng định lượng; B4, B7–B9 và giao Git chưa đủ bằng chứng nghiệm thu. Chủ dự án quyết định cuối cùng.

## 8. Vấn đề còn lại

1. Apple dùng các hàng `<td>` trống rồi headers đa tầng; parser hiện lấy hàng đầu làm columns, để reporting_periods rỗng. Số trong chunk thiếu nhãn kỳ, không đủ cho tính toán tự động đáng tin.
2. Đơn vị scale/footnote ở ngoài table chưa liên kết đầy đủ; nhiều layout tables được coi là financial tables. Không khẳng định table semantics đã VERIFIED chỉ từ text/spans khớp.
3. Reprocessing cùng raw nhưng parser mới: đường dẫn derived artifacts dựa raw hash, còn idempotent reuse chưa buộc kiểm phiên bản parser/chunker. Đã dùng root mới; chưa chạy force trên corpus cũ. Cần thiết kế migration/versioned derived paths trước khi tái xử lý corpus chủ dự án.
4. Evidence verifier kiểm nguồn raw và locator; chưa đánh giá relevance, faithfulness của câu trả lời hay throughput.
5. RateLimiter hiện theo client; nhiều client/process có thể vượt aggregate SEC rate nếu vận hành đồng thời.
6. Cần đăng nhập GitHub để refresh baseline, kiểm tra PR/contributor, push và tạo Draft PR.

## 9. Milestone C

Chưa đủ điều kiện dùng corpus hiện tại làm bằng chứng hoàn chỉnh cho nghiên cứu retrieval tài chính. Chỉ đề xuất persistent BM25, incremental generation, snapshot-consistent lexical/dense, metadata filtering, RRF và resource/latency measurements trong NEXT_MILESTONE_PLAN.md; không triển khai C.

## Tái lập

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

Bằng chứng chi tiết: LIVE_SEC_EVIDENCE, TABLE_VALIDATION, PROVENANCE_AUDIT, IDEMPOTENCY_RECOVERY cùng thư mục. Logs/audit JSON và `pip freeze` đầy đủ giữ cục bộ tại `tmp/milestone_b_verification/`, được ignore. Không đưa giá trị contact vào Git.
