# Milestone D — baseline and problem statement

Design review date: 2026-10-25. **DESIGN ONLY — NO MILESTONE D IMPLEMENTATION AUTHORIZED.** Project identity: Hybrid Search for Financial Intelligence. This package proposes experiments; it reports no new retrieval or answer scores.

## Immutable starting point

Accepted integration branch: `codex/topic3-milestone-b-sec-corpus`, local and fetched remote HEAD `d1d5195b26f77d8fb25c830229c4c3693d4b638f`. Accepted Milestone C merge `69e6866552d15571858b44707d59a453443fae9c` is an ancestor (exit 0 from `git merge-base --is-ancestor`). Milestone B historical merge: `bde80f6d672f1744b54ec669300a86844139c54f`. C acceptance scope is a controlled local pilot with documented limitations, not production certification. See [acceptance](../MILESTONE_C_OWNER_ACCEPTANCE.md), [integration](../MILESTONE_C_INTEGRATION_REPORT.md), [freeze](../MILESTONE_C_SCIENTIFIC_EVIDENCE_FREEZE.md).

Preflight: clean `git status --short`; fetched `origin --prune`; created only `codex/topic3-milestone-d-research-blueprint` from the accepted HEAD. `origin/main` was `ceaa8acfcfaea8056e45b859a0fc44d6381fb22a`; local `main` remains at its pre-existing `d59a9a9` (ahead by one), and neither main ref nor the accepted branch is a write target. No owner collection, corpus, manifest, model or historical evaluation has been changed by this research.

## Actual architecture inspected at that commit

| Aspect | Source and behavior | Implication for D |
|---|---|---|
| Ingestion | `app/financial_ingestion/{schemas,html_parser,chunker}.py`: immutable source snapshots, structured filing, row-level table chunks and text windows | Reuse identity and source coordinates; row-aware chunking already exists |
| Data flow | `app/financial_index/corpus.py` loads manifest-bound chunks; `service.py` builds and publishes generations; API calls search; `client.py` displays evidence | Research must remain snapshot-bound |
| Lexical stage | `lexical.py`: persistent SQLite postings, term frequency, generation document frequency and filtered population; BM25 k1=1.5, b=0.75; stable chunk-ID tie | Strong mandatory baseline, not a throwaway comparator |
| Dense stage | `service.py`: Ollama embedding identity/digest/prefix enforced; isolated generation collection; filtered Qdrant candidates, deterministic local ordering | Reusing a vector from another representation or prefix is invalid |
| Fusion stage | `app/services/financial_search_service.py`: RRF, k=60, sum reciprocal channel ranks, dedup per channel and logical chunk | No evidence of an arithmetic RRF defect; overlap can promote a weak shared candidate |
| Storage/lifecycle | SQLite documents/postings/members/frequencies/vectors/generations; isolated Qdrant collections; atomic active pointer, rollback, protection, retention | Incremental embedding reuse does not imply delta-only collection size/build work |
| Contracts/security | `app/api/financial_index.py` and `service.py`: bounded requests, mutation authentication, embedded exclusive ownership, shared mutation lock | D must not weaken fail-closed validation or local ownership |
| Provenance | `corpus.py`: source/structured/chunk hashes, regenerated chunk correspondence; bounded generation/version cache still hashes per request | Retrieval validity is distinct from claim, unit and period correctness |
| Product/legacy | `client.py` Financial Search exposes BM25/Dense/Hybrid, ticker/form; API additionally supports filing/CIK/fiscal filters. Legacy Chat/RAG uses its separate path | UI defaults BM25; API's existing default is Hybrid. No silent default change is proposed |

Table chunks carry caption, section, expanded header columns, row label/context, unit context, reporting periods, cells with raw text and inline numeric attributes, footnotes, continuation metadata, filing/version, URL and structural locator. Their repeated headers/metadata can be verbose. Text windows use 1,200 characters with 120 overlap; embedding input is capped at 6,000 characters and Ollama truncation is allowed. Character length is not a token guarantee. Truncation and representation dilution are hypotheses requiring position-aware logging, not established sole causes of Dense errors.

BM25 uses `log(1 + (N-df+0.5)/(df+0.5))` with filtered corpus statistics; repeated query tokens are unique, with typed number/sign/percent/form/fiscal tokens. Dense retrieval requests up to four times the candidate budget within filtered membership before final ordering. Ties beyond a backend cut need explicit measurement. Complete generations retain full membership/collections; vector input caching saves embedding calls, not all disk or publication cost. SQLite WAL and process-local locks do not establish distributed safety.

## Locked scientific evidence

These are historical observations, not experiments rerun for D:

| Evaluation identity | BM25 Recall@5 | Dense Recall@5 | Hybrid Recall@5 | Interpretation |
|---|---:|---:|---:|---|
| Original frozen 14, pre-prefix repair | 0.911 | 0.321 | 0.714 | Diagnostic historical baseline; incompatible with repaired vector identity |
| Issuer/document held-out NVDA/WMT, repaired prefixes | 0.9375 | 0.8125 | 0.9375 | 16 questions, 320 sampled chunks; consumed held-out |

Held-out MRR@5: 0.796875 / 0.495833 / 0.770833. nDCG@5: 0.832717 / 0.574017 / 0.813982 (BM25/Dense/Hybrid). Development was MSFT/KO. AAPL/TSLA and the intermediate 16-question set are also consumed. **BM25 is the recommended default for the current evaluated financial corpus. Hybrid has not shown consistent superiority.** See [issuer evaluation](../ISSUER_HELDOUT_EVALUATION.md) and [retrieval diagnosis](../MILESTONE_C_RETRIEVAL_DIAGNOSIS.md).

Example failure already documented: WMT operating-margin evidence ranked BM25 1, Dense 24, Hybrid 9. Conversely NVDA foreign-tax evidence ranked 6/5/2. These motivate query-level analysis; neither case proves a universal routing rule. The prefix defect was repaired in C; D must not attribute all later Dense weakness to that old defect.

Historical cache p50 1,558→238 ms describes same-corpus service timings, not HTTP throughput. The later acceptance recheck was run alongside tests and is a separate observation. Accepted regression was 195 passed/3 skipped; CI's smaller count reflects its documented platform selection. None is a new D result.

Existing verification source inspected: `tests/test_persistent_financial_index.py` covers exact BM25/filter parity, asymmetric prefixes, restart, incremental reuse, failed publication, concurrent build, drift/membership and tamper rejection; `tests/test_financial_hardening.py` covers auth, owner lock/recovery, retained-generation cleanup and provenance cache/TOCTOU; `tests/test_sec_table_context.py` covers multi-level headers, row axes, numeric attributes, footnotes and continuation. These fixture tests do not establish natural-language financial understanding. `scripts/evaluate_persistent_financial.py` checks a frozen query hash/model/manifest and uses binary relevance plus query-resampled bootstrap. D proposes graded qrels and issuer-cluster paired uncertainty separately; its future metrics must not be silently substituted into C results.

## Problem boundary and questions

Current retrieval returns traceable evidence, not verified financial answers. Filings may remain `PARTIAL_EXTRACTION`; table-level `OK` does not certify full filing extraction. Fiscal labels do not alone resolve every comparative column. There is no persistent-path intent router, explicit semantic cell-period alignment verifier, or source-bound calculation contract. Limited issuers, sampled corpus, small correlated query counts, local single-owner Qdrant and retained-generation growth constrain claims.

| RQ | Motivation and hypothesis | Independent variable / comparator | Dependent variables / falsification | Data, scope and risks |
|---|---|---|---|---|
| D1 query understanding | Explicit issuer/period/intent resolution may reduce wrong-context evidence | Deterministic parsing+resolution on/off, same BM25 candidates | Slot accuracy, wrong-period rate, R@5; falsified if no improvement or more false exclusions | New mixed fiscal/calendar/ambiguous questions; issuer aliases and comparative periods can mislead |
| D2 table evidence | Compact structure-preserving views may improve evidence selection | C row view vs versioned compact row; unchanged model and router | R@5, cell/period alignment, truncation, bytes; falsified by lost context or no quality/cost benefit | New six-table-family evidence; incomplete headers/footnotes risk false certainty |
| D3 adaptive retrieval | Conservative routing may keep exact-query strength and help paraphrases | BM25, Dense, fixed RRF vs bounded policies in 06 | Paired R@5/nDCG, category regressions, latency; reject if guardrails fail | Fresh issuer-held-out data; lexicality heuristic may misclassify intent |
| D4 grounded QA | Source-bound deterministic checks may reduce accepted wrong numbers | Same retrieved evidence and draft, verifier off/on in offline evaluation | Supported numeric correctness, unsupported claims, coverage/abstention; reject if safety gain is absent or usable coverage collapses | Later labeled numerical/summary subset; retrieval failure cannot be repaired by arithmetic |
| D5 cost/utility | Selective Dense and bounded verification may offer a better quality/cost trade-off | Matched corpus/config workloads for shortlisted methods | Warm/cold p50/p95, RSS/VRAM, failures, build/disk; reject if budget exceeded or no Pareto value | Owner's 8 GB RAM/4 GB VRAM; estimates require live measurement later |

Expected scope is contracts → derived evidence → one bounded retrieval experiment → optional grounded QA → independent evaluation. Contribution candidates are the combination and reproducible negative/positive findings for source-bound SEC evidence on modest hardware; global algorithmic novelty is not established. Detailed acceptance/stop rules appear in 08–13.
