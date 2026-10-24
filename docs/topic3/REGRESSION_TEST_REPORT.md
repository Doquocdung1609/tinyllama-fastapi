# Topic 3 — Milestone A regression test report

## Environment

- Windows, Python 3.13.2 virtual environment.
- Local Qdrant collection: `knowledgebase`.
- Local Ollama embedding model: `nomic-embed-text`.
- No Cross-Encoder checkpoint installed or downloaded.
- Test target before audit fixes: PR #1 head `76336f4...`.
- Test target after fixes: working branch `codex/topic3-milestone-a-pr1`.

## Automated tests

| Stage | Command | Actual result | Classification |
|---|---|---|---:|
| Original PR targeted | `.venv\Scripts\python.exe -m pytest -q tests/test_financial_search.py tests/test_financial_api.py tests/test_financial_benchmark.py` | 14 passed, 1 warning, 1.23 s | UNIT/API-STUBBED |
| Original PR full regression | `.venv\Scripts\python.exe -m pytest -q` | 86 passed, 3 skipped, 1 warning, 8.13 s | UNIT + LOCAL REGRESSION |
| Audit-fix targeted | `.venv\Scripts\python.exe -m pytest -q tests/test_financial_search.py tests/test_financial_api.py tests/test_financial_benchmark.py tests/test_qdrant_service.py` | 23 passed, 1 warning, 2.58 s | UNIT/API-STUBBED |
| Audit-fix full regression | `.venv\Scripts\python.exe -m pytest -q` | 94 passed, 3 skipped, 1 warning, 7.18 s | UNIT + LOCAL REGRESSION |
| Syntax | `.venv\Scripts\python.exe -m compileall -q app scripts tests` | exit 0 | STATIC EXECUTION |
| Dependencies | `.venv\Scripts\python.exe -m pip check` | No broken requirements | ENVIRONMENT |
| Diff whitespace | `git diff --check` | no errors | STATIC |

The warning is Starlette's deprecation notice for its current `httpx`
TestClient adapter. The three skipped media tests require optional real-media
conditions and are unrelated to financial retrieval.

## Live end-to-end retrieval smoke

Command shape:

```powershell
$env:PYTHONPATH='.'
.venv\Scripts\python.exe scripts/financial_retrieval_benchmark.py `
  --cases tmp/topic3_pr1_smoke_cases.json `
  --api http://127.0.0.1:8000 `
  --output tmp/topic3_pr1_smoke_final `
  --methods bm25 dense hybrid --ks 1 3 5 10
```

The qrel was manually tied to page 155 chunk
`aedb60bc088e4242970a43da1e897bde-00578`. Gold IDs were supplied only to the
evaluator and were not sent in `/financial/search` requests.

| Method | R@1 | R@3 | R@5 | R@10 | MRR@10 | nDCG@10 | Wall latency |
|---|---:|---:|---:|---:|---:|---:|---:|
| BM25 | 0 | 1 | 1 | 1 | 0.3333 | 0.5 | 315.9 ms |
| Dense | 0 | 0 | 0 | 0 | 0 | 0 | 3,864.1 ms |
| Hybrid | 1 | 1 | 1 | 1 | 1 | 1 | 2,379.2 ms |

All methods reported the same corpus snapshot SHA-256. One inspected hybrid
response broke 2,511.54 ms into corpus preparation 33.33, BM25 196.15,
embedding 2,169.15, Qdrant ANN 112.66, and fusion 0.10 ms.

This is not a valid method-comparison benchmark: `n=1`, the question was known
from earlier development, the corpus is not SEC filings, and only one relevant
chunk was labeled. It is integration evidence only.

## Negative-path integration

| Case | Actual result | Status |
|---|---|---:|
| `hybrid_rerank` without local model | HTTP 503 with explicit path requirement | PASS |
| Whitespace-only query | HTTP 422 | PASS |
| Missing document scope | Pydantic HTTP 422 | PASS |
| Production Qdrant health | online, 1,947 vectors, dimension 768 | PASS |
| Existing RAG endpoints | Included in 94-test full regression | PASS |

## BM25 scaling probe

Command:

```powershell
$env:PYTHONPATH='.'
.venv\Scripts\python.exe scripts/topic3_bm25_scaling.py `
  --sizes 100 1000 5000 --repeats 7 `
  --output reports/topic3_bm25_scaling.csv
```

| Chunks | Cold | Warm P50 | Warm P95 | P50 q/s |
|---:|---:|---:|---:|---:|
| 100 | 47.490 ms | 30.498 ms | 35.621 ms | 32.789 |
| 1,000 | 243.606 ms | 261.552 ms | 312.418 ms | 3.823 |
| 5,000 | 1,209.679 ms | 1,079.902 ms | 1,208.678 ms | 0.926 |

The corpus is deterministic synthetic finance-like text. These numbers prove
the query-time rebuild cost on this machine, not real filing relevance or
production capacity.

## Unverified paths

- Cross-Encoder real inference: BLOCKED, no approved checkpoint.
- SEC EDGAR ingestion and provenance: NOT IMPLEMENTED.
- Real ticker/year/form Qdrant filtering: PARTIAL, no filing metadata corpus.
- Concurrent throughput/load and restart during financial search: NOT RUN.
- Access-control isolation: NOT IMPLEMENTED.
- Independent development/holdout retrieval quality: NOT IMPLEMENTED.
