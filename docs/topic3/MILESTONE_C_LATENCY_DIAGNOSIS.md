# Milestone C — latency diagnosis

## Nguyên tắc đo

- Không sửa số baseline trong `MILESTONE_C_MEASUREMENTS.json`.
- Tất cả số dưới đây là independent rerun, cùng 822 chunk và model digest/dimension, warm probes luân phiên endpoint để giảm order bias.
- HTTP end-to-end chạy qua uvicorn một worker, ba representative queries (`aapl_sales`, `tsla_debt`, `tsla_amend_fees`), ba repeats, cùng top-5/candidate-40/provenance path.
- Microbenchmarks tách query tokenization, filtered BM25, Ollama identity/embed, Qdrant, RRF và serialization. Provenance được profile theo file source.

## Reproduce baseline HTTP

Với `OLLAMA_BASE_URL=http://localhost:11434`:

| Mode | HTTP p50 | HTTP p95 (max của 9 samples) | Reported p50/p95 |
|---|---:|---:|---:|
| BM25 | 808,7 ms | 1.657,8 ms | 808,1 / 1.500,7 ms |
| Dense | 4.894,8 ms | 6.211,0 ms | 4.845,0 / 5.674,7 ms |
| Hybrid | 4.926,7 ms | 6.324,5 ms | 5.017,6 / 5.684,4 ms |

Các p50 tái hiện sát report; p95 dùng chỉ 9 samples nên không so tuyệt đối với full baseline.

## Stage breakdown

| Stage | Independent p50 | p95 | Kết luận |
|---|---:|---:|---|
| Query normalization | 0,014 ms | 0,023 ms | Không đáng kể. |
| Filtered persistent BM25 | 35,13 ms | 113,96 ms | Bao gồm filter stats SQL, postings và scoring; production code chưa tách filter riêng. |
| Ollama identity (`localhost`) | 2.055,9 ms | 2.088,0 ms | Persistent IPv6 fallback effect. |
| Ollama embed (`localhost`) | 2.121,5 ms | 2.146,0 ms | Bao gồm connection + inference. |
| Qdrant search | 17,65 ms | 53,84 ms | Không phải dense bottleneck. |
| RRF | 0,073 ms | 0,130 ms | Không đáng kể. |
| JSON serialization approximation | 0,542 ms | 1,016 ms | Không đáng kể; không gồm socket I/O. |
| Provenance full source | 471–1.651 ms/source p50 | source-dependent | Chủ yếu parse raw HTML + regenerated chunks. |

Service `embedding_ms` hiện đo identity lookup cộng embed generation, không tách hai call. Rerun raw policy cho p50 ~4.193–4.213 giây ở Dense/Hybrid, phù hợp tổng hai Ollama probes.

## `localhost` vs `127.0.0.1`

Máy review resolve `localhost` thành `::1` trước `127.0.0.1`; Ollama phục vụ IPv4. Không có proxy env. 12 tags probes và 6 embed probes mỗi endpoint, sau warm-up:

| Endpoint | `/api/tags` p50/p95 | `/api/embed` p50/p95 |
|---|---:|---:|
| `http://localhost:11434` | 2.044,7 / 2.065,5 ms | 2.121,5 / 2.146,0 ms |
| `http://127.0.0.1:11434` | 15,7 / 32,5 ms | 73,7 / 81,2 ms |

HTTP API thực, chỉ đổi Ollama endpoint:

| Mode | `localhost` p50 | IPv4 p50 | Chênh lệch |
|---|---:|---:|---:|
| BM25 | 808,7 ms | 715,7 ms | -93,0 ms; không gọi Ollama, variation chủ yếu provenance. |
| Dense | 4.894,8 ms | 870,2 ms | -4.024,6 ms (-82%). |
| Hybrid | 4.926,7 ms | 741,2 ms | -4.185,5 ms (-85%). |

Đây là persistent endpoint effect trên máy review, không phải one-off. Safe operational recommendation: cấu hình explicit `OLLAMA_BASE_URL=http://127.0.0.1:11434` khi Ollama cùng máy và chỉ listen IPv4. Không đổi historical baseline.

## Provenance cost

Ba source profiles:

| Source class | Full `verified_source` p50 | Raw parse | Hash raw+structured+chunks | Load structured | Rechunk |
|---|---:|---:|---:|---:|---:|
| Apple 10-Q | ~471 ms | 446 ms | 15,6 ms | 43,9 ms | 35,7 ms |
| Tesla 10-K | ~1.651 ms | 1.317 ms | 98,1 ms | 206,3 ms | 104,6 ms |
| Tesla 10-K/A | ~546 ms | 424 ms | 20,7 ms | 44,6 ms | 47,1 ms |

Per-request cache chỉ tồn tại trong local `sources` dict, nên cùng source không reparse hai lần trong một response; request kế tiếp làm lại toàn bộ. Với result set chạm nhiều filings, provenance cộng dồn và giải thích BM25 p95 >1,5 giây dù lexical component chỉ hàng chục ms.

## Safe generation-bound verification cache

Đề xuất không bỏ rehash:

1. Cache regenerated `chunk_id -> FinancialChunk` theo key `(generation, structured_path, raw_hash, structured_hash, chunks_hash, normalized_hash, parser_version, chunker_version)`.
2. Mỗi query vẫn SHA-256 raw/structured/chunks và so frozen hashes. Nếu hash khác, fail closed và evict entry. Như vậy tamper detection tức thời vẫn giữ; chỉ bỏ JSON model-load + raw parse + rechunk lặp lại.
3. Cache bounded LRU theo source count/estimated bytes; thread-safe single-flight để hai queries không cùng parse một filing.
4. Invalidate toàn bộ entry của generation khi generation bị xóa; activation không cần xóa retained generation khác. Close process xóa memory cache tự nhiên.
5. Không dùng `(size, mtime)` làm trust decision: attacker có thể giữ size/mtime. Stat chỉ dùng prefilter; cryptographic rehash vẫn bắt buộc nếu API tiếp tục cam kết tamper detection trên mọi response.

Tests bắt buộc trước merge cache:

- cache hit gọi digest mỗi request nhưng parse/chunk đúng một lần;
- sửa một byte raw, structured hoặc chunks sau cache hit phải fail ngay;
- restore file đúng hash cho phép verify lại;
- same source ở generation khác không dùng nhầm entry nếu parser/chunker/hash policy khác;
- concurrent first-hit chỉ tạo một parse;
- LRU eviction không làm giảm provenance correctness;
- source bị thay trong khoảng hash→read phải bị normalized/context validation bắt; thêm test TOCTOU bằng monkeypatch.

## Build latency/resources

- Raw-policy cold build với `localhost`: 492,65 giây; embedding stage 449,93 giây; 809 embeddings; peak Python 176,08 MiB.
- Prefix-aware cold build với explicit IPv4: 220,44 giây; embedding stage 202,00 giây; 809 embeddings; peak Python 272,27 MiB.
- Cùng generation content sau cache: interruption→resume 13,81 giây, 0 embeddings mới, 822 Qdrant upserts.
- Python memory không bao gồm Ollama process/VRAM. Peak khác nhau giữa runs không đủ để kết luận prefix làm tăng RAM.

## Kết luận latency

Hai bottlenecks được xác nhận độc lập: IPv6→IPv4 fallback của `localhost` (~4 giây cho identity+embed) và full provenance reparse (0,5–1,7 giây/source). BM25/Qdrant/RRF/serialization không phải nguyên nhân chính. Đổi endpoint explicit IPv4 là safe config repair; provenance cache cần implementation/tests riêng, không nên thêm vội trong review này.

