# Milestone C measured benchmark

Date: 2026-10-24. Hardware: AMD Ryzen 7 7445HS, 15.231 GiB usable RAM, RTX 3050 Laptop GPU (4 GiB available). Windows 11 build 26300, Python 3.12.10, FastAPI 0.162.0, Streamlit 1.66.1, Qdrant client 1.20.0, Torch 2.6.0+cu124, Ollama 0.40.10. GPU availability is recorded; GPU kernel/VRAM peaks were not profiled.

## Fixed real corpus and protocol

All modes use the same selected 822 B chunks: Apple 566/566, Tesla original 128/1609 and amendment 128/597. Tesla selection is uniform ordinal sampling including endpoints, defined before inspecting retrieval output. There are 2,772 available chunks in these sources; full Tesla dense indexing is not claimed.

Apple manifest: `f192ac227f38c9fb18f707b8ecc2ba87546db81beae7c33a1a24b78959b32bd0`.

Tesla original/amendment manifest: `fad83b03abafefe126fb01c7147961544f91baa5ae1db7ff4ca7a5031f38e2a4`.

Dataset: `sec-pilot-c`; generation: `026d4963a52b347ffbe44f99cb91fe7af158cff646910eb91ce1907ecdb1618d`; membership SHA-256: `751f8178ec233c89e9e91bb8ccc5fd06f75aea731d6b3ddff3ddca68e262e434`.

Installed embedding identity: nomic-embed-text:latest, digest `0a109f422b47e3a30ba2b10eca18548e944e8a23073ee3f3e947efcf3c45e59f`, dimension 768, first 6,000 characters with explicit Ollama truncation. This is the same identity for dense and hybrid.

Fourteen source-row queries were frozen in feature commit bb60a82 before the first retrieval evaluation. Local query-file SHA-256: `c40d85bdbe8e552e9d3eebf09ffba32914ee0c12e6f4ca1a8df3d0bcda56fc7e` (raw-file line-ending sensitive). Each mode runs three repetitions per query; API mode order rotates by query. First API request per mode is excluded from warm summaries (41 samples/mode); local lexical baseline has 42 scoring samples. Baseline source validation is performed separately outside lexical timing. No relevance targets were changed after results were seen.

Sequential rates are sample count divided by summed measured elapsed time, not concurrent serving capacity. p95 uses the nearest-rank observed quantile. Data and per-query IDs/metrics are in [MILESTONE_C_MEASUREMENTS.json](MILESTONE_C_MEASUREMENTS.json); query judgments and exact source locators are in [MILESTONE_C_QUERIES.json](MILESTONE_C_QUERIES.json).

## Mandatory real-corpus comparison

Corpus generation is the exact source snapshot/selection above for every column/mode. Retrieval component excludes embedding and provenance. Original/matched baselines time a local scoring function; API retrieval includes generation/filter/dense validation. HTTP includes embedding, provenance and transport. Do not compare baseline local scoring with API HTTP as equivalent work. All quality figures are macro @5 on this small development set.

| Mode | Retrieval p50/p95 ms | Component sequential qps | HTTP p50/p95 ms | HTTP sequential qps | Recall@5 | MRR@5 | nDCG@5 | Provenance validity | Isolated per-mode RAM |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Previous lexical baseline | 57.889 / 124.267 | 20.504 | NOT_MEASURED | NOT_MEASURED | 0.911 | 0.786 | 0.822 | 100% | NOT_MEASURED |
| Formula/token-matched control | 154.306 / 315.692 | 7.729 | NOT_MEASURED | NOT_MEASURED | 0.911 | 0.786 | 0.822 | 100% | NOT_MEASURED |
| Persistent BM25 | 30.585 / 94.323 | 24.996 | 808.082 / 1500.672 | 1.044 | 0.911 | 0.786 | 0.822 | 100% | NOT_MEASURED |
| Dense | 25.030 / 43.114 | 35.546 | 4845.000 / 5674.746 | 0.197 | 0.321 | 0.113 | 0.160 | 100% | NOT_MEASURED |
| Hybrid RRF | 59.447 / 164.043 | 13.251 | 5017.574 / 5684.377 | 0.195 | 0.714 | 0.613 | 0.627 | 100% | NOT_MEASURED |

Per-mode RAM is NOT_MEASURED, rather than copying one shared process peak into separate mode columns. Source correspondence is verified for all returned chunks, including baseline results checked offline; it does not imply relevance or financial truth.

## Cold requests and stage costs

“Cold” means first request of that mode in this new API process, not cold OS filesystem caches or independent cold Ollama/model state. Legacy smoke ran first, so model state may be warm; the first dense request additionally opens local Qdrant. Dense/hybrid share that client afterwards.

| Mode | First HTTP ms | Warm embedding-stage p50 ms | Warm provenance p50 ms |
|---|---:|---:|---:|
| Persistent BM25 | 601.938 | 0.000 | 711.730 |
| Dense | 5540.805 | 4165.905 | 629.078 |
| Hybrid RRF | 4813.757 | 4163.137 | 721.559 |

The embedding stage includes model identity HTTP lookup, embedding request/transport and dimension validation. It is **not isolated GPU inference time**. A post-benchmark diagnostic GET /api/tags took 2071.767 ms through configured localhost versus 44.494 ms through 127.0.0.1 (one observation each, both HTTP 200). This identifies a local connection-path cost worth investigating, without establishing the DNS/IPv6 root cause or an alternative full-benchmark result. No benchmark result was replaced by this faster probe. A local deployment can explicitly configure OLLAMA_BASE_URL=http://127.0.0.1:11434 when that binding is reachable, then rerun the complete benchmark; that experiment is NOT_MEASURED here.

Provenance rehashes source artifacts and reparses selected filings per request. End-to-end latency is therefore materially higher than postings search. BM25 has no embedding call; a zero-duration embedding stage has undefined throughput, stored as null in exported evidence.

## Construction, reuse, update and restart

| Experiment | Build stage | Embedding/cache stage | CLI elapsed | Python process peak |
|---|---:|---:|---:|---:|
| First 822-chunk build, no index/cache | 303.927 s | 289.245 s | NOT_MEASURED | NOT_MEASURED |
| Separate fresh-root build after stopping nomic | 265.178 s | 249.101 s | 267.289 s | 221.910 MiB |
| Same READY generation repeated | Validation/reuse | 0 new embeddings/postings | 3.565 s | 125.402 MiB |
| Cached original-only membership, 694 chunks | 10.938 s | 0.451 s cache lookup | 13.026 s | 244.551 MiB |
| Cached amendment update, 694→822 | 11.993 s | 0.496 s cache lookup | 14.086 s | 257.027 MiB |

Both uncached builds inserted 822 new posting documents and embedded 809 unique texts; 13 identical inputs reused embeddings. Timing variance is preserved, not discarded. The second build has a separate empty root and a model stopped before launch; its timing includes model startup but excludes parent-shell startup. The first trial did not instrument a process peak; it is not reconstructed afterwards.

The amendment experiment uses a separate dataset name in a globally prepopulated cache. It adds 128 logical members, computes new membership/statistics and upserts 822 generation-specific vectors, while adding zero new postings/embeddings. It demonstrates cached publication cost, **not cold-new-document incremental embedding cost**. The original-only manifest is `662a0e5260dbbc8171980c1dd8e30f4975e6f41aa147f6cbafbc0f6e5d36ee6b`. Prior generation/collections remain present. Fixture tests separately verify a genuinely new derived chunk requires one new embedding.

Fresh-interpreter BM25 CLI trial: index open 2.810 ms; complete command body including provenance 460.721 ms; peak 81.098 MiB. Index-open timing measures constructor/SQLite schema opening, excludes Python/import startup and is not full dense cold load. The CLI read the published generation without rebuilding. First API requests above separately capture API/Qdrant lazy startup.

Retained main index occupies 51,427,016 bytes (49.045 MiB), including shared postings/cache and three collections (822, 694 and 822 members). It is not one-generation size and excludes raw B corpus and the separate cold experiment. Benchmark-driver process peak was 174.449 MiB; shared API lifetime peak was 578.738 MiB after legacy smoke and all modes. Both exclude external Ollama RAM/VRAM and are not attributable per mode.

## Lexical scaling controls

These are component experiments with one fixed query, five sequential trials (first excluded from warm summaries), no embedding/provenance and no tracemalloc instrumentation. Real subsets are the first 100/400/822 selected IDs in sorted chunk-ID order, not tuned by relevance. Synthetic cases use the existing make_corpus generator. Build time is lexical only, not full application READY publication.

| Dataset | Chunks | Original p50/p95 ms | Matched p50/p95 ms | Persistent p50/p95 ms | Persistent qps | Lexical build ms |
|---|---:|---:|---:|---:|---:|---:|
| Synthetic | 100 | 3.540 / 3.873 | 6.531 / 7.980 | 3.351 / 3.970 | 292.193 | 40.411 |
| Synthetic | 1000 | 32.607 / 36.138 | 72.844 / 75.217 | 11.884 / 15.141 | 78.887 | 321.989 |
| Synthetic | 5000 | 169.504 / 194.570 | 358.943 / 388.891 | 55.771 / 59.889 | 18.007 | 1531.181 |
| Real | 100 | 7.960 / 8.440 | 22.978 / 23.547 | 3.210 / 3.656 | 310.972 | 96.498 |
| Real | 400 | 35.361 / 44.916 | 103.825 / 120.499 | 10.248 / 13.166 | 96.432 | 428.406 |
| Real | 822 | 79.997 / 84.420 | 197.978 / 201.261 | 17.623 / 18.656 | 56.042 | 1457.888 |

The existing tracemalloc-instrumented historical script was also rerun without modification: 5,000 synthetic chunks gave p50 653.051 ms, p95 835.047 ms, 1.531 qps using its reciprocal-p50 convention, peak Python allocation 7.879 MiB. The owner's historical 0.926 qps is preserved as a different-machine/run observation, not a speedup denominator. Tracemalloc overhead makes those numbers incomparable to the untraced component table; the matched untraced controls provide the relevant comparison.

## Research questions

- C-RQ1: persistent postings reduce measured lexical latency on this machine, including the matched-tokenizer controls. This does not claim lower source-validated end-to-end latency than a baseline that omits source validation.
- C-RQ2: all 14 queries preserve the exact top-five ordering of the formula/token-matched baseline. Original and persistent macro quality also match on this set; fixtures cover financial distinctions absent from the development questions.
- C-RQ3: source-pinned lexical/dense generations are consistent in the pilot and controlled failure tests. Unavailable/mismatched dense indexes fail closed or explicitly degrade when requested.
- C-RQ4: **No hybrid improvement is demonstrated.** Hybrid is worse than BM25 on these source-row targets; dense is worse still. No ranking/qrels tuning was performed after this result.
- C-RQ5: real lexical latency increases with selected corpus size in the fixed-query control, while remaining below recomputed lexical baselines. Full dense/hybrid scaling beyond 822 chunks is NOT_MEASURED.

See [completion/reproduction commands](MILESTONE_C_COMPLETION_REPORT.md) and [limitations](MILESTONE_C_LIMITATIONS.md). Small samples, warmed caches, sequential execution and incomplete semantic judgments preclude general production or accuracy conclusions.
