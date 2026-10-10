# GenAI Learning Studio

Ứng dụng học tập GenAI chạy local bằng FastAPI và Streamlit. Hệ thống giữ tám tab: Dashboard, Chat với Ollama, Talk to Documents / RAG, Chunk Explorer, English Script → Audio, Text → Image, Image → Video và System / GPU.

## Thành phần

- LLM local qua Ollama; mặc định `qwen2.5:3b`, có thể chọn `llama3:latest` trong Chat/RAG.
- Embedding `nomic-embed-text`, Qdrant local, hybrid dense + lexical rank fusion.
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

Kết quả cuối hiện tại: Recall@5 100%, answer correctness 96.67%, citation accuracy 100%, refusal precision/recall 100%. Xem `reports/rag_root_cause.md`.

Hồi quy P0 cho câu hỏi đa nghĩa về số loại đổi mới tài chính đạt 4/4 case, gồm Q01 và hai câu ngoài tài liệu. Xem `reports/rag_p0_context_repair.md` và `reports/rag_p0_regression.csv`.

## Video

Mode SVD nhận ảnh, không nhận text prompt. UI chỉ hiện các điều khiển backend thực sự dùng: seed, frames, fps, motion bucket, noise augmentation và decode chunk size. Trên GTX 1650 Ti 4 GB + RAM 8 GB, SVD được báo `BLOCKED` và checkpoint không được tự tải.

Mode FFmpeg tạo hiệu ứng Ken Burns, luôn ghi rõ `ken_burns_motion_demo_not_diffusion`.

Xem `reports/video_feasibility.md` và `reports/video_pipeline_explained.md`.

## Kiểm thử

```powershell
.\.venv\Scripts\python.exe -m pytest -q
$env:RUN_REAL_MEDIA_TESTS="1"
.\.venv\Scripts\python.exe -m pytest tests\test_media_integration.py -q
.\.venv\Scripts\python.exe scripts\smoke_test.py
```

Real media tests tạo PNG Tiny-SD, WAV SAPI và MP4 FFmpeg. Chúng không coi mock hay file MP4 tồn tại là bằng chứng SVD đã chạy.
