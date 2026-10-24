# Môi trường cộng tác — 24/10/2026

Đã đọc inventory ZIP gốc. Giữ .venv 3.12.10 hoạt động thay vì xóa để ép owner Python 3.13.2. Windows 11 / RTX 3050 Laptop 4 GB / ~15,2 GiB RAM, driver 610.64. Owner Windows / GTX 1650 Ti / ~8 GB RAM. Ollama thực tế 0.40.10, owner 0.30.10; user PATH đã có Programs/Ollama. Shell cũ cần mở lại hoặc append đường dẫn vào $env:Path.

Torch 2.6.0+cu124 / torchvision 0.21.0+cu124, CUDA 12.4 available, RTX 3050 được kiểm bằng thực thi. Official wheel hash 3313061c1fec4c7310cf47944e84513dcd27b6173b72a349bb7ca68d0ee6e9c0 khớp index. Tải full ban đầu không tiến triển; tải HTTP ranges và kiểm SHA trước pip install, không bypass SSL/hash. GPU instructions: https://pytorch.org/get-started/previous-versions/#v260 ; Ollama PATH: https://docs.ollama.com/windows .

Tesseract UB-Mannheim 5.4.0.20240606 cài bằng winget, verified installer hash. eng/vie từ https://github.com/tesseract-ocr/tessdata_best , osd từ tessdata_fast. Fast có một OCR numeric failure, best vượt test và full regression. Chỉ đổi local data pack, không sửa OCR code. FFmpeg binary imageio-ffmpeg 0.6.0 nằm tools/downloads/ffmpeg-0.6.0/ffmpeg.exe; user PATH có thư mục này.

.env local có TESSERACT_CMD trỏ Program Files/Tesseract-OCR, TESSDATA_DIR=./tools/downloads/tessdata_best. Không in SEC contact. Models/digests cả ba khớp owner (báo cáo chính). Local Tiny-SD checkpoint có thật, test PNG thành công. SVD checkpoint chưa tải; 4 GB VRAM không chứng minh diffusion video ready. FFmpeg motion không phải SVD.

API profile: QDRANT_PATH=./qdrant_data/independent-verification, collection independent_verification, conversation SQLite/upload/processed riêng. Corpus=./financial_corpus/collaborator-v5-final. Không đụng knowledgebase hoặc corpus owner. Không có 1.947 vectors owner để kiểm.

Không cài mù toàn bộ freeze owner: cloud/CLI/Jina không dùng không phải baseline bắt buộc. Theo dependency declarations repo, thêm media/GPU/verification. pip check đạt. Môi trường không byte-for-byte giống owner. Actual và khác biệt:

| Package | Owner | Actual |
|---|---|---|
| agent-detector | 2.0.0 | NOT_INSTALLED |
| aiohappyeyeballs | 2.7.1 | NOT_INSTALLED |
| aiohttp | 3.14.3 | NOT_INSTALLED |
| aiosignal | 1.4.0 | NOT_INSTALLED |
| certifi | 2026.7.22 | 2026.10.23 |
| detect-installer | 0.2.1 | NOT_INSTALLED |
| dnspython | 2.8.0 | NOT_INSTALLED |
| edge-tts | 7.2.8 | NOT_INSTALLED |
| email-validator | 2.3.0 | NOT_INSTALLED |
| fastapi | 0.142.2 | 0.162.0 |
| fastapi-cli | 0.0.32 | NOT_INSTALLED |
| fastapi-cloud-cli | 0.26.0 | NOT_INSTALLED |
| fastar | 0.12.0 | NOT_INSTALLED |
| filelock | 4.0.9 | 4.2.4 |
| frozenlist | 1.8.0 | NOT_INSTALLED |
| googleapis-common-protos | 1.75.5 | NOT_INSTALLED |
| grpcio | 1.84.0 | 1.84.1 |
| hf-xet | 1.6.0 | 1.7.0 |
| httptools | 0.8.0 | 0.9.0 |
| importlib-metadata | 9.0.1 | 10.1.0 |
| iniconfig | 2.3.0 | 2.3.1 |
| multidict | 6.9.1 | NOT_INSTALLED |
| narwhals | 2.26.0 | 2.27.1 |
| numpy | 2.5.3 | 2.5.4 |
| opentelemetry-api | 1.45.0 | 1.45.1 |
| opentelemetry-exporter-http-transport | 0.66b0 | NOT_INSTALLED |
| opentelemetry-exporter-otlp-common | 0.66b0 | NOT_INSTALLED |
| opentelemetry-exporter-otlp-proto-common | 1.45.0 | NOT_INSTALLED |
| opentelemetry-exporter-otlp-proto-http | 1.45.0 | NOT_INSTALLED |
| opentelemetry-proto | 1.45.0 | NOT_INSTALLED |
| opentelemetry-sdk | 1.45.0 | NOT_INSTALLED |
| opentelemetry-semantic-conventions | 0.66b0 | NOT_INSTALLED |
| pandas | 3.0.6 | 3.1.0 |
| pluggy | 1.6.0 | 1.7.0 |
| portalocker | 3.2.0 | 4.4.1 |
| propcache | 0.5.4 | NOT_INSTALLED |
| pyarrow | 25.0.1 | 26.0.0 |
| pycparser | 3.11 | 3.12 |
| pydantic | 2.13.5 | 2.14.1 |
| pydantic-core | 2.46.5 | 2.50.1 |
| pydantic-extra-types | 2.11.1 | NOT_INSTALLED |
| pydantic-settings | 2.15.0 | NOT_INSTALLED |
| pypdf | 6.19.0 | 6.21.2 |
| python-dateutil | 2.9.0.post0 | 3.0.0 |
| qdrant-client | 1.19.1 | 1.20.0 |
| rich-toolkit | 0.20.5 | NOT_INSTALLED |
| rignore | 0.8.1 | NOT_INSTALLED |
| rpds-py | 2026.6.3 | 2026.9.1 |
| sentry-sdk | 2.71.0 | NOT_INSTALLED |
| setuptools | 84.0.0 | 84.2.1 |
| starlette | 1.7.0 | 1.9.0 |
| streamlit | 1.65.0 | 1.66.1 |
| tabulate | 0.10.0 | NOT_INSTALLED |
| tokenizers | 0.23.2 | 0.23.3 |
| toml | 0.10.2 | NOT_INSTALLED |
| transformers | 5.18.0 | 5.20.2 |
| typer | 0.27.2 | 0.27.3 |
| tzdata | 2026.4 | 2026.5 |
| websockets | 17.1 | 17.3 |
| yarl | 1.25.1 | NOT_INSTALLED |
| zipp | 4.1.1 | 4.1.2 |

NOT_INSTALLED có thể là optional/CLI. Full freeze giữ local packages-final.txt. OCR file hashes:

- eng.traineddata: `8280aed0782fe27257a68ea10fe7ef324ca0f8d85bd2fd145d1c2b560bcb66ba`
- osd.traineddata: `9cf5d576fcc47564f11265841e5ca839001e7e6f38ff7f7aacf46d15a96b00ff`
- vie.traineddata: `b6b49293d95d0b6dbd8780174627e82c75be957b6f4ed9862155540d6b00bb45`

GitHub CLI 2.103.2 cài từ winget; người dùng tự login device flow, gh setup-git. Không token trong remote/Git.
