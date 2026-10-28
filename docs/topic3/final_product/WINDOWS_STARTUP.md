# Khởi động Windows

## Yêu cầu một lần

- Python 3.13 và `pip install -r requirements.txt` trong `.venv`; Ollama đã cài và model `nomic-embed-text:latest` có digest `0a109f422b47e3a30ba2b10eca18548e944e8a23073ee3f3e947efcf3c45e59f`.
- Snapshot SEC P7/P10 đã xác minh và Research QA snapshot phải có trên máy. Script không tự tải model, filing hoặc tạo lại vector. Các thư mục này là dữ liệu nghiên cứu riêng, không thuộc Git.
- Đặt các biến môi trường trong PowerShell phiên hiện tại. Không lưu token trong repo:

```powershell
$env:STUDIO_SEC_RESEARCH_ROOT = '<P7_SEC_SNAPSHOT>'
$env:STUDIO_SEC_VECTOR_ROOT = '<P10_READY_VECTORS>'
$env:TOPIC3_RESEARCH_ROOT = '<PINNED_QA_SNAPSHOT>'
$env:STUDIO_WORKSPACE_DIR = '<EMPTY_OR_OWNED_PDF_WORKSPACE>'
$env:STUDIO_API_TOKEN = '<LOCAL_TOKEN_16_CHARS_OR_MORE>'
$env:TOPIC3_RESEARCH_API_TOKEN = '<ANOTHER_LOCAL_TOKEN_16_CHARS_OR_MORE>'
```

Nếu `.venv` ở nơi khác, đặt `STUDIO_PYTHON` trỏ tới `python.exe`. Sau cấu hình một lần, lệnh khởi động:

```powershell
.\scripts\start_financial_studio.ps1
```

Script kiểm tra dependency, Ollama và digest, kiểm tra cổng trống, khởi động ba tiến trình ẩn, chờ health rồi mở browser mặc định. URL mặc định: UI `http://127.0.0.1:8501`, API `http://127.0.0.1:8000`, Research API `http://127.0.0.1:8767`. Có thể đổi cổng bằng `-ApiPort`, `-ResearchPort`, `-UiPort`; dùng `-NoBrowser` khi chỉ muốn khởi động dịch vụ. Có thể đổi Python bằng `-Python`. Log và PID ở `%TEMP%\financial-intelligence-studio`. Đóng các tiến trình dịch vụ của buổi demo khi kết thúc; không xóa workspace hay nguồn SEC để dừng dịch vụ.

Nếu thiếu snapshot hoặc sai model digest, script dừng trước khi mở UI. Các bước thử nghiệm thực tế trong [báo cáo E2E](END_TO_END_TEST_REPORT.md) dùng cổng 8079/8767/8517 để không đụng dịch vụ khác.
