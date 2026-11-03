# Source to chunk to qrel traceability

Each C1 record names a frozen question, accession, raw source SHA-256, source locator and disposition. The C2 ledger refers to the immutable C1 ledger SHA-256 and records a provisional AI technical label. The C3 provenance map refers to original frozen chunk IDs and text hashes in both index A and B. Each provisional qrel carries the frozen question ID, original chunk ID, original text SHA-256 and raw source SHA-256. The validator rejects unknown or duplicate chunk IDs, changed text hashes, changed source hashes and an unknown grade disguised as a numeric relevance grade.

The full 94-row C1 and C2 ledgers, 8,670-row provenance map and 17,340-row qrels live in the private owner-machine handoff. Their byte hashes and sizes are in `G3T_PRIVATE_EVIDENCE_MANIFEST.json`. Git contains redacted counts and the reproducible code, not answer values or raw SEC responses.

Eight of the eleven historical cases have a static row/value match in an original chunk. The three AMD cases `09_01`, `10_01` and `10_02` do not have a static text match; this is a **manual corpus check needed**, not proof that ingestion lost the facts. Source-available-only text earns no retrieval credit. No model-ranking outputs were read during source review.
