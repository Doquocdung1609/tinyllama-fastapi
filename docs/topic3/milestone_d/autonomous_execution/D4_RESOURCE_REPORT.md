# D4 resource report

Environment: Windows 11, Python 3.13.2, approximately 8 GiB visible RAM with less than 1 GiB free at preflight; Ollama at `127.0.0.1:11434` refused connections. No model was downloaded, no paid service used, no embeddings or Qdrant collection built. Demo uses a small isolated SQLite lexical index and a single-request semaphore. The frozen synthetic diagnostic JSON contains per-case in-process times and p50/max; those values include D1/D3/D2/D4 work on tiny invented HTML and exclude FastAPI HTTP transport, Streamlit rendering, real SEC parsing and startup. Do not compare them to accepted C end-to-end latency.

The real-mode per-query source verification cost was measured separately in the D2/D3 artifacts. With current D2 250 KiB cap, that cost does not yield a supported numeric QA context for the newly downloaded 0.9–1.1 MiB filings or historical 2 MiB filings. D4 does not attempt to bypass the cap to improve apparent coverage.
