# GenAI Learning Studio

Ứng dụng học tập GenAI bằng tiếng Việt: FastAPI backend, Streamlit UI, Ollama `llama3:latest`, RAG với Qdrant và TTS. Image/video là module tùy chọn; chúng không ảnh hưởng đến chat, RAG hay TTS.

## Kiến trúc

```text
Người dùng → Streamlit → FastAPI
                         ├─ Chat / TTS chuẩn hóa → Ollama llama3:latest
                         ├─ PDF upload → Extract theo trang → Clean → Chunk
                         │                              → Embedding → Qdrant
                         ├─ Question → Embedding → Similarity search → Prompt → Llama 3
                         ├─ Text → Stable Diffusion cục bộ (tùy chọn)
                         └─ Image → Video diffusion → Frames → MP4 (tùy chọn)
```

## Cài đặt Windows

Python 3.11–3.13 được hỗ trợ cho lõi ứng dụng. Tạo môi trường ảo và cài các dependency cơ bản:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

Ollama là runtime riêng. Cài Ollama, sau đó tải Llama 3 và embedding model:

```powershell
ollama pull llama3
ollama run llama3:latest
ollama pull nomic-embed-text
```

LLM mặc định luôn là Ollama `llama3:latest`; không cần OpenAI API key. Ollama quản lý CPU/GPU model của nó riêng, không yêu cầu cài CUDA PyTorch cho chat/RAG.

## Chạy ứng dụng

Mở hai terminal trong thư mục dự án:

```powershell
uvicorn main:app --reload
```

```powershell
streamlit run streamlit_app.py
```

`streamlit run client.py` cũng được giữ làm lệnh tương thích.

FastAPI docs: `http://127.0.0.1:8000/docs`. Streamlit kiểm tra FastAPI, Ollama và Qdrant khi mở Dashboard/System.

## Cấu hình

Sao chép `.env.example` thành `.env`. Cấu hình chính:

- `OLLAMA_BASE_URL`, `OLLAMA_MODEL`
- `EMBEDDING_PROVIDER=ollama`, `EMBEDDING_MODEL=nomic-embed-text`
- `QDRANT_URL` để dùng server; để trống thì dùng Qdrant local persistence tại `qdrant_data/`
- `QDRANT_COLLECTION`, `CHUNK_SIZE`, `CHUNK_OVERLAP`, `TOP_K`, `SCORE_THRESHOLD`
- `MAX_UPLOAD_MB` và các thư mục `UPLOAD_DIR`, `PROCESSED_DIR`, `TTS_OUTPUT_DIR`, `IMAGE_OUTPUT_DIR`, `VIDEO_OUTPUT_DIR`

Đổi embedding model sau khi đã lập chỉ mục sẽ làm thay đổi vector dimension hoặc không gian vector. Xóa/rebuild collection trước khi đổi model.

## Các tab

1. **Dashboard**: trạng thái Ollama/Qdrant, model, số documents/chunks, dimension, GPU được phát hiện và số lượng media.
2. **Chat với Llama 3**: hội thoại cục bộ, temperature, giới hạn tokens và xóa lịch sử.
3. **Talk to Documents / RAG**: PDF upload, tiến độ theo stage, top-k, ngưỡng similarity, câu trả lời, trang nguồn, chunk retrieval và debug prompt.
4. **Chunk Explorer**: raw/cleaned text, chỉnh chunk size/overlap, thống kê, bảng và expanders cho từng chunk/metadata.
5. **English Script → Audio**: Llama 3 chuẩn hóa tùy chọn, speech rate/volume, audio player và tải file.
6. **Text → Image**: gọi Stable Diffusion cục bộ khi dependency/model/GPU sẵn sàng.
7. **Image → Video**: thử nghiệm Stable Video Diffusion cục bộ, upload ảnh, số frames/FPS và player MP4.
8. **System / GPU**: thông tin runtime, model/embedding/Qdrant và document library với thao tác xóa.

Chế độ học tập ở sidebar giải thích Extraction, Cleaning, Chunking, Embedding, Vector DB, Retrieval và Generation.

## RAG pipeline

`POST /documents/upload` kiểm tra phần mở rộng/MIME, ghi theo từng block bằng aiofiles, áp hạn mức kích thước, rồi khởi chạy BackgroundTasks. Worker trích từng trang bằng pypdf, giữ `original_text`, làm sạch văn bản, chia chunk, tạo embedding và upsert point + metadata vào Qdrant. Truy vấn tạo embedding câu hỏi, tìm top-k vector cosine, lọc score threshold, đưa context có tên file/trang vào prompt và hỏi Llama 3. Không có context phù hợp thì prompt yêu cầu model thừa nhận tài liệu chưa cung cấp câu trả lời.

Mặc định dùng Qdrant persistent local mode, không cần Docker. Có thể đặt `QDRANT_URL=http://localhost:6333` để chuyển qua server.

## Chunk visualization

Chunk Explorer gọi lại PDF đã tải và dựng chunk preview tức thời theo `chunk_size` và `chunk_overlap`. Mỗi chunk hiển thị trang, ID, ký tự, vị trí start/end, overlap, token estimate, embedding status và vector ID nếu đã index. Token count là ước tính gần đúng (`kí tự / 4`), không phải tokenizer của Llama.

## TTS

Llama 3 sửa dấu câu/chuẩn bị phát âm nhưng không tổng hợp tiếng nói. `pyttsx3` gọi Windows SAPI để tạo WAV offline; `edge-tts` còn giữ như fallback tương thích từ bản cũ khi `pyttsx3` chưa cài. Từng tệp có timestamp trong `audio/`. TTS không yêu cầu API trả phí khi dùng SAPI.

## Image và video

Hai module này là tùy chọn. Cài `requirements-image.txt` trên máy tương thích và cấu hình model local qua `IMAGE_MODEL`; video cần thêm `requirements-video.txt`, `VIDEO_MODEL`, CUDA và nhiều VRAM. PyTorch CUDA có thể tải rất lớn; không cài cùng bộ lõi. Nếu model/GPU/ffmpeg không sẵn có, API trả lỗi dễ đọc và các chức năng chính tiếp tục chạy. Không tạo ảnh/video giả.

## API chính

- `GET /health`, `GET /system/status`, `GET /stats`
- `POST /chat`
- `POST /documents/upload`, `GET /documents`, `GET /documents/{id}`, `GET /documents/{id}/chunks`, `GET /documents/{id}/preview`, `POST /documents/{id}/process`, `DELETE /documents/{id}`
- `POST /rag/query`
- `POST /tts/normalize`, `GET /tts/voices`, `POST /tts/generate` (và `/generate` tương thích bản cũ)
- `POST /image/generate`, `POST /video/generate`
- `GET /qdrant/status`, `DELETE /qdrant/collection`

## Tests

```powershell
pytest -q
```

Các test bao gồm chunk size/overlap, text rỗng/ngắn, metadata và trang, schema, retrieval prompt/source, health endpoint và kiểm tra loại file upload. Test này không cần Ollama hoạt động, nhưng end-to-end RAG cần `ollama pull nomic-embed-text` và `ollama pull llama3`.

## Giới hạn đã biết

- Trạng thái document đang xử lý lưu trong bộ nhớ tiến trình; tài liệu READY và chunks được khôi phục từ processed JSON khi FastAPI khởi động lại. Nếu tiến trình dừng giữa lúc indexing, hãy bấm Re-index cho tài liệu còn trong `uploads/` hoặc tải lại PDF.
- PDF scan cần OCR; pypdf chỉ trích văn bản có sẵn.
- Ollama cần hoạt động và có sẵn model LLM/embedding. Lỗi embedding hiển thị hướng dẫn thay vì fallback vector giả.
- Similarity threshold phụ thuộc model embedding và nội dung thực tế; điều chỉnh trong UI khi score thấp.
- Voice SAPI tùy thuộc giọng đã cài trên Windows; duration chưa được đo tự động.
- Stable Diffusion/Video chưa được xác minh trên máy này vì PyTorch/diffusers/GPU CUDA không có trong môi trường lõi.
