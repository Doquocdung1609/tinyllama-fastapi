# D3 dev/validation diagnostic results

11 automatically literal-row labelled questions (PG5/COST6), source freeze before ranking, no human adjudication. Raw per-query IDs/pools/contributions/locators/failures/latency and failure-inclusive metrics are archived in D3_DEV_VALIDATION_DIAGNOSTICS_v1.json. No heldout opened.

| Arm | Successful requests/11 | Scientific interpretation |
|---|---:|---|
| B |11|Real C persistent BM25, source-verified |
| D |0|No compatible research vectors/Ollama; quality NOT_MEASURED |
| F |0|Dense unavailable; quality NOT_MEASURED |
| R |9|Two finite-terminology queries route to unavailable Dense |
| T |0|F unavailable; real D2 context also unsupported |
| A |9|Some queries cannot use exact-hit heuristic and require unavailable Dense |
| AT |9|Same availability as A; real D2 lookup absent, zero table bonuses, not an eligible table experiment |

B all11: Recall@5 .701515; Recall@10 .824242; Precision@5 .327273; MRR@5 .712121; nDCG@5 .652706; group coverage@5 .909091/@10 1.0. Multi-parent literal relevance explains fractional recall even when one supporting row is found. No broader financial relevance or answer correctness follows.

R/A/AT conditional-success metrics in JSON use9 queries and must not be compared directly with B's11-query mean. Failure-inclusive metrics/paired differences retain all11; zeros on unavailable channels are engineering-failure accounting, **not** evidence of weak Dense embeddings. No adaptive finalist qualifies. B remains an operational baseline, not a newly demonstrated universal quality winner.

Returned evidence across all runs380; wrong issuer0/380; each returned parent passed C source correspondence. Complete evidence-returning requests38/77, so empty/failed responses are not100% provenance-complete queries. Wrong observation-period rate NOT_MEASURED: this diagnostic has no explicit-period queries. Scope audit separately finds0/11 gold filing exclusions. These finite source/table-label diagnostics do not establish an unqualified provenance/security guarantee.
