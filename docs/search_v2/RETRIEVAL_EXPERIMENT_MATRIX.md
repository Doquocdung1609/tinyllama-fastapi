# Frozen ablation matrix

| Arm | PDF intervention | SEC behavior | Verification |
|---|---|---|---|
| B0 | unchanged owner baseline FTS5 all-token OR | unchanged SEC BM25 | source bytes only |
| B1 | unchanged locked Nomic768 dense | unchanged SEC dense | source bytes only |
| B2 | unchanged fixed RRF k60 | unchanged SEC RRF | source bytes only |
| C1 | quoted phrases/controlled aliases, weighted label/body/context; chunks | B0 passthrough | no automatic numeric authority |
| C2 | metric/table row candidates | B2 passthrough | separate reviewed-cell binding |
| C3 | C1+C2+baseline union, deterministic evidence compatibility | B2 passthrough | explicit query conflicts; related passages may remain |
| C4 | C3 plus strict context/clarification rules for financial lookups; narrative paragraphs separately | B2 passthrough | only compatible audited cells get reviewed-answer label |

Rules are generic and unit-tested, not company keywords. Fixed ordinal features (metric20,row5,reviewed5,conflict−30,source-statement match3/mismatch−2) express evidence compatibility, not probabilities or learned financial correctness. Baselines remain independent in Evaluation. C4 was selected using development quality and abstention before first test execution; policy/source-label hashes are in EVALUATION_POLICY_LOCK.json. An extra English proper-name probe found a wrong-issuer eligibility defect after that run. The critical guard was fixed; all subsequent38-query results are explicitly exposed-label retests, not untouched heldout evidence. Original results and lock are preserved.

Initial development exposed an unsafe narrative→unrelated-reviewed-cell promotion. It was repaired with regression; initial diagnostic results are preserved and superseded by DEVELOPMENT_SCORED_RESULTS.json. Source-period/basis ambiguity was tightened before final development and policy lock. A scoring repair prevents repeated hits for the same source from inflating nDCG. Initial Windows SQLite handle/rename issue and line-ending/hash issue were repaired before a successful benchmark. No tests disabled.

No installed lightweight model reranker was available. The measured deterministic option fits the machine; no unsupported claim that it beats a model reranker. A new model/download was not made compulsory. SEC is explicitly a passthrough control, so aggregate improvements cannot be interpreted as improved SEC parsing or authentication.

Final v2.6 validation:643backendPASS,7frontendPASS,buildPASS; extra source-title statement/unit candidates and explicit statement conflicts tested. The38-query v2.6 result is exposed-label retest. Original v2.3 policy source archive matches its first-run hash.

Original run bytes (including superseded diagnostics and first test) are retained in MEASURED_RUN_SNAPSHOTS.zip; per-entry hashes are in its manifest. Final result JSON files use one record per line without changing any measured values.
