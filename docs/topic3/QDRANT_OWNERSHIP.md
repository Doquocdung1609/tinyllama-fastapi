# Milestone C — Qdrant ownership

## Embedded mode

Một OS kernel file lock tại `<index-root>/.qdrant-owner.lock` bảo đảm chỉ một process mở embedded Qdrant directory. File còn sót sau crash không được coi là owner; kernel lock tự giải phóng khi process chết. Regression dùng process con, xác nhận process thứ hai fail `LOCAL_QDRANT_ALREADY_OWNED`, terminate bất thường rồi owner mới mở lại được.

Thread safety trong owner process dùng lock riêng cho Qdrant operations; SQLite dùng WAL và transaction. Query được phép chạy trong build vì generation mới chưa publish; cleanup đợi active queries và chặn queries mới.

## Server mode

Khi `FINANCIAL_INDEX_QDRANT_URL` được đặt, local owner lock không áp dụng và nhiều app process có thể dùng Qdrant server. Collection vẫn generation-isolated (`financial_c_<24 hex>`), payload có full generation và publish chỉ xảy ra sau count, dimension và exact chunk-ID validation.

## Operational rule

Embedded: chạy đúng một API worker và không chạy CLI index song song cùng root. Multi-worker bắt buộc dùng Qdrant server. Server mode hiện chưa mang API-key/TLS config trong app, nên endpoint phải nằm trên trusted network cho đến khi có secret/TLS support.
