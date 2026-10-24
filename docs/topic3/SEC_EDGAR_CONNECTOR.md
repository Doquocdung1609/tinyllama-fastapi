# SEC EDGAR Connector

## Nguồn chính thức

Connector sử dụng submissions API `https://data.sec.gov/submissions/CIK##########.json` và primary filing trong `https://www.sec.gov/Archives/edgar/data/...`. Theo tài liệu SEC, submissions API công khai không cần API key, CIK có 10 chữ số và JSON chứa lịch sử filing; truy cập tự động vẫn phải tuân thủ chính sách fair access.

Tham khảo:

- [EDGAR Application Programming Interfaces](https://www.sec.gov/search-filings/edgar-application-programming-interfaces)
- [SEC Developer Resources](https://www.sec.gov/about/developer-resources)
- [SEC Webmaster FAQ](https://www.sec.gov/files/about/webmaster-faq.htm)

## Cấu hình bắt buộc

```dotenv
SEC_USER_AGENT="GenAILearningStudio student@example.edu"
SEC_REQUESTS_PER_SECOND=6
SEC_TIMEOUT_SECONDS=30
SEC_MAX_RETRIES=3
SEC_MAX_FILING_MB=100
```

`SEC_USER_AGENT` phải có tên ứng dụng và email thật. Nếu thiếu/sai, constructor dừng trước request và CLI/live smoke trả `BLOCKED_EXTERNAL_SOURCE` với `network_requests: 0`. Không ghi email/secret vào repository.

## Hợp đồng truy cập

- Chỉ HTTPS trên `data.sec.gov` hoặc `www.sec.gov`, kể cả URL cuối sau redirect.
- Rate limit cấu hình trong `(0, 10]` request/giây; mặc định 6 để có khoảng dự phòng.
- Timeout hữu hạn; retry cho lỗi kết nối, 429 và 5xx.
- Không retry 403/404; 403 hướng dẫn kiểm tra định danh/tốc độ.
- Exponential backoff có jitter và tôn trọng `Retry-After` nếu có.
- `ETag` và `Last-Modified` được lưu; 304 chỉ hợp lệ khi raw cache còn tồn tại.
- Download ghi file tạm rồi atomic replace, xóa file tạm khi lỗi và giới hạn bytes.
- Không bypass CAPTCHA, rate limit hoặc restriction.

## Discovery

Đầu vào: CIK, ticker tùy chọn, tập form, date range, limit. Chỉ hỗ trợ `10-K`, `10-Q`, `10-K/A`, `10-Q/A`. Ticker không là khóa; nếu không được cung cấp thì giữ NULL và ghi lý do. Fiscal year/period không được đoán từ ngày báo cáo; parser chỉ cập nhật khi có iXBRL fact rõ ràng.

`dry-run` chuẩn hóa CIK và in đúng URL/kế hoạch nhưng không khởi tạo SEC client và không gửi mạng.

## Trạng thái xác minh

- **VERIFIED (offline):** header, CIK/accession, form/date filter, retry lỗi kết nối + 429, conditional headers, 304 cache, giới hạn host và download bytes.
- **BLOCKED_EXTERNAL_SOURCE:** live discovery/download ngày 2026-10-24 vì biến môi trường định danh SEC chưa được cấu hình.
