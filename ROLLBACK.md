# Hướng dẫn khôi phục

## Các checkpoint

- Mã/cấu hình ban đầu: đường dẫn được ghi trong `reports/checkpoint_path.txt`.
- Dữ liệu RAG trước migration extraction layout: `reports/data_backup_path.txt`.
- Snapshot dependency: `reports/pip-freeze-before.txt` và `reports/pip-freeze-after-install.txt`.

## Khôi phục mã

1. Dừng đúng tiến trình FastAPI và Streamlit của thư mục dự án.
2. Sao lưu trạng thái hiện tại sang một thư mục mới.
3. Chép các tệp từ checkpoint mã về thư mục dự án. Không chép hoặc xóa `uploads`, `processed`, `qdrant_data`, `audio`, `images`, `videos` nếu chỉ cần rollback mã.
4. Chạy `python -m pytest -q`, sau đó `.\start_genai.ps1`.

## Khôi phục index RAG v1

1. Dừng FastAPI để Qdrant local nhả file lock.
2. Đổi tên `processed` và `qdrant_data` hiện tại để giữ một bản phục hồi ngược.
3. Chép hai thư mục tương ứng từ đường dẫn trong `reports/data_backup_path.txt` về project.
4. Khởi động FastAPI và kiểm tra `/documents`, `/qdrant/status`.

## Khôi phục dependency

Không gỡ package toàn hệ thống. Môi trường thay đổi chỉ nằm trong `.venv`. Nếu cần rollback sạch, tạo `.venv` mới và cài `requirements.txt`; dùng snapshot freeze để đối chiếu phiên bản. Wheel ảnh/video là tùy chọn và không cần cho chat, RAG hoặc TTS.
