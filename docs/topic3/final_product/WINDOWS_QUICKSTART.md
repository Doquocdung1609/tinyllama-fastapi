# Khởi động Windows

Máy đã kiểm tra: Windows, Python 3.12.10, Node 24.19.0, Ollama đã cài Nomic đúng digest, Qwen2.5:3b tùy chọn, Tesseract vie/eng/osd. CI Python 3.13. Không tự tải model trong script startup. Không cần kích hoạt venv nếu dùng đường dẫn Python đầy đủ.

```powershell
cd C:\Users\Admin\Documents\GitHub\tinyllama-fastapi
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
npm ci --prefix frontend
.\scripts\run_financial_studio.ps1 -Mode Development -Workspace .\studio_workspace\react-product-20261028 -OpenBrowser
```

UI http://127.0.0.1:5173, API http://127.0.0.1:8110/docs. Mở `tmp/studio-runtime/access-token.txt`, sao chép khóa vào màn hình đăng nhập cục bộ. Không gửi/commit tệp này. Token không xuất trong URL hoặc console startup. Nếu Ollama mới cài chưa nhận lệnh, mở terminal mới hoặc dùng `& "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe" --version`; launcher tự tìm đường dẫn đã cài. Chỉ tải model thủ công khi chủ máy muốn; không đổi digest/index cũ.

```powershell
.\scripts\run_financial_studio.ps1 -Stop
npm run build --prefix frontend
.\scripts\run_financial_studio.ps1 -Mode Prebuilt -Workspace .\studio_workspace\react-product-20261028 -OpenBrowser
```

Prebuilt dùng http://127.0.0.1:8110/app/, không cần Node runtime sau build. Dừng bằng -Stop; kiểm tra ownership PID+creation time, không kill mọi Python/Node/Ollama. Cổng bị chiếm sẽ báo lỗi; không tạo bản chạy trùng. Development cần cả 8110/5173 trống. APIport/UIport có thể đổi; Vite proxy lấy STUDIO_API_TARGET.

Workspace mặc định mới là kho riêng; để xem hai PDF đã xử lý dùng đúng -Workspace như trên. Upload PDF do chủ dự án cung cấp trong Kho tài liệu. OCR: cấu hình TESSERACT_CMD và TESSDATA_DIR trong .env cục bộ nếu khác vị trí đã cài, yêu cầu eng/vie/osd. Xem Hệ thống trước upload. Các trang chưa đối chiếu giữ ứng viên, số liệu chưa được dùng tính toán. Không có dữ liệu raw PDF trong Git.

## SEC tùy chọn

Máy hiện đã có profile product PG/HD riêng, launcher phát hiện khi cả source/vector manifest hiện diện và kiểm tra identity. Chỉ chuẩn bị mới khi được chủ dự án cho phép và SEC_USER_AGENT có thông tin liên hệ hợp lệ. Không sửa registry hash để nhận file khác. Có thể truyền STUDIO_SEC_RESEARCH_ROOT, STUDIO_SEC_VECTOR_ROOT và TOPIC3_RESEARCH_ROOT cùng snapshot; sai identity bị từ chối.

```powershell
.\scripts\run_financial_studio.ps1 -Stop
.\.venv\Scripts\python.exe scripts/prepare_product_sec.py --root tmp/studio-runtime/sec/p7-isolated-review-product-20261028
.\.venv\Scripts\python.exe scripts/p10_build_isolated_vectors.py --root tmp/studio-runtime/sec/p7-isolated-review-product-20261028 --vector-root tmp/studio-runtime/sec/t3-p10-isolated-vectors-product-20261028 --batch-size 4 --output tmp/studio-runtime/sec/vector-build.json
```

Đây là lệnh setup rõ ràng, không có trong startup. Snapshot mới khác bytes cần review registry riêng; script không tự chấp nhận thay đổi qua mọi lần chạy. Contact User-Agent hiện được lấy từ cấu hình đã có, không in công khai. 1 request/s, không retry, giới hạn 4MB/HTML.

## Kiểm thử / rollback

```powershell
.\.venv\Scripts\python.exe -m pytest -q
npm run test --prefix frontend
npm run build --prefix frontend
cd frontend
npx playwright install chromium
npx playwright test
```

Live E2E cần Development đang chạy, token private và hai PDF thật tại đường dẫn đã cung cấp (hoặc HPG_PDF/BIDV_PDF). Test số liệu cần các ô trong SOURCE_REVIEW_FIXTURES đã được đối chiếu qua UI; không tự coi mọi OCR đúng. Thiếu nguồn/token sẽ SKIP rõ ràng. CI chạy core deterministic và frontend unit/build; không tải corpus/model cá nhân.

Legacy dự phòng: cài requirements-legacy-ui.txt rồi `scripts/start_financial_studio.ps1 -Legacy -UiPort 8501`. Không chạy hai phiên đồng thời trên cùng workspace/Qdrant local. Giữ các báo cáo lịch sử WINDOWS_STARTUP/USER_GUIDE nguyên bản để truy vết; hướng dẫn React hiện tại là tệp này.
