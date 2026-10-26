# D5 reproducibility, costs and unresolved risks

## Commands and environment

Windows 11, Python 3.13.2, Qdrant-client 1.20.0, Pydantic 2.13.5, FastAPI 0.142.2, Starlette 1.7.0 and pytest 8.4.2. `SCORE_THRESHOLD=0.55`, `RUN_REAL_MEDIA_TESTS=0`. No paid service, model download, new embedding, new vector index or production activation. The research source root is an isolated marker-owned local directory; only its three new official SEC files, frozen metadata, lexical-only SQLite and synthetic demo index were used.

Reproduction (the D5 held-out command is **one-shot** and must not be rerun under v1; inspect its saved result instead): `python -m scripts.run_d5_frozen_heldout --root <owned-research-root>` after committed preregistration; `python -m scripts.run_d5_e2e_http --root <owned-research-root>` creates an output file exclusively; `python -m scripts.run_d5_verifier_ablation`. Ordinary regression: `python -m compileall -q app scripts`, `python -m pytest -q`, `python -m pytest -q -m "not integration"`, `git diff --check`. Scripts use `x`/`open('x')` for frozen outputs; a repeated held-out run fails at the exclusive access marker.

Accepted baseline `32c4a4834c5f8a0b34ac28c42f960c862dd8077d`: 550 tracked Git blobs; `git diff --name-status <base> HEAD` reported zero modified/deleted baseline paths. Raw SEC hashes for PG/COST/HD rechecked true. This is Git/source-byte integrity evidence, not a claim that every runtime path was penetration tested. The frozen C 14-query evidence retains Recall@5 BM25 .911, Dense .321, Hybrid .714; the prior issuer-held-out C result remains separate and recommends BM25. No D1/C evaluation label or historical result was altered.

Hardware at preflight: ~8 GiB visible RAM, <1 GiB free; later observation ~1.07 GiB free. Ollama `127.0.0.1:11434` refused connections, so Dense/F/LLM were not activated; no large model download was attempted. Per-query cold/warm transport and concurrent throughput were not experimentally separated. D5 HTTP JSON includes individual elapsed times; D3 stage measurements and C baseline are separate measurement boundaries.

## Open findings

1. **HIGH scientific blocker:** D2's unchanged 250 KiB cap prevents verified real table-cell context for retained and newly acquired SEC filings. Real numeric QA precision/recall cannot be estimated. Do not lift the cap without bounded revalidation and regression.
2. **HIGH scientific blocker:** no compatible local vectors/Ollama, so Dense, fixed RRF and adaptive finalist cannot be compared on the frozen partitions. Failure-inclusive zero is availability, not model quality.
3. **HIGH generalization limit:** five held-out exact-row queries from one issuer and auto-generated relevance, zero human adjudicators. No issuer-cluster interval or paraphrase/table-wide inference.
4. **MEDIUM product gap:** explicit contradictory query CIK202/UI CIK999 returned `NO_ELIGIBLE_EVIDENCE` rather than a typed conflict. It did not broaden scope or emit a claim, but loses the conflict explanation. Accepted D1 behavior should be reviewed in a separate authorized repair.
5. **MEDIUM product gap:** first BM25 hit for real `net sales` PG query was a partial-extraction segment percentage row. The UI exposes the warning, and numeric QA abstains. Better table/row ranking requires new evidence and is not tuned on D5 held-out.
6. **PARTIAL UI gate:** official SEC source link and structural locator were visible; the in-app browser did not show a navigated destination after clicking. No source-navigation success claim.
7. **OPERATIONAL GAPS:** no live publication/read concurrency stress, distributed coordination, production hardening or full legacy UI smoke. Synthetic restart and existing C tests are narrower evidence.

Recommended next step is owner review of Draft stacked PRs and a separately authorized, bounded source-window/provenance design plus independent human-labeled real financial table dataset. Do not merge based on this research package or change accepted BM25 defaults.
