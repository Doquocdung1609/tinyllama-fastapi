# GenAI Learning Studio

Ứng dụng học tập GenAI chạy local bằng FastAPI và Streamlit. Hệ thống giữ tám tab: Dashboard, Chat với Ollama, Talk to Documents / RAG, Chunk Explorer, English Script → Audio, Text → Image, Image → Video và System / GPU.

## Thành phần

- LLM local qua Ollama; mặc định `qwen2.5:3b`, có thể chọn `llama3:latest` trong Chat/RAG.
- Embedding `nomic-embed-text`, Qdrant local, hybrid dense + lexical rank fusion.
- Hội thoại PDF nhiều lượt được lưu bằng SQLite; mỗi chat có phạm vi tài liệu riêng và được phục hồi sau reload.
- OCR CPU cục bộ bằng Tesseract `vie+eng`, kèm tọa độ từ, confidence và tái tạo bảng scan có kiểm tra số.
- Phép tính tài chính dùng công thức xác định, giữ đầu vào, đơn vị, nguồn và kết quả kiểm chứng.
- RAG debug hiển thị từng giai đoạn từ candidate đến evidence thực sự vào prompt.
- TTS local bằng Windows SAPI/pyttsx3.
- Text-to-image bằng `./models/tiny-sd`.
- Stable Video Diffusion local-only có capability gate; FFmpeg motion demo là mode riêng, không phải generative video.

## Chạy ứng dụng

```powershell
cd C:\Users\Admin\Desktop\AI_thay_Hieu\tinyllama-fastapi
.\start_genai.ps1
```

Không tự mở browser:

```powershell
.\start_genai.ps1 -NoBrowser
```

Sau khi sẵn sàng:

- UI: http://127.0.0.1:8501
- API docs: http://127.0.0.1:8000/docs
- Health: http://127.0.0.1:8000/health
- Video capabilities: http://127.0.0.1:8000/video/capabilities

`start_genai.ps1` đọc model bắt buộc từ `.env`, kiểm Ollama, FastAPI và Streamlit trước khi báo READY.

## Thiết lập OCR local

Tesseract phải có `vie`, `eng` và `osd`. Cấu hình mẫu trong `.env.example`:

```dotenv
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
TESSDATA_DIR=.\tools\tessdata
```

Kiểm tra capability tại `GET /system/status` hoặc xem trạng thái xử lý của tài liệu. Trang native-text không chạy OCR; trang ảnh/ít chữ mới được render 300 DPI và OCR trên CPU.

## Talk to Documents

1. Mở tab **Talk to Documents** và upload một hoặc nhiều PDF.
2. Chờ trạng thái `READY` hoặc `PARTIAL`; tiến độ hiển thị các bước extraction, OCR, chunking, embedding và indexing thực tế.
3. Chọn tài liệu, tạo cuộc hội thoại, rồi hỏi bằng `st.chat_input`.
4. Nhấn nguồn dưới câu trả lời để xem đúng trang PDF và vùng bằng chứng.
5. Chuyển chat hoặc reload trình duyệt; query parameter `conversation` và lịch sử SQLite khôi phục phiên.

API hội thoại chính:

```text
POST   /conversations
GET    /conversations
GET    /conversations/{conversation_id}
PATCH  /conversations/{conversation_id}
DELETE /conversations/{conversation_id}
POST   /conversations/{conversation_id}/messages
GET    /conversations/{conversation_id}/messages
```

Ví dụ tạo chat và gửi follow-up:

```powershell
$chat = Invoke-RestMethod -Method Post http://127.0.0.1:8000/conversations `
  -ContentType application/json -Body '{"active_document_ids":["<document-id>"]}'
Invoke-RestMethod -Method Post "http://127.0.0.1:8000/conversations/$($chat.conversation_id)/messages" `
  -ContentType application/json -Body '{"content":"Doanh thu năm 2024 là bao nhiêu?"}'
Invoke-RestMethod -Method Post "http://127.0.0.1:8000/conversations/$($chat.conversation_id)/messages" `
  -ContentType application/json -Body '{"content":"So với năm trước tăng bao nhiêu phần trăm?"}'
```

## RAG đáng tin cậy

Pipeline:

```text
PDF → extract/clean/chunk → embedding/Qdrant
    → dense candidates + lexical candidates
    → weighted reciprocal rank fusion
    → evidence selection + adjacent context budget
    → grounded prompt → Ollama → validated citation
```

Response `/rag/query` có các trường debug:

- `retrieved_candidates`
- `reranked_candidates`
- `evidence_candidate_pool`
- `selected_evidence`
- `adjacent_context`
- `included_prompt_context`
- `excluded_chunks` cùng `exclusion_code`, `exclusion_reason`, `exclusion_stage`
- `evidence_selection` với direct/adjacent/total token budgets
- `supporting_sources`, `lexical_diagnostics`, `citation_validation`, `generation_validation`, `timings`

Query có thể chọn model:

```json
{
  "question": "Ba loại đổi mới tài chính căn cứ theo loại hình là gì?",
  "document_id": "aedb60bc088e4242970a43da1e897bde",
  "top_k": 5,
  "score_threshold": 0.55,
  "generate_answer": true,
  "model": "qwen2.5:3b"
}
```

## Benchmark

Chạy 30 câu thật qua FastAPI và Qdrant:

```powershell
.\.venv\Scripts\python.exe scripts\rag_live_benchmark.py `
  --document-id aedb60bc088e4242970a43da1e897bde `
  --output reports\rag_live_benchmark.csv `
  --details reports\rag_live_benchmark_details.json `
  --model qwen2.5:3b --cold-first
```

Tạo appendix ground truth từ processed PDF:

```powershell
.\.venv\Scripts\python.exe scripts\build_eval_evidence.py `
  --processed processed\aedb60bc088e4242970a43da1e897bde.json
```

So sánh generation Qwen và Llama bằng cùng prompt:

```powershell
.\.venv\Scripts\python.exe scripts\compare_llms.py `
  --document-id aedb60bc088e4242970a43da1e897bde
```

Kết quả xác nhận hiện tại:

- Multi-turn thật qua FastAPI: 12/12 PASS.
- P0 production: 4/4 PASS, Recall@8 100%, citation supported 100%, refusal recall 100%.
- Regression production: 5/5 câu đúng; citation theo page-window evaluator 4/5.
- OCR/financial/chart quan trọng: 8/8 PASS; clean Vietnamese CER 0,98%, clean English CER 1,07%, numeric scan 12/12 ô chính xác.
- Toàn bộ pytest: 55 passed, 3 skipped.

Xem `reports/final_product_acceptance.md`. Quyết định tổng thể là `PARTIAL` vì chưa có final holdout do bên ngoài niêm phong và chart ảnh tùy ý vẫn phụ thuộc nhãn OCR đọc được.

## Video

Mode SVD nhận ảnh, không nhận text prompt. UI chỉ hiện các điều khiển backend thực sự dùng: seed, frames, fps, motion bucket, noise augmentation và decode chunk size. Trên GTX 1650 Ti 4 GB + RAM 8 GB, SVD được báo `BLOCKED` và checkpoint không được tự tải.

Mode FFmpeg tạo hiệu ứng Ken Burns, luôn ghi rõ `ken_burns_motion_demo_not_diffusion`.

Xem `reports/video_feasibility.md` và `reports/video_pipeline_explained.md`.

## Kiểm thử

```powershell
.\.venv\Scripts\python.exe -m pytest -q
$env:TESSERACT_CMD="C:\Program Files\Tesseract-OCR\tesseract.exe"
.\.venv\Scripts\python.exe scripts\conversation_api_benchmark.py --api http://127.0.0.1:8000
.\.venv\Scripts\python.exe scripts\final_product_validation.py --api http://127.0.0.1:8000
$env:RUN_REAL_MEDIA_TESTS="1"
.\.venv\Scripts\python.exe -m pytest tests\test_media_integration.py -q
.\.venv\Scripts\python.exe scripts\smoke_test.py
```

Real media tests tạo PNG Tiny-SD, WAV SAPI và MP4 FFmpeg. Chúng không coi mock hay file MP4 tồn tại là bằng chứng SVD đã chạy.


## Topic 3 — Financial Intelligence Search (development)

The new **retrieval-only** `POST /financial/search` endpoint adds four methods on the existing indexed PDF chunks: `bm25` (real Okapi BM25), `dense` (Ollama embeddings + Qdrant), `hybrid` (RRF rank fusion), and `hybrid_rerank` (optional local CPU Cross-Encoder). It is separate from the original `/rag/query` learning assistant. Every search requires an explicit `document_ids` list and returns source/page/text, channel ranks, raw scores and timings.

Example request, using an **actual document ID returned by an uploaded report**:

```json
{"query":"What changed in operating cash flow in 2024?","document_ids":["<YOUR_DOCUMENT_ID>"],"method":"hybrid","top_k":5}
```

Setup, benchmark command, metadata caveats and remaining work for a genuine finance deployment are documented in [Financial Search Topic 3](docs/FINANCIAL_SEARCH_TOPIC3.md). The optional Cross-Encoder is isolated in `requirements-financial-rerank.txt` and uses a locally installed model set by `FINANCIAL_RERANKER_PATH`; it is not available by default. **This is a development/research feature, not a production-ready financial data service.**

### Milestone C — tìm bằng chứng SEC đã lập chỉ mục

Trang **Tìm kiếm tài chính** dùng `GET /financial-index/datasets` và `POST /financial-index/search` để tìm theo từ khóa, ngữ nghĩa hoặc kết hợp. Kết quả hiển thị bảng/đoạn nguồn, kỳ báo cáo, công bố SEC và trạng thái đối chiếu. Tờ khai trích xuất một phần luôn có cảnh báo. Đây là truy xuất bằng chứng, chưa phải hệ thống chứng nhận câu trả lời tài chính.

Chỉ mục nằm riêng tại `FINANCIAL_INDEX_PATH` (mặc định `./financial_search_data`). Cần có corpus B đúng manifest và mô hình Ollama `nomic-embed-text` đã cài; ứng dụng không tự tải mô hình. Dừng tiến trình API đang sở hữu thư mục chỉ mục trước khi dùng CLI xây dựng chỉ mục:

```powershell
.\.venv\Scripts\python.exe scripts/financial_index.py build --dataset sec-pilot-c --sources docs/topic3/MILESTONE_C_SOURCES.json
.\.venv\Scripts\python.exe scripts/financial_index.py status
# Sau khi CLI hoàn tất, khởi động API và Streamlit như bình thường.
```

Corpus và cơ sở dữ liệu cục bộ không nằm trong Git. [Báo cáo hoàn thành](docs/topic3/MILESTONE_C_COMPLETION_REPORT.md), [đo hiệu năng](docs/topic3/MILESTONE_C_BENCHMARK.md), [đánh giá truy xuất](docs/topic3/MILESTONE_C_RETRIEVAL_QUALITY.md) và [giới hạn](docs/topic3/MILESTONE_C_LIMITATIONS.md) ghi rõ phạm vi 822 đoạn và hướng dẫn tái lập.
