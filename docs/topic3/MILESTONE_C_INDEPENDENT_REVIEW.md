# Milestone C — independent review

> Hardening closure 2026-10-25: các gap auth, single-owner, retention, provenance cache, Windows path và stable errors dưới đây đã được triển khai/test. Một race stale cleanup-plan và temp-artifact failure được phát hiện thêm và sửa có regression. Kết luận cập nhật nằm ở `FINAL_ACCEPTANCE_REPORT.md`; phần còn lại của file giữ nguyên làm audit trail của review ban đầu.

**Kết luận:** `READY_FOR_OWNER_REVIEW` cho phạm vi pilot cục bộ, sau hai sửa chữa có regression test. PR #8 phải tiếp tục là **Draft**, không merge trong đợt review này và không bắt đầu Milestone D.

## Phạm vi và danh tính bản review

- Repository: `Doquocdung1609/tinyllama-fastapi`; PR #8 được GitHub xác nhận `open=true`, `draft=true`, `merged=false`.
- HEAD đầu vào: `4ce6176ce0208303dc966813738acefc4879d021`, đúng expected HEAD.
- Base: `c84c060d1bbf507b01badb8073f22cbf53b9b7ec`.
- Review đọc toàn bộ diff và trực tiếp kiểm tra `lexical.py`, `service.py`, `corpus.py`, API, UI, benchmark và tests. Không lấy completion report làm bằng chứng duy nhất.
- Corpus/index lịch sử C không còn trong checkout bàn giao. Review đã tái tạo cô lập đúng ba SEC source, không sửa/xóa dữ liệu lịch sử của chủ repo. Apple raw/normalized hashes, snapshot generation, 566 chunk; Tesla original/amendment identities, lineage, 1.609/597 chunk đều khớp evidence B. Manifest hash mới khác vì `created_at` nằm trong manifest hash; chi tiết này được ghi là giới hạn reproducibility, không bị che giấu.

## Kết quả code review

| Hạng mục | Kết quả độc lập | Nhận xét |
|---|---|---|
| SQLite BM25 | VERIFIED | Postings/TF được lưu một lần; filtered `N`, average length và `df` được tính trong đúng scope; positive-IDF Okapi BM25 `k1=1.5`, `b=0.75`; deterministic tie-break theo chunk ID. Ranking khớp formula-matched baseline trên cả 14 query. |
| Persistent lifecycle | VERIFIED_WITH_LIMITS | Restart đọc lại SQLite/Qdrant không rebuild; postings và vector cache tái sử dụng. Không có GC/retention cap tự động. |
| Atomic publication | VERIFIED | Qdrant collection mới được hoàn tất/validate trước khi SQLite `active` switch trong `BEGIN IMMEDIATE`; failure không đổi active generation. Không tuyên bố distributed transaction. |
| Consistency/rollback | VERIFIED | Count, generation payload, dimension và full chunk-ID set được kiểm tra; retained generation queryable và rollback được. Payload hash chỉ được kiểm trên hit trả về, không full-scan lúc publish. |
| Incremental semantics | VERIFIED_WITH_LIMITS | Changed revision chỉ embed text mới; unchanged postings/vectors được reuse. Mỗi generation vẫn ghi full membership/frequencies và full Qdrant collection: không phải O(delta). |
| Qdrant synchronization | VERIFIED | Collection name generation-bound, payload có full generation, count/ID validation ngăn mixed generation. Local Qdrant chỉ an toàn với một owning process. |
| RRF/dedup | VERIFIED | Mỗi channel dedup, score đúng `sum(1/(60+rank))`, tie-break deterministic sau khi candidate lists đã hình thành. Equal weighting có failure chất lượng, không phải lỗi công thức. |
| Metadata filters | VERIFIED_WITH_POLICY_GAP | CIK/ticker/form/year/period/filing ID được prefilter ở cả SQLite và Qdrant. Không có policy “original vs amended” mặc định; caller phải truyền `form_type`/`filing_ids`. |
| Provenance | VERIFIED_BUT_EXPENSIVE | Raw/structured/chunks hashes, normalized parse và regenerated chunk context được kiểm. Mỗi request vẫn rehash/reparse/rechunk whole source. |
| Input validation | PARTIAL | Query/mode/range/dataset/hash/CIK/form được bound; SQL parameterized. Item strings trong `filing_ids`/`expected_manifests`, ticker và fiscal period chưa canonicalize chặt. Build/activate endpoints không có auth/rate limit. |
| Legacy compatibility | VERIFIED | Full suite với real media và owner environment đạt 184 PASS sau cả hai regression tests mới. |
| Resource/concurrency | VERIFIED_WITH_LIMITS | WAL/transactions và concurrent query/build trong một process hoạt động. Multi-worker/process trên cùng Qdrant directory không được hỗ trợ/enforce. Disk tăng theo collection retained. |

## Lỗi đã sửa có mục tiêu

### 1. Accepted concurrent build bị bỏ rơi ở `BUILDING`

`FinancialIndex.build()` trước đây dùng non-blocking lock trước khối `try`. Khi API đã trả `202 BUILD_QUEUED` cho build thứ hai trong lúc build đầu đang chạy, background task thứ hai ném `BUILD_ALREADY_RUNNING`; `fail()` không chạy và generation nằm `BUILDING` vô thời hạn.

Sửa chữa: serialize accepted builds bằng blocking in-process lock. Regression test giữ lock, gửi build thứ hai trong thread, chứng minh request chờ, hoàn tất `READY`, active pointer đổi đúng và generation cũ vẫn retained. CAS `base_active` tiếp tục chặn một build stale publish qua một active generation đã đổi.

### 2. Nomic retrieval contract bị vi phạm

Documents và queries trước đây đều embed raw text. Model card Nomic ghi task prefix là bắt buộc cho asymmetric retrieval: document dùng `search_document:` và query dùng `search_query:`. Sửa chữa tách `embed_documents()`/`embed_query()`, đưa prefix policy vào model identity để generation/cache cũ không bị trộn, và thêm regression test kiểm JSON gửi thật tới Ollama.

Đây là sửa contract của model, không phải tuning `k`, weight hoặc candidate limit trên 14 query cũ. Baseline cũ vẫn giữ nguyên. Bộ dev/held-out mới được freeze trước khi chạy generation đã sửa.

## Rủi ro/giới hạn còn mở

1. **Mutating endpoints không có auth/rate limit.** `/financial-index/build` cho phép `force_rebuild`; `/activate` đổi active generation. Nếu API không chỉ bind trên máy tin cậy, đây là đường gây CPU/disk exhaustion hoặc rollback ngoài ý muốn. Pilot local chấp nhận được; production không chấp nhận.
2. **Một process sở hữu local Qdrant.** Code chỉ có thread locks. `uvicorn --workers >1`, CLI chạy cùng lúc API hoặc process khác mở cùng directory vẫn có thể fail/lock. Cần enforce một worker hoặc chuyển Qdrant server mode.
3. **Không có garbage collection.** Một generation cùng 822 chunk tăng khoảng 9,0 MB trong rerun; ba generation với hai embedding identities chiếm 58,35 MiB. `force_rebuild` có thể tăng disk vô hạn.
4. **Dense tie/candidate nondeterminism.** Nhiều chunk ngắn giống hệt (“Apple Inc.”) có cosine bằng nhau. Code chỉ sort ID sau khi Qdrant đã cắt top-160; tie group cắt ở boundary có thể làm một số irrelevant IDs thay đổi. Aggregate relevance metrics đã ổn định trong reproduction, nhưng exact dense ID list không hoàn toàn reproducible.
5. **Manifest cross-root không content-reproducible.** `created_at` nằm trong `manifest_hash`; cùng raw/normalized/chunk generation ở root mới sinh manifest hash và index generation C khác. Ngoài ra generation signature không chứa root, nên relocate một READY index tới root mới cần explicit rebuild.
6. **Provenance TOCTOU/performance.** Rehash bảo vệ tamper tốt, nhưng full reparse/rechunk mỗi query tiêu tốn 0,47–1,65 giây/source. Cache an toàn được đề xuất trong latency report.
7. **Windows long-path.** Isolated corpus dưới checkout dài đã fail khi ghi staging path; cùng thao tác ở `C:\mscr` thành công. Không có guard/preflight cho effective path length.
8. **Error disclosure.** Một số HTTP 503/409 trả `str(exc)` có thể lộ absolute local paths. Chỉ phù hợp môi trường dev tin cậy.
9. **Original/amended semantics.** Dataset có thể chứa cả 10-K và 10-K/A cùng period. Không có default precedence; UI chỉ cho form filter, không giải thích amendment policy.

## Thí nghiệm reliability có giới hạn

- Cold rebuild 822 chunk: 809 unique embeddings; 220,44 giây sau prefix/IPv4, Python peak 272,27 MiB; Ollama RAM/VRAM không nằm trong con số này.
- Controlled failure sau một batch: new generation chuyển `FAILED`, old generation vẫn active.
- Close/reopen rồi resume: 0 new postings, 0 new embeddings, 822 upserts, hoàn tất 13,81 giây.
- Sáu BM25 queries chạy trong lúc resume đều đọc old generation; không có SQLite/Qdrant error.
- Hai collections retained đều đúng 822 point; old/new hybrid IDs bằng nhau khi content giống nhau.
- Rollback đưa active pointer về generation gốc; restart/idempotent build không rebuild.
- Test là exception/restart có kiểm soát, không phải power-loss/corrupt-disk test.

## Regression và lệnh thực tế

```powershell
# Môi trường sạch, chưa nạp owner .env / real media
.\.venv-review\Scripts\python.exe -m pytest -q
# Trước sửa: 178 passed, 3 skipped, 1 failed, 1 warning
# Fail: test_rag_defaults kỳ vọng 0.55 nhưng default code là 0.7.

.\.venv-review\Scripts\python.exe -m pytest tests/test_persistent_financial_index.py tests/test_financial_search.py tests/test_financial_ingestion.py -q
# 37 passed, 1 warning trước hai test mới
# 39 passed, 1 warning sau hai repairs

.\.venv-review\Scripts\python.exe -m pytest tests/test_persistent_financial_index.py -q
# 15 passed, 1 warning sau concurrency + prefix repairs

# Nạp đúng owner .env, model local, RUN_REAL_MEDIA_TESTS=1
# IMAGE_MODEL và TESSDATA_DIR được resolve thành absolute paths trong owner checkout.
<owner-venv-python> -m pytest -q
# 184 passed, 2 warnings in 40.11s
```

Con số reported `182 PASS` được reconciled: cùng suite/environment của owner cộng đúng hai regression tests mới cho `184 PASS`. Một lần chạy trung gian cấu hình nhầm `IMAGE_MODEL` thành path tương đối trong checkout Git-LFS-only cho `183 passed, 1 failed`; chạy lại với model path tuyệt đối qua `184 PASS`, xác nhận đó là lỗi harness, không phải regression. Hai warning là Starlette/httpx deprecation và diffusers/numpy deprecation, không phải test failure.

## Readiness

`READY_FOR_OWNER_REVIEW` nghĩa là code/data evidence đủ để chủ repo review trong phạm vi pilot local; **không đồng nghĩa production-ready hoặc merge-ready**. PR #8 phải giữ Draft. Trước production cần auth/rate limit, single-owner enforcement hoặc Qdrant server, retention/GC, bounded provenance cache, issuer/document-held-out evaluation và power-loss testing.

