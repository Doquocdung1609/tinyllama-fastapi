# SEC import watchdog and recovery

The import progresses through discovery, acquisition, source verification, extraction and lexical publication. New imports checkpoint actual verified bytes, parsed tables and extracted chunks. The lexical receipt reports published parent count. The vector builder updates completed and target embeddings after committed batches.

The API keeps the filing at `LEXICAL_READY` with a separate `BUILDING_DENSE`, `DENSE_PENDING` or bounded retry reason. In lexical-only mode, Dense retry is visibly disabled by configuration. An operator can enable Dense and request a retry without replacing the original acquisition. Product searches require a validated publication.

The supervising process checks its worker every five seconds. An inactive worker is stopped after 240 seconds without durable progress, with an additional one-hour wall limit. A prepublication interruption becomes retryable. An authenticated lexical publication survives a Dense interruption and remains available for BM25. The child’s original per-batch timeout and memory guard remain active.

- The real Microsoft 10-Q in the main product library retained its BM25 publication across backend restart. It did not advertise Dense or Hybrid there.
- The same accession in the alternate workspace has its own READY generation and complete vector membership.
- The unit test simulates a hung child. The isolated browser test additionally simulates an interrupted Dense state on a real, published PepsiCo filing before restarting the backend. The follow-up job events and successful lexical query document recovery. Neither simulation changes original SEC HTML or declares an unfinished vector generation READY.

See [diagnostics](MSFT_IMPORT_DIAGNOSTIC.json), [acceptance](SEC_SOURCE_SCOPE_MATRIX.csv) and [browser logs](LIVE_BROWSER_RESULTS.md).
