# Milestone C — generation-bound provenance cache

## Contract

Cache chỉ giữ kết quả parse/rechunk, không cache trust decision. Mỗi request vẫn đọc và SHA-256 raw, structured và chunks bytes; sau snapshot read còn rehash path để bắt file bị đổi trong khoảng kiểm tra. Mismatch fail closed và clear cache.

Key gồm generation, filing, ba artifact hashes, normalized/manifest hash, parser version, chunker version và chunking policy. LRU bị bound theo entry và byte; first hit có single-flight; cleanup generation invalidate entries; process close clear toàn bộ.

## Đối chứng cùng corpus

Trên 6 query NVDA, 3 modes/query, explicit IPv4:

| Config | Provenance p50/p95 | End-to-end p50/p95 | Cache |
|---|---:|---:|---|
| Disabled | 1.410 / 1.606 ms | 1.558 / 2.763 ms | 18 miss |
| Generation-bound LRU | 100 / 120 ms | 238 / 325 ms | 18 hit, 2 warm-up miss, 15,26 MiB |

BM25, Qdrant và IDs không đổi. Cache tiết kiệm parse/rechunk; hash cost khoảng 100 ms vẫn còn để giữ tamper detection.

## Tests

Raw/structured/chunks one-byte tamper đều fail; restore cho verify lại; generation/parser/chunker version tạo miss riêng; concurrent first hit parse một lần; eviction không làm sai kết quả; TOCTOU bị bắt; cleanup invalidates. Cache không chống attacker có quyền thay cả artifacts lẫn manifest/index metadata—đó là trust-boundary khác.
