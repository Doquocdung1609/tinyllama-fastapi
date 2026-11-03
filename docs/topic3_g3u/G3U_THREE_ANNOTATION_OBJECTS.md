# Three annotation objects and the source boundary

| Object | Evidence and use | Current authority |
| --- | --- | --- |
| `EXACT_ANSWER_GOLD` | Complete source-backed answer to frozen G2 wording, including comparative and negative scope | No human-certified 94-row set; C2 is AI proposal only |
| `EXACT_FINANCIAL_CELL` | Original SEC row, column, period, value, currency and unit/scale binding | C1 source cells exist, but two scope questions and some unit contexts remain for human review |
| `ORIGINAL_SINGLE_CHUNK_QREL` | Relevance of **one** frozen 8,670-corpus chunk to a frozen question; F10 Policy B | Source-only G3U has conservative AI `PARTIAL`/`UNJUDGED`; genuine human events are zero |

A verified SEC HTML table can establish source truth but is not a returned original chunk. Adjacent chunks, a stitched source bundle or a future sidecar cannot be credited as an original-single-chunk hit. Original retrieval rankings stay in a separate sealed private log; the judge view contains no arm, rank, score or previous labels. The static source queue is target-filing-only and not the ranked mixed-arm union, so it cannot diagnose off-target retrieval failures.
