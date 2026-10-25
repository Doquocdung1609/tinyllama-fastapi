# Milestone C scientific evidence freeze — 2026-10-25

Freeze reviewed at source `a6c3d6f`. No historical measurement or query artifact was edited. New acceptance documents add audit evidence only.

Windows checkout recovery: `core.autocrlf=true` produced CRLF copies and correctly triggered the runner's frozen-byte hash guard. `.gitattributes` now explicitly keeps scientific JSON and evaluation/benchmark scripts as LF. This changes checkout policy only; Git blobs, frozen queries, judgments and measurements are unchanged. Acceptance validates hashes on a fresh integration checkout.

## Scientific interpretation

Original 14-query development Recall@5 remains BM25 0.911, Dense 0.321, Hybrid 0.714. Prefix-aware generations are explicitly separate from raw-policy generations. The old set diagnoses the prefix defect; its improvement is not an unbiased generalization result.

Issuer/document split: development MSFT/KO (8 questions), held-out NVDA/WMT (16). Corpus selected before query authoring/ranking; qrels manually grounded in source rows/paragraphs and locators, no generated answers as labels. Frozen query hash was checked before evaluation. Held-out is consumed; further model/fusion tuning requires a fresh holdout.

| Held-out mode | Recall@5 | MRR@5 | nDCG@5 |
|---|---:|---:|---:|
| BM25 | 0.9375 | 0.796875 | 0.8327166136742353 |
| Dense | 0.8125 | 0.49583333333333335 | 0.5740173397493409 |
| Hybrid | 0.9375 | 0.7708333333333334 | 0.8139824383928644 |

Acceptance audit independently recomputed these macro metrics from saved per-query retrieved IDs and frozen qrels using the evaluation scorer; all matched to 1e-12. No ranking parameters or qrels were changed. BM25 remains the recommended default for this corpus; Hybrid does not demonstrate consistent superiority.

## Identity

- Development dataset `issuer-dev-index-v1`, generation `ddf187006addb1c19462937ddff8b8707f6d524af827dd4bbd1946113a80a40d`, manifest `4bd1437b7a333fc660d59638a54017d761f9f098fcb8a0d9e3118f42c9f80ee5`.
- Held-out dataset `issuer-heldout-index-v1`, generation `afe00aa93e6957a92e0292f6ae54d258dc1c1f5a84e3f83c275931476875d691`, manifest `579c202eb8f41a964ab88fc551ab7cfe04774637db89acd27156f006add9cef7`.
- Nomic digest `0a109f422b47e3a30ba2b10eca18548e944e8a23073ee3f3e947efcf3c45e59f`, 768 dimensions, asymmetric prefixes; authoritative identity is also in frozen query JSON.
- Parameters: top-5 evaluation, top-10 diagnostic list, candidate 40, equal RRF k=60; document truncate first 6000 content characters; 160 ordinal chunks/filing, separate 320-chunk generations.

## Measurement boundaries

Historical HTTP, core lexical, embedding, Qdrant and provenance measurements remain separately labeled. Cache comparison is same-corpus service timing, not HTTP: disabled total p50 1558 ms, warm cache 238 ms; every-request hashes remain mandatory. First-connection localhost fallback and reused-session embedding measurements are separate. New product smoke is functional verification and does not replace benchmark baselines.

## SHA-256 file freeze

| Artifact | SHA-256 |
|---|---|
| MILESTONE_C_MEASUREMENTS.json | bb7b1f6ee3ae33ad3275e23e4537cf3b74c687a3ff3288cae98d5919e3be96d9 |
| MILESTONE_C_QUERIES.json | c40d85bdbe8e552e9d3eebf09ffba32914ee0c12e6f4ca1a8df3d0bcda56fc7e |
| MILESTONE_C_NEXT_EVAL_QUERIES.json | 39196ad6b304e5f79975c8bfb3573d593a3ef0052ccd55135bd1dbd2face6555 |
| MILESTONE_C_ISSUER_HELDOUT_CORPUS.json | 1944ca03db486354ad5f77b15b19993795d33f56b1255de338e82ca74b5c8b9f |
| MILESTONE_C_ISSUER_HELDOUT_QUERIES.json | c8aedd619f362208fcb097c197f351b117aaa7e2c3bfd758ef97c56df842792a |
| reports/milestone_c_issuer_heldout.json | a9f442aa81e9c658311078f326a5139c7fd1cad848b120f2473b66444021b15b |
| reports/milestone_c_issuer_development.json | 4425398031ca17177ed63242484d2699c975a40b231372bf407160821e90d08e |
| reports/milestone_c_hardening_latency.json | e9034699e4c1177df79a5ccc11453138b0e9b8a0feff9af747191c6417446b0e |
| scripts/evaluate_persistent_financial.py | 9d908b9199ad427571d8318151739585b8703bf6ef256b06c8977999e60e38f4 |
| scripts/benchmark_financial_hardening.py | 34dff7a1e4461da9ae479eb1897f3eae40fc28cacf1ee9cc4858402b5ceb12c3 |

Limits: small n and wide bootstrap intervals; deterministic filing subsets; exact-row qrels may omit useful narrative; partial administrative table extraction; limited issuer/form coverage. Source verification validates evidence correspondence, not generated financial answers or decisions.

## Post-integration checksum clarification

The table above preserves hashes observed on the original review workstation. Some older JSON files and Python-written result files used CRLF there. The accepted `.gitattributes` policy emits canonical LF Git-blob bytes in fresh checkouts; therefore their file hashes differ by newline encoding only. An explicit post-merge byte comparison of every frozen artifact's Git blob at `4eee5de` versus accepted merge `69e6866` found all identical. No numerical result, query, judgment or historical Git blob changed.

Canonical LF SHA-256 values at accepted commit `69e6866552d15571858b44707d59a453443fae9c`:

| Artifact | Canonical SHA-256 |
|---|---|
| MILESTONE_C_MEASUREMENTS.json | 9925a0f6cab569a36e0ceef0e1d53613c9e2306f67dae005b83faca5bac95554 |
| MILESTONE_C_QUERIES.json | b98e125698a0c10db83c03327654264234326706d7256287e2189983d8757d86 |
| reports/milestone_c_issuer_heldout.json | 7ee95bbefe47f2f92a3b99b48d886686a5fd41d0ee5017bf8ec8299015ee632e |
| reports/milestone_c_issuer_development.json | 43d04075e2cc760ed07f137177b7a537294e3a555ff7b92fca7ea7551e951f22 |
| reports/milestone_c_hardening_latency.json | fda94ba2dba563a817369cb7ce58025dd6c4459bb153f5a9242a0f184459ff8d |

All other listed query/corpus/script hashes are unchanged between the reviewed workstation copies and canonical LF blobs. The held-out query hash `c8aedd…792a` remains byte-identical and the benchmark hash guard passes on the fresh Windows checkout.
