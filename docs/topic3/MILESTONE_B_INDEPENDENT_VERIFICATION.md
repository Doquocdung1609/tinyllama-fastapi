# Milestone B — Finalization độc lập, 24/10/2026

**Kiến nghị: PARTIAL.** Đã sửa ngữ cảnh bảng chính, chạy Chat/RAG, OCR và media thật, kiểm chứng SEC độc lập. Còn các layout tables chưa phân loại chắc chắn, live amendment chưa chạy và API historical revision chưa đầy đủ. Owner quyết định nghiệm thu; không triển khai C.

## 1. Git và repository

Repository: https://github.com/Doquocdung1609/tinyllama-fastapi.git

Nhánh `codex/topic3-milestone-b-independent-verification-20261024`; base `de01cbd4157fcbfdcac3201aed7e2f89ba3b3044`; commit mã đã kiểm chứng `ae7cc77dc21883519c2be11843f8016c635c8315`. HEAD tài liệu/giao cuối xem `git log -3` và mục Delivery bổ sung.

Giữ nguyên `7a6bbd9593f229cbb14ba9e49b6a24aa0c1083f4`, `4572c67c665c3b0a0ad433ef2bce8b4178e29bad`. Đã chạy status, branch -vv, remote -v, fetch origin --prune, log --all --oneline --decorate -30, branch -a, show --stat hai commit và cat-file baseline. Working tree ban đầu sạch. Sau user tự login gh, fetch thành công: remote B vẫn de01cbd, local ahead 2/behind 0 trước sửa. A/B có đủ, A nằm trong ancestry. Không phát hiện divergence; không thể biết contributor đang có sửa đổi chưa push.

PR #1 vẫn OPEN/Draft từ feat/topic3-financial-hybrid-retrieval vào main. Không merge. Reference repo AI_agent_Demo không truy cập được với tài khoản hiện hành (GraphQL repository not found); không dùng code từ đó.

environment_handoff.zip đã giải nén riêng tại Downloads/environment_handoff_extracted và đọc inventory. Owner HEAD de01cbd được xác nhận; ZIP không chuyển corpus/vectors owner.

## 2. Tái lập môi trường

Windows 11, RAM ~15,2 GiB, RTX 3050 Laptop 4 GB, driver 610.64; Python 3.12.10 giữ nguyên .venv thay vì xóa để ép 3.13.2. Ollama thực tế 0.40.10; owner 0.30.10. Đã sửa user PATH. Torch 2.6.0+cu124 / torchvision 0.21.0+cu124, CUDA 12.4 available, GPU name khớp. Cài requirements-image, imageio[ffmpeg] và dependency kiểm chứng. pip check không có dependency hỏng.

Tesseract 5.4.0.20240606, eng/vie tessdata_best + osd. FFmpeg từ binary imageio-ffmpeg; local paths và khác biệt package có trong COLLABORATOR_ENVIRONMENT_REPORT.md. SEC contact chỉ nằm trong .env private.

Models thực tế và digest so owner đều khớp:

- `llama3:latest`: `365c0bd3c000a25d28ddbf732fe1c6add414de7275464c4e4d1c3b5fcb5d8ad1`, 4,661,224,676 bytes.
- `nomic-embed-text:latest`: `0a109f422b47e3a30ba2b10eca18548e944e8a23073ee3f3e947efcf3c45e59f`, 274,302,450 bytes.
- `qwen2.5:3b`: `357c53fb659c5076de1d65ccb0b397446227b71a42be9d1603d46168015c9e4b`, 1,929,912,432 bytes.

Không tuyên bố hai môi trường giống byte-for-byte. Không tự tải Jina/reranker vì có tên trong config.

## 3. Tích hợp ứng dụng thật

Direct Ollama generate trả giải thích có nghĩa về balance sheet; embedding trả một vector số 768 chiều. start_genai.ps1 -NoBrowser báo READY. /health, /docs, /qdrant/status, /system/status, corpus filings, evidence và Streamlit /_stcore/health đều HTTP 200.

PDF fixture một trang qua /documents/upload → READY → embedding thật → Qdrant collection independent_verification 768 chiều. RAG trả đúng “finance a solar-powered logistics hub”, trích rag-financial-verification.pdf trang 1. Cả 5 checks integration đều true; lỗi input chat/upload/document trả 422/415/404. Đây là fixture tổng hợp, không giả làm SEC.

Một mẫu /chat giải thích balance sheet đã nhầm sang income statement và trộn ngôn ngữ. Functional inference không chứng minh độ chính xác tư vấn tài chính. Không chỉnh QA/prompt ngoài scope để che kết quả này. Chưa thao tác mọi tab qua trình duyệt; UI operational được giới hạn ở startup và health.

## 4. Sửa kỹ thuật Milestone B

- Schema/parser giữ statement/table title, multi-row TD/TH headers, spans, physical row indices, row-period groups, unit context, iXBRL sign/scale, footnotes và locators.
- Không trộn tr của bảng lồng vào bảng cha; body th không bị nuốt thành header. Bảng tiếp diễn chỉ nhận context khi continued rõ hoặc phần giới thiệu ngay trước gọi đúng chủ đề và layout tương ứng. % không bị gán scale triệu USD.
- Chunk có công ty/CIK/accession/form, title, cột/kỳ, units, numeric attributes, footnotes, source URL và locator; bỏ hàng hoàn toàn trống/header-only, không tạo phantom evidence.
- Parser/chunker cuối sec-html-v5 / financial-structure-v5. Derived paths, chunk identity và manifest generation có version; không reuse stale parser/chunker. Historical raw/derived/manifests giữ nguyên.
- Final status thống nhất structured/chunk/registry. Evidence kiểm normalized hash và toàn bộ chunk/context tái dựng, không chỉ hash dòng số.
- Tests mới cho các behavior trên, migration giữ bytes cũ, restart, tamper context và cả hai amendment forms. Không sửa thuật toán retrieval/Milestone C.

## 5. Bằng chứng khoa học

Nguồn: https://www.sec.gov/Archives/edgar/data/320193/000032019326000020/aapl-20260627.htm. Retrieved UTC 2026-10-24T14:56:54.544431+00:00; HTTP 200, 1.018.317 bytes. Apple Inc., CIK 0000320193, AAPL, 10-Q, accession 0000320193-26-000020; filing 2026-07-31, report 2026-06-27, FY 2026/Q3 explicit iXBRL. 10 metadata checks độc lập đều true.

Raw SHA256 `d2fa42061d517dc6fd528f32a09197553f0d70214405f6fc09497829c95e8b8c`. Normalized `94d101e71b2dd31d69f324a20a49459c3f733070041736950ffc40e6c3460e7e`. Dataset `collaborator-v5-final`, snapshot `v1-84fb27e8d817077c`, manifest `f192ac227f38c9fb18f707b8ecc2ba87546db81beae7c33a1a24b78959b32bd0`.

40 tables / 4.762 source cells đối chiếu BeautifulSoup, 0 mismatches; 28 value/period/unit cases PASS. Balance/income/cash/EPS được kiểm riêng. 566 chunks; 12 provenance samples VERIFIED. Lặp ingest giữ 1 filing/1 raw/566 IDs và cùng manifest. Recovery/amendments là fixture-only, được ghi rõ.

620 chunks và snapshot owner là lịch sử, không ép repaired output giữ 620. Root v3/v4 là thử nghiệm trước v5 và được giữ riêng; không ghi đè bằng chứng cũ.

| Gate | Status | Bằng chứng / giới hạn |
|---|---|---|
| B1 Correct Git baseline | VERIFIED | Auth/fetch thành công; remote B de01cbd; hai commit cũ giữ nguyên, không divergence |
| B2 Environment | VERIFIED | pip check, CUDA/OCR/FFmpeg, 3 model digest đúng; phiên bản khác owner được ghi rõ |
| B3 Ollama LLM | VERIFIED | Direct generate có nghĩa, /chat sinh thật; không phải kiểm chứng mọi câu tài chính |
| B4 Embedding | VERIFIED | Vector số 768 chiều, Qdrant dimension 768 |
| B5 API/UI | VERIFIED | Health/docs/Streamlit health HTTP 200, startup READY; chưa kiểm mọi tương tác trình duyệt |
| B6 Qdrant/RAG | VERIFIED | PDF fixture qua upload/embedding/Qdrant riêng, RAG đúng ý và file/trang 1 |
| B7 Real SEC | VERIFIED | HTTP 200, hash gốc trùng owner; 10 checks metadata từ submissions/iXBRL |
| B8 Financial tables | PARTIAL | 28 giá trị/kỳ/scale PASS; 4 layout tables thiếu header; cả filing PARTIAL_EXTRACTION |
| B9 Provenance | VERIFIED | 12 mẫu + API VERIFIED; test raw/normalized/context tamper |
| B10 Idempotency | VERIFIED | 1 filing, 1 raw, 566 IDs và manifest giữ nguyên |
| B11 Recovery | VERIFIED | Checkpoint/retry/new registry instances; fixture kiểm soát, không kill production |
| B12 Amendments | PARTIAL | Cả 10-K/A và 10-Q/A fixture đạt; live amendment NOT_TESTED |
| B13 Regression | VERIFIED | 142 PASS, 0 FAIL, 0 SKIP, 2 warnings, bật real media và OCR |
| B14 Draft PR | PENDING_DELIVERY | Cập nhật URL sau push; không merge |

## 6. Regression

**142 passed, 0 failed, 0 skipped, 2 warnings in 27.95s**, RUN_REAL_MEDIA_TESTS=1. Tiny-SD PNG không trống, SAPI WAV có frames, FFmpeg motion MP4 đúng mode, OCR vie+eng giữ các ô numeric. SVD diffusion không chạy trên GPU 4 GB; không gọi motion demo là diffusion.

Lần dùng tessdata_fast: 139 PASS / 1 FAIL / 0 SKIP / 2 warnings, scan trang thứ hai nhận sai 180. Đổi sang official tessdata_best, test đơn lẻ đạt rồi chạy lại full suite. Không bỏ test, không đổi failure thành skip, không sửa code OCR ngoài scope.

Warnings: Starlette/httpx TestClient deprecation; Diffusers/NumPy __array__(copy=False). Pip cũng cảnh báo thư mục tạm ~il không xóa được khi thay Pillow đang được process cũ nạp; pip check và full suite sau cài đều đạt. Compileall và git diff --check đạt.

Live integration là script riêng với 5 checks, không cộng vào 142 pytest cases. Logs/JSON/pip freeze nằm trong tmp/milestone_b_verification (ignored).

## 7. Giao GitHub

Minh-1512 tự login device flow; gh setup-git dùng credential store, không token trong remote. Target là codex/topic3-milestone-b-sec-corpus để không trộn lại A/B vào main. Các commit cũ giữ nguyên. PR URL/SHAs cuối bổ sung ở mục Delivery sau push. Không force-push, không merge.

## 8. Nghiệm thu

**PARTIAL**. Bảng trọng yếu và pipeline thật đã có bằng chứng, nhưng toàn filing còn PARTIAL_EXTRACTION do 4 layout tables; live amendment và historical chunk lookup chưa đầy đủ. Không tuyên bố production readiness. Owner quyết định có chấp nhận giới hạn hay cần mở coverage trước nghiệm thu B.

## 9. Vấn đề còn lại

1. Layout tables indices 5/9/11/38 thiếu header rõ (cover/legal/TOC/exhibit). Không đoán và không gắn cả filing READY giả.
2. Chỉ một issuer/filing thật; không chứng minh mọi footnote/financial table của mọi issuer chính xác.
3. Historical JSON/JSONL/manifests còn nguyên, nhưng registry/API chỉ phục vụ revision active, chưa dispatch parser lịch sử/tìm mọi chunk cũ.
4. 10-K/A, 10-Q/A và recovery kiểm qua fixtures; chưa live amendment, kill OS hoặc lỗi vector index thật.
5. RateLimiter theo client, chưa điều phối aggregate nhiều process. SEC chạy bounded/tuần tự, không bypass.
6. Khác Python/Ollama/package versions; Jina/reranker/SVD checkpoint chưa được chứng minh có. Không có 1.947 vectors lịch sử owner.
7. Functional Chat không bảo đảm đúng thuật ngữ tài chính; cần grounded evaluation khi có milestone phù hợp.

## 10. Sẵn sàng Milestone C

Pilot core financial tables có thể hỗ trợ nghiên cứu sau owner chấp nhận/khép giới hạn B. Đề xuất persistent BM25, incremental index, snapshot/generation lexical+dense, metadata prefilter, RRF, table-aware context, P50/P95/throughput/CPU/RAM và restart consistency. Không triển khai C; không nêu cải thiện chưa đo. 0,926 queries/s trên 5.000 synthetic chunks là số lịch sử, không phải benchmark SEC mới.

## Tái lập

```powershell
# Python hiện tại 3.12.10; giữ .venv hoạt động.
.\.venv\Scripts\python.exe -m pip install -r requirements-verification.txt
.\.venv\Scripts\python.exe -m pip install torch==2.6.0 torchvision==0.21.0 --index-url https://download.pytorch.org/whl/cu124
.\.venv\Scripts\python.exe -m pip install -r requirements-image.txt 'imageio[ffmpeg]'
$env:Path += ';' + [Environment]::GetEnvironmentVariable('Path', 'User')
$env:FINANCIAL_CORPUS_DIR='./financial_corpus/collaborator-v5-final'
$env:FINANCIAL_REGISTRY_DB='./financial_corpus/collaborator-v5-final/registry.sqlite3'
$env:SEC_TIMEOUT_SECONDS='20'
$env:SEC_MAX_RETRIES='1'
.\.venv\Scripts\python.exe scripts/sec_live_smoke.py --cik 320193 --limit 1 --dataset-id collaborator-v5-final
.\.venv\Scripts\python.exe scripts/verify_milestone_b.py --root financial_corpus/collaborator-v5-final --dataset-id collaborator-v5-final --output tmp/milestone_b_verification/audit-v5-final.json
# Truyền profile này khi KHỞI ĐỘNG API; không đổi được profile của process đã chạy.
$env:QDRANT_PATH='./qdrant_data/independent-verification'
$env:QDRANT_COLLECTION='independent_verification'
$env:CONVERSATION_DB='./data/independent-verification.sqlite3'
$env:UPLOAD_DIR='./uploads/independent-verification'
$env:PROCESSED_DIR='./processed/independent-verification'
.\start_genai.ps1 -NoBrowser
.\.venv\Scripts\python.exe scripts/verify_local_integration.py --collection independent_verification --output tmp/milestone_b_verification/integration-final.json
$env:TESSDATA_DIR='./tools/downloads/tessdata_best'
$env:RUN_REAL_MEDIA_TESTS='1'
$env:TTS_OUTPUT_DIR='./audio/milestone-b-verification'
$env:IMAGE_OUTPUT_DIR='./images/milestone-b-verification'
$env:VIDEO_OUTPUT_DIR='./videos/milestone-b-verification'
.\.venv\Scripts\python.exe -m pytest -q -rs
.\.venv\Scripts\python.exe -m compileall -q app scripts main.py client.py streamlit_app.py
.\.venv\Scripts\python.exe -m pip check
```



---

# Bằng chứng lịch sử của lượt trước (không thay thế kết quả mới)

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
