# P0 — RAG evidence selection and context budget repair

Ngày kiểm tra: 2026-10-10  
API thật: `http://127.0.0.1:8000/rag/query`  
Model sinh câu trả lời: `qwen2.5:3b`  
Document ID: `aedb60bc088e4242970a43da1e897bde`  
Tham số: `top_k=5`, `score_threshold=0.55`

## Kết luận

P0 đã PASS trên suy luận thật. Câu hỏi `đổi mới tài chính có mấy loại` trả về đủ hai hệ phân loại:

- Theo loại hình đổi mới trong tài chính: **3 loại**, trang 155.
- Theo chức năng đối với hệ thống tài chính: **8 loại**, trang 156.

Hai citation được giải quyết từ đúng E1 và E2, không dùng citation fallback. `missing_counts_final=[]`.

## Root cause chính xác

### 1. Từ hỏi “mấy” bị coi là từ nội dung hiếm

Trong phiên bản lỗi, `_STOP_WORDS` chưa có `mấy`/`nhiêu` (đường xử lý cũ bắt đầu ở `app/services/rag_service.py` dòng 22–33 của HEAD gốc). Chunk 269 trang 73 chứa câu “không mấy coi trọng ... đổi mới”, nên được lexical rank 1 với `lexical_score=0.511927`, cao hơn các chunk trả lời thật (`0.497091`).

Baseline ghi nhận rerank:

| Rank | Trang/chunk | Lexical score | Vai trò thực tế |
|---:|---|---:|---|
| 1 | 73 / 269 | 0.511927 | Nhiễu do từ “mấy” |
| 2 | 154 / 573 | 0.497091 | Dẫn nhập vùng liên quan |
| 3–5 | 155 / 577–579 | 0.497091 | Hệ phân loại 3 loại |
| 6–7 | 156 / 581–582 | 0.497091 | Hệ phân loại 8 loại |

### 2. Bộ chọn context neo vào rank 1 rồi ưu tiên vùng liền kề

Đường xử lý cũ lấy `results[:top_k]`, gọi neighbor expansion trước khi có phân bổ ngân sách bằng chứng trực tiếp, rồi cắt context theo ký tự (HEAD gốc: `app/services/rag_service.py` dòng 251–283). Ở baseline thực tế, page-anchor chọn trang 73 và loại các ứng viên 154–155 với lý do dạng văn bản `distant generic match; adjacent context preferred`.

Kết quả: E1 là chunk 269 trang 73; E2–E8 là bảy chunk liền kề 270–276, trang 73–75. Một hit sai và neighbor của nó dùng 1.623/1.800 token. Không có chunk trang 155–156 trong prompt dù chúng đã có trong rerank.

### 3. Candidate pool bị giới hạn bởi top-k trước selection

Page 156 đứng hạng 6–7 nên không vào `results` top 5. Selector không thể chọn hệ phân loại thứ hai dù reranker đã tìm thấy nó.

### 4. ID và citation chưa được kiểm chứng theo context thật

Prompt cũ không gán E-ID ổn định theo thứ tự block được đưa vào prompt. Citation do model viết chưa được đối chiếu với chunk đã bao gồm; khi model từ chối, fallback gắn nguồn hạng đầu trang 73, làm câu trả lời vừa sai vừa dẫn nguồn sai.

## Thay đổi mã nguồn có mục tiêu

Tất cả thay đổi nằm trong pipeline tổng quát; không có câu trả lời, page 155/156 hay ngoại lệ theo query được hardcode trong `app/`.

1. **Lọc từ hỏi và nhận diện phát biểu phân loại có số lượng**
   - `mấy`, `nhiêu` được loại khỏi lexical terms: `app/services/rag_service.py:22`.
   - `_classification_count_match`: `app/services/rag_service.py:185`.
   - Chỉ boost khi “đổi mới tài chính” là chủ thể được phân loại, tránh câu chỉ nhắc thuật ngữ trong một quan hệ khác.

2. **Direct evidence luôn được chọn trước neighbor**
   - `_select_prompt_context`: `app/services/rag_service.py:331`.
   - Tổng ngân sách 1.800 token; direct 75% = 1.350; reserve adjacent 450.
   - Tối đa 6 direct và 2 adjacent; deduplicate theo nội dung; ưu tiên đa dạng trang/facet.
   - Neighbor chỉ được đề xuất sau khi direct đã khóa, chỉ trong phạm vi chênh tối đa một trang và không được đẩy direct ra khỏi prompt.

3. **Candidate pool lớn hơn top-k trả về**
   - Diagnostic/evidence window và `evidence_pool`: `app/services/rag_service.py:691–713`.
   - API vẫn giữ `retrieved_chunks` theo top-k, nhưng selector có thể xét tối đa `max(10, top_k*2)` ứng viên vượt ngưỡng. Vì vậy page 156 không còn bị mất chỉ vì đứng hạng 6–7 trước rerank cấu trúc.

4. **Diagnostics máy đọc được cho mọi ứng viên bị loại**
   - `BELOW_SCORE_THRESHOLD`, `UNSUPPORTED_NUMERIC_ANCHOR`, `LOW_DIRECT_RELEVANCE`, `DUPLICATE_CONTENT`, `DIRECT_LIMIT`, `DIRECT_BUDGET_RESERVED`, `ADJACENT_LIMIT`, `TOTAL_TOKEN_BUDGET`.
   - Mỗi record có `exclusion_code`, `exclusion_reason`, `exclusion_stage` và số token/limit liên quan khi áp dụng.
   - Ghép diagnostics retrieval và context selection tại `app/services/rag_service.py:826`; số lượng trước selection tại dòng 849.

5. **E-ID chính xác và citation validation**
   - Gán `E1..En` trực tiếp theo `included_prompt_context`: `app/services/rag_service.py:466`.
   - `_resolve_evidence_citations`: `app/services/rag_service.py:230`.
   - Chỉ giải quyết ID tồn tại; báo `invalid_evidence_ids`, `citation_missing`, `citation_fallback_added`, `resolved_citations` với filename/page/chunk ID thật.
   - Chuẩn hóa cả `[E1]` và bare `E1` từ model nhỏ trước khi đối chiếu.

6. **Kiểm tra độ đầy đủ của câu trả lời cho nhiều hệ phân loại**
   - Extract fact từ chính evidence đã đưa vào prompt: `app/services/rag_service.py:287`.
   - Kiểm tra số phải đi cùng từ loại/nhóm, tránh nhầm số thứ tự item: dòng 318.
   - Nếu thiếu một hệ phân loại, chạy prompt sửa tập trung tối đa hai lần và chỉ dừng khi đủ các count fact: `app/services/rag_service.py:743–788`.

7. **RAG Debug UI**
   - Hiển thị candidate pool, E-ID, budget, exclusion code, citation và generation validation: `client.py:195–202`.

## Before / after final prompts

Toàn bộ prompt được lưu nguyên văn:

- Before: `reports/rag_prompt_before.txt`
- After — prompt evidence ban đầu: `reports/rag_prompt_after_initial.txt`
- After — prompt sửa cuối thực sự gửi Qwen: `reports/rag_prompt_after_final.txt`

Tóm tắt block header:

**Before (7.430 ký tự)**

```text
[E1 | Bằng chứng trực tiếp: ..., trang 73, chunk ...-00269]
[E2 | Nguồn liền kề: ..., trang 73, chunk ...-00270]
...
[E8 | Nguồn liền kề: ..., trang 75, chunk ...-00276]
```

**After — evidence prompt (5.860 ký tự)**

```text
[E1 | Bằng chứng trực tiếp | TÍN HIỆU: PHÂN_LOẠI_CÓ_SỐ_LƯỢNG: ..., trang 155, chunk ...-00578]
[E2 | Bằng chứng trực tiếp | TÍN HIỆU: PHÂN_LOẠI_CÓ_SỐ_LƯỢNG: ..., trang 156, chunk ...-00581]
[E3 | Bằng chứng trực tiếp | TÍN HIỆU: PHÂN_LOẠI_CÓ_SỐ_LƯỢNG: ..., trang 156, chunk ...-00582]
[E4 | Nguồn liền kề: ..., trang 156, chunk ...-00583]
[E5 | Nguồn liền kề: ..., trang 155, chunk ...-00579]
```

**After — focused final prompt** chứa đúng hai fact đã kiểm chứng từ E1/E2:

```text
[E1] Tiêu chí: loại hình đổi mới trong tài chính. Số lượng: 3 loại.
[E2] Tiêu chí: chức năng đối với hệ thống tài chính. Số lượng: 8 loại.
```

## Số liệu before / after cho query lỗi

| Chỉ số | Before | After cuối |
|---|---:|---:|
| Retrieved exact-page precision | 3/5 = 60% | 3/3 = 100% |
| Coverage hai hệ phân loại trong retrieved top-k | 1/2 = 50% | 2/2 = 100% |
| Precision block trong prompt theo trang 155–156 | 0/8 = 0% | 5/5 = 100% |
| Coverage hai hệ phân loại trong prompt | 0/2 = 0% | 2/2 = 100% |
| Direct / adjacent blocks | 1 / 7 | 3 / 2 |
| Context token estimate | 1.623 | 1.131 |
| Answer correctness | FAIL | PASS |
| Citation đúng evidence | FAIL, fallback trang 73 | PASS, E1 trang 155 + E2 trang 156 |
| API `total_ms` | 18.824,6 ms | 14.372,8 ms |
| Wall time lần chạy cuối | không lưu trong baseline JSON | 14.425,9 ms |

Lần chạy cuối có `BELOW_SCORE_THRESHOLD=7`, `ADJACENT_LIMIT=3`, `missing_counts_final=[]`, `citation_valid=true`, `citation_fallback_added=false`.

Một lần đo trước đó kéo dài khoảng 4.386 giây do máy bị pause/sleep giữa hai log Ollama; đây là outlier hệ thống, vẫn được giữ trong `reports/rag_ambiguous_after.json` và không dùng làm latency đại diện.

## Kết quả API hồi quy thật

File: `reports/rag_p0_regression.csv`, chi tiết đầy đủ trong `reports/rag_p0_regression_details.json`.

| Case | Kết quả | Trang retrieved | `total_ms` |
|---|---|---|---:|
| P0-AMBIGUOUS | PASS: 3 loại + 8 loại, citation 155 + 156 | 155,156,156 | 9.407,5 |
| RAG-Q01 | PASS: đủ sản phẩm, chuyển đổi rủi ro, quy trình; citation 155 | 155,156,156,158,155 | 16.878,8 |
| RAG-Q15 | PASS: từ chối câu dự báo Bitcoin ngoài tài liệu | rỗng | 2.458,5 |
| RAG-Q16 | PASS: từ chối câu Tổng thống 2026 ngoài tài liệu | rỗng | 2.433,3 |

Tổng hợp 4 case:

- Recall@k: **100%**
- MRR: **100%**
- Evidence precision: **95%**
- Evidence-in-prompt coverage: **100%**
- Answer correctness: **100%**
- Citation accuracy trên câu có hỗ trợ: **100%**
- Refusal recall / precision: **100% / 100%**
- Thời gian API trung bình: **7.794,525 ms**

Q01 vẫn PASS theo ba expected elements và citation. Qwen 3B đôi lúc chèn một từ ngoại ngữ nhỏ trong phần diễn giải dài (`atau`); việc này không làm sai ba mục hay nguồn và nằm ngoài lỗi P0 selection/budget.

## Unit, integration và bảo toàn hệ thống

- Toàn bộ unit/API test: **32 passed, 3 skipped**, 1 deprecation warning, 1,37 giây.
- Các test P0 mới: `tests/test_rag_hybrid.py:173–282`.
- Real media integration: **3 passed**, 1 warning, 36,11 giây.
  - Tiny-SD sinh PNG thật và ảnh không trắng.
  - TTS thật.
  - FFmpeg/video demo integration.
- Qdrant vẫn online, dimension **768**.
- Active document vẫn có **971 chunks/vectors**. Collection hiện có 1.947 vectors vì workspace đã chứa hai bản 971-chunk của cùng PDF và một tài liệu 5-chunk; bản sửa này không re-index, xóa hoặc thay vector nào.
- Tiny-SD status: **READY**, model `./models/tiny-sd`.

## Runtime smoke và reload UI

`scripts/smoke_test.py` PASS trên dịch vụ đang chạy:

- FastAPI `/health`: HTTP 200, 20,5 ms.
- Streamlit `/`: HTTP 200, 165,9 ms.
- Streamlit `/_stcore/health`: HTTP 200, body `ok`.
- HTML có Streamlit bundle và `<div id="root">`; response dài 6.463 byte.
- Đủ 8 tab theo contract.
- Ollama, Qdrant và embedding đều online; image status `READY`.

Kiểm tra ảnh chụp trình duyệt tự động không thực hiện được vì Computer Use helper báo `failed to write kernel assets: The system cannot find the path specified (os error 3)` sau một lần reset/retry. Log Streamlit không có exception của ứng dụng; chỉ có một `ConnectionResetError [WinError 10054]` khi client đóng kết nối, thường xảy ra lúc reload/ngắt WebSocket và server vẫn tiếp tục trả HTTP 200.

## Artifacts

- Baseline đầy đủ: `reports/rag_ambiguous_baseline.json`
- Kết quả cuối đầy đủ: `reports/rag_ambiguous_after_final.json`
- Regression summary: `reports/rag_p0_regression.summary.json`
- Regression CSV: `reports/rag_p0_regression.csv`
- Regression raw responses: `reports/rag_p0_regression_details.json`
- Test cases: `reports/rag_p0_eval_cases.json`

