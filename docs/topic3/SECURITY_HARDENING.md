# Milestone C — security hardening

## Mutation boundary

`build`, `activate`, generation protection và cleanup yêu cầu `Authorization: Bearer <FINANCIAL_INDEX_ADMIN_TOKEN>`. Default khi token trống là deny (`503`); token sai trả `401` bằng constant-time comparison. Local bypass chỉ hoạt động khi `FINANCIAL_INDEX_ALLOW_LOCAL_MUTATIONS=true` và peer là loopback.

Request body bị giới hạn 16 KiB, Pydantic cấm unknown fields, dataset/ticker/form/period/filing IDs/manifests được canonicalize và bound. Queue build tối đa và cooldown force-rebuild ngăn lặp vô hạn. HTTP chỉ trả stable error code; causal exception/path vẫn chỉ có ở direct service diagnostic.

## Resource controls

- Accepted builds được serialize và số pending request bị bound.
- `force_rebuild` có cooldown theo dataset.
- Batch embedding giới hạn 1–32; candidate/top-k giới hạn 100.
- Provenance LRU bound theo cả entry và byte.
- Retention mặc định không auto-delete; apply phải explicit và generation active/rollback/pinned/evaluation bị chặn.
- Windows path preflight fail sớm với `WINDOWS_PATH_CAPACITY_EXCEEDED`.

## Verification

Regression bao phủ missing/invalid/valid token, explicit local override, read compatibility, oversized/malformed payload, queue/cooldown, stable error, timeout và path capacity.

## Giới hạn còn lại

Đây không phải public-Internet security certification. Read search vẫn public theo legacy contract; token không có rotation/role/audit identity; Qdrant server URL chưa cấu hình API key/TLS; rate limiting là process-local; nhiều API replicas cần external coordinator. Secret phải được inject ngoài Git và không xuất hiện trong report/log.
