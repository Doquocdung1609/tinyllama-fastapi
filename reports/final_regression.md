# Final regression — 2026-10-10

## Trạng thái theo chức năng

| Chức năng | Trạng thái | Bằng chứng |
|---|---|---|
| FastAPI health/docs | PASS | HTTP 200, smoke test |
| Streamlit load + rerun | PASS | HTTP 200; AppTest chạy lần đầu và rerun đều 0 exception |
| Tám tab | PASS | AppTest mở từng tab, 8/8 có 0 exception |
| Ollama | PASS | online; Qwen2.5 3B và Llama 3 selectable |
| RAG critical Q01 | PASS | đúng 3 loại, page 155, evidence trong prompt |
| RAG critical Q09 | PASS | đúng Open Banking/API, page 214 |
| RAG 30-case | PASS với 1 limitation | 29/30 answer; retrieval/citation/refusal đạt gate |
| Chunk Explorer | PASS | tab load, API/document library hoạt động |
| TTS local | PASS | WAV thật hợp lệ |
| Tiny-SD text-to-image | PASS | PNG 256×256 thật, nonblank |
| FFmpeg motion demo | PASS | MP4 thật, mode ghi rõ non-generative |
| SVD genuine diffusion | BLOCKED — HARDWARE / MODEL_NOT_AVAILABLE | 4 GB VRAM, 8 GB RAM, không có checkpoint |
| Qdrant data | PASS / preserved | 971 vector, dimension 768, cosine |

## Lệnh và kết quả kiểm thử

### Unit và API

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Kết quả: **26 passed, 3 skipped**. Ba test skipped là real media suite có opt-in riêng. Có một deprecation warning từ Starlette TestClient/httpx, không làm test thất bại.

### Media inference thật

```powershell
$env:RUN_REAL_MEDIA_TESTS="1"
.\.venv\Scripts\python.exe -m pytest tests\test_media_integration.py -q
```

Kết quả: **3 passed** trong 38.60 giây:

- Tiny-SD tạo PNG đúng kích thước, file >1 KB và variance >1.
- Windows SAPI tạo WAV có frame và sample rate hợp lệ.
- FFmpeg tạo MP4 Ken Burns >1 KB với mode `ken_burns_motion_demo_not_diffusion`.

### Smoke API/UI

```powershell
.\.venv\Scripts\python.exe scripts\smoke_test.py
```

Kết quả: `passed=true`; FastAPI, Streamlit, tám tab, Ollama, Qdrant và embedding đều true. Image status READY. Video status BLOCKED đúng capability thực.

### Streamlit reload và tám tab

Streamlit `AppTest` chạy cùng entry point `streamlit_app.py` hai lần liên tiếp: 0 exception ở cả hai lần. Sau đó test chọn lần lượt cả tám sidebar option; kết quả mọi tab đều có 0 exception. Entry point dùng `runpy.run_path(...)`, vì vậy UI script được thực thi lại ở mỗi Streamlit rerun thay vì bị Python import cache làm trang trắng.

### RAG thật

`scripts/rag_live_benchmark.py` gọi endpoint FastAPI thật với Qdrant thật và Qwen2.5 3B thật. Kết quả cuối:

| Metric | Giá trị |
|---|---:|
| Recall@5 | 100% |
| MRR | 1.000 |
| Evidence precision | 65.56% |
| Evidence vào prompt | 100% |
| Answer correctness | 96.67% |
| Citation accuracy | 100% |
| Refusal recall / precision | 100% / 100% |
| Average end-to-end | 17.04 s |

Ca còn lại: Q29 retrieval đúng trang 216–218 và citation đúng, nhưng answer chỉ nói “hai nhóm khách hàng” mà không nêu rõ người tiêu dùng và nhà cung cấp giải pháp tài chính.

## Acceptance checkpoint

1. Q01 retrieve và dùng page 155: **YES**.
2. Q09 trả đúng quan hệ Open Banking/API: **YES**.
3. Citation xuất phát từ context thực: **YES**; evidence ID được resolve và validate.
4. Qwen/Llama cùng selected context và constraints: **YES**.
5. Retrieval và generation metrics tách riêng: **YES**.
6. Unsupported questions refused: **YES**, 2/2; precision 100%.
7. UI giải thích image conditioning: **YES**.
8. UI chỉ có text motion prompt khi backend hỗ trợ: **YES**; SVD báo không hỗ trợ và không hiện prompt.
9. Genuine video diffusion đã chạy: **NO — BLOCKED**, không tuyên bố PASS.
10. Text-to-image giữ nguyên và chạy thật: **YES**.
11. Tám tab operational: **YES**.
12. RAM/VRAM/disk được kiểm tra trước video: **YES**.
13. 971-vector dataset được giữ nguyên: **YES**.
14. PASS claims có output/test tương ứng: **YES**.

## Khởi động demo

```powershell
cd C:\Users\Admin\Desktop\AI_thay_Hieu\tinyllama-fastapi
.\start_genai.ps1
```

Mở http://127.0.0.1:8501. Trong RAG, chọn tài liệu đang active, để `top_k=5`, threshold `0.55`, bật Debug Mode và thử Q01/Q09. Trong Image → Video, dùng FFmpeg motion demo; phần SVD hiển thị blocker thật.

## Giới hạn còn lại

- Q29 còn thiếu hai actor cụ thể dù bằng chứng đúng.
- Qwen nhỏ có thể thay đổi cách diễn đạt giữa các lượt; benchmark dùng temperature 0 nhưng inference nền tảng vẫn có thể có khác biệt nhỏ.
- Citation fallback có thể gắn top evidence khi model không phát ra `[E#]`; metadata `citation_fallback_added` cho biết trường hợp này.
- Local Qdrant folder chỉ cho một process mở đồng thời. Không chạy hai FastAPI instance cùng trỏ `qdrant_data`; dùng Qdrant server nếu cần multi-process.
- SVD/CogVideoX không phù hợp cấu hình hiện tại. Cần GPU/RAM lớn hơn hoặc adapter remote có kiểm soát.
