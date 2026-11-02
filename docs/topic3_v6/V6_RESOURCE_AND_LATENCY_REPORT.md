# Hardware, search cost and storage

Machine observed on 2026-11-02: AMD Ryzen 7 7445HS, six cores/twelve logical processors, 15.23 GiB visible RAM. During pilot the corrected B local Qdrant index contained 8,670 points. A and B restored on-disk directories occupy approximately **94.4 MiB and 94.5 MiB** respectively; cached embedding models occupy **572.2 MiB** and 13 original SEC HTML review snapshots **37.3 MiB**. These caches/snapshots were not committed. Around the pilot observation, C: had about **66.0 GiB free**. No larger-index experiment was run, so larger-index memory and latency are unmeasured; size, payload scans and embedding/cache requirements would grow.

V6 exploratory pilot: 300 live searches in one research process, 30 questions × ten frozen methods. Process/sidecar initialization measured **686.95 ms** in that process. Peak observed process RSS was **1,216.68 MiB**; the minimum sampled free physical RAM in the method summaries was **2,471.45 MiB**. These are samples after queries, not a high-frequency true peak. Search p50/p95 in ms:

| Method | p50 | p95 |
|---|---:|---:|
| BM25 | 254.5 | 279.4 |
| Dense BGE-small | 41.2 | 48.2 |
| SPLADE | 610.6 | 671.0 |
| BM25+Dense | 301.5 | 338.3 |
| SPLADE+Dense | 671.0 | 719.4 |
| Author Stage-2 | 691.1 | 759.6 |
| A2 | 425.3 | 445.5 |
| A3 | 433.7 | 471.4 |
| A4 | 430.4 | 547.1 |
| A4R | 428.7 | 477.2 |

A2–A4R are separate full searches per question, not one shared candidate fetch, so p50 differences include embedding and local Qdrant/cache effects. A3 scans all 8,670 payloads when the sidecar initializes; that one-time work is in initialization, not each query latency. It stores those payloads in RAM. A4 and A4R add relatively small local ordering work but no verified financial answer. Pilot order is fixed, cache is reused, and the first query of each model may be colder; **controlled cold-versus-warm latency was not measured**. V5R manifest p50/p95 and lower free-RAM samples differ with machine load. Do not extrapolate these times to a hosted multi-user service. One local Qdrant writer/reader lock requires serialized access in the product API.
