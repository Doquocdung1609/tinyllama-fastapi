# Windows resource stability — PARTIAL

**Memory pressure occurred; this is not an all-PASS stability result.** All 599 live one-second samples are in OWNER_RESOURCE_SAMPLES.json. No unrelated application/model was stopped. No observed OOM, process crash or lost original document in this bounded run. RSS and available memory do not prove absence/presence of a leak.

## Comparable isolated CLI arms, same nine source PDFs/vectors

| Measure | Before V3R | Final V3R2 |
|---|---|---|
| Python benchmark peak RSS MiB | 1020.36 | 975.49 |
| System minimum available MiB | 1929.04 | 1984.52 |
| Cold prepare ms | 97227.28 | 98025.67 |
| Query p50 ms | 1641.23 | 1503.35 |
| Query p95 ms | 1835.09 | 1838.53 |

Final repeated prepare 870.76ms, build count1 unchanged. Cold validation reconstructs bounded in-memory records and checks immutable files, so restart is not instant. The small Python RSS reduction is supported; larger free-RAM differences are affected by other applications and cannot be attributed to this patch.

## Real Prebuilt/Chrome lifecycle

| Measure | Actual |
|---|---|
| Owned API Python peak RSS | 1091.59 MiB |
| All Chrome peak summed RSS | 4235.83 MiB |
| Tesseract peak RSS | 205.74 MiB |
| Initial Ollama-name-only peak | 41.07 MiB, lower bound |
| Ollama + separate llama-server bounded warm-query peak | 249.89 MiB |
| Minimum system available RAM | 708.15 MiB |
| Samples below768/1536MiB | 1 / 6 |
| Minimum free disk | 74.07 GiB |
| GPU final | NVIDIA GeForce RTX 3050 Laptop GPU, 4096 MiB, 417 MiB |
| Query-embedding p50/p95 | 60.59 / 108.75 ms (168 actual nested timings) |
| Fresh one-page scan region extraction | 10619.43 ms |
| Upload→READY including OCR/embedding | 11486.13 ms |
| Added-document prepare / removed-test-document prepare | 66202.03 / 62892.19 ms |
| Restart prepare observed wait | 77992.00 ms |

Ollama initially sampled by name misses Windows llama-server.exe: early peaks are explicitly incomplete, not total family peaks. A separate quarter-second three-mode measurement includes both (OLLAMA_FAMILY_MEASUREMENT.json). GPU numbers are snapshots, not a continuously sampled VRAM peak. System available RAM includes owner applications; Chrome sum is not JS heap or a leak measurement.

The scan is a raster derivative of original SEM PDF page7 at150dpi, with parent SHA256 and page mapping retained. It is a technical OCR lifecycle test, not new independent data. OCR returned SCANNED/REGION_FUSION,212 OCR words, mean confidence86.39,12 low-confidence words; REVIEW_PENDING. Three modes ran on that identical one-document scope. Only that newly created technical document was deleted after evidence was preserved. Nine original documents remain READY. Rebuild count1→2→3 corresponds to real add/delete changes; old immutable index files remain. See LIVE_OCR_LIFECYCLE.json.

Chrome: four live tests PASS including reviewed highlight, unreviewed candidates/raw units, stale-response rejection, no-source numeric abstention, ACB three metrics and20 page transitions. Same-scope original ACB warm-mode measurements (ms): bm25 947.75, bm25 925.93, dense 1365.94, dense 1342.73, hybrid 1663.86, hybrid 1711.0. See LIVE_SAME_SCOPE_MODES.json. These are scoped retrieval checks, not universal financial accuracy.

## Implemented controls and practical limit

- Explicit new owner clone only; legacy roots preserve original behavior. Single reentrant OCR/embedding/index/query admission, max2 waiters. Low-memory admission thresholds:768MiB heavy,256MiB search; UI warning below1536MiB. Limits are entry checks, not reserved OS memory; other apps may reduce RAM after entry.
- Region corpus max30000 entries /192MiB index; two build-page views,64 header caches,2048 label cache. Duplicate source-entry corpus discarded; source-byte/payload/chunk hashes still checked per prepare/query.
- New-document rebuild discards the previous in-memory corpus before loading a replacement. Immutable versions stay. PDF pages cancel rendering/cleanup, inactive page evidence query cache is evicted.
- Repeated warm search does not create a new index generation. Restart retained five index SQLite files byte-for-byte and mtime-for-mtime, all original raw hashes and eight reviewed facts. Runtime restart still validates sources and reconstructs in-memory state.

**Presentation recommendation:** use READY documents, wait for prepared index, do not run OCR/benchmark alongside the presentation. Let the owner close unnecessary tabs/apps if desired; this agent did not close unrelated work. The observed ~708MiB free-RAM trough means stability remains PARTIAL; no unqualified demo-readiness certification or SEARCH_LOCKED.
