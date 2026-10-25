# Owner and supervisor decision memo

**MILESTONE_D_BLUEPRINT_READY_FOR_OWNER_REVIEW.** This means the design package is ready to review, not that implementation, a dataset freeze or any improvement has been accepted. **DESIGN ONLY — NO MILESTONE D IMPLEMENTATION AUTHORIZED.** Keep Hybrid Search for Financial Intelligence as the project identity, with BM25 as the current recommended default and honest negative Hybrid findings.

## Ten decisions

1. **Why D?** C established usable persistent evidence retrieval for a limited local pilot. It did not establish reliable paraphrase/table retrieval, automatic period resolution or financial-answer correctness. D should test those gaps independently before adding product complexity.
2. **Which shortcomings?** Dense ranking weakness on table-heavy questions; shared irrelevant candidates promoted by fixed RRF; verbose row representations; missing explicit intent/cell-period contracts; no source-bound numeric checker; small consumed evaluation sets. Some causes remain hypotheses, not confirmed model incapacity.
3. **Central contribution?** A falsifiable, source-bound study of conservative query-aware Hybrid retrieval and table evidence under a local resource budget. Optional numeric verification is downstream. Do not claim invention of row chunking, RRF, adaptive RAG or calculator agents.
4. **Minimum scientific experiment?** Fresh issuer/source split and human qrels; matched B/D/F and one preregistered conservative finalist; per-query errors, paired uncertainty, provenance and latency. A negative result retaining B is valid. No answer model is required.
5. **Minimum usable product?** Existing Financial Search plus explicit scope/period clarification and compact source table evidence, with partial-extraction warnings and traceable locators. Optional answer extraction/comparison only after separate correctness gates; a generic chatbot is not the objective.
6. **First component?** D1 contracts and deterministic resolver fixtures; prepare evaluation freeze conventions before ranking. Resolve fiscal/calendar, comparative columns and amendments before spending on fusion.
7. **Postpone what?** Learned router, neural reranker, multiple table-vector channels, multi-agent critic loops, fine-tuning, broad issuer expansion, distributed operation and automatic financial advice. D4 prose generation is optional after retrieval evidence.
8. **What disproves the approach?** No fresh-split quality benefit under exact-query/cost guardrails; scope exclusions lose relevant evidence; table compaction loses units/headers; verifier passes wrong operands or achieves safety only by abstaining almost always. Keep original baseline and report failures.
9. **Resource/schedule risks?** 8 GB RAM/4 GB VRAM, sequential model use, source/amendment availability and independent qrel reviewers.20–33 focused days is an estimate; small issuer counts limit inference. Stop on resource/source/safety gates in10–11.
10. **What needs explicit authorization?** D1 code/tests, new source acquisition and dataset freeze, D2 derivative artifacts or re-embedding, D3 ranking runs, D4 answer interface/model calls, migrations/new collections, additional model downloads, paid/cloud use and any deletion. This Draft PR authorizes none of these. Owner may approve D1 alone and defer later stages.

## Architecture alternatives

| Choice | Flow and complexity | Research value | Resource/risk | Recommendation |
|---|---|---|---|---|
| A conservative BM25-first adaptation | Resolve scope→BM25; conditional Dense; bounded fusion/table rerank; optional deterministic answer checks | Directly tests whether modest adaptation helps without discarding strong lexical behavior | At most one embedding per query; existing index plus candidate-time views; misrouting/count heuristic still risky | **Primary.** Best match to accepted evidence and hardware; simple controls/falsification |
| B multi-channel adaptive search | Simultaneous lexical, dense row, table-summary/cell candidates; learned or richer routing/reranking; optional agent answerer | Can explore representation/channel interactions if A cannot address measured errors | More indexes/embeddings/candidate normalization, annotation and inference; hard attribution, overlap bias and memory risks | Viable later design, contingent on evidence and new approval; not minimum D |

Architecture A preserves C storage/provenance/lifecycle and isolates legacy Chat/RAG. Design B would need a distinct versioned experiment namespace and additional fair canonical-parent deduplication. Neither design is promised to outperform BM25. Primary reason for A is lower experimental complexity and fit to evidence, not an unmeasured speed claim.

## Proposed owner approval record

Owner/supervisor should approve or revise: fresh issuer/form availability policy; reviewer availability;144-question scope; four-cluster holdout limitation;0.02 exact-recall margin and other06 thresholds; local resource caps; D1-only next authorization; D4 optional boundary; code reuse/license constraints for the demo; publication claims/negative-result policy. These are open execution decisions, not missing contents of this design. No holdout or new model is represented as frozen today.

## Review gates and artifacts

Statuses refer to this research task. `VERIFIED` means an inspection or design artifact exists, not that the proposed component works. Literature transfer, source availability and future performance remain limited or untested.

| Gate | Status | Evidence / qualification |
|---|---|---|
| RD01 accepted C baseline | VERIFIED |01 records fetched baseline `d1d5195…`, accepted merge `69e6866…` ancestor and C acceptance |
| RD02 source architecture | VERIFIED |01,03,05 inspect actual ingestion/index/API/UI/provenance source at baseline |
| RD03 literature | VERIFIED_WITH_LIMITATIONS |02 primary-source ledger; source-setting results, publication/access limits explicit |
| RD04 required paper | VERIFIED_WITH_LIMITATIONS |02 arXiv record/v3 method/data/metrics reviewed; no local replication or established proceedings record |
| RD05 second repository | VERIFIED |02 static code comparison at `87681e11…`; runtime/results not reproduced |
| RD06 hypotheses | VERIFIED |01 RQ-D1–D5 IV/DV/baseline/data/falsification;12 claim limits |
| RD07 query design | VERIFIED |04 contracts/rules/scope/fixture and measurement plan |
| RD08 table design | VERIFIED_WITH_LIMITATIONS |05 six retained-source family examples, including operations/component notes; no full-filing extraction claim |
| RD09 retrieval alternatives | VERIFIED |06 seven bounded arms, exact rules/ties/cost/failure and overlap analysis |
| RD10 grounded QA boundary | VERIFIED |07 source-bound operand checks, supported operations and abstention; not implemented |
| RD11 evaluation protocol | VERIFIED_WITH_LIMITATIONS |08 fresh split proposal, annotation/freeze/stats; source availability and future qrels not verified |
| RD12 ablations | VERIFIED |09 controlled contrasts, optional fixed-draft verifier ablation |
| RD13 resource budget | VERIFIED_WITH_LIMITATIONS |10 explicit local envelope/estimates; no new runtime measurement |
| RD14 claim matrix | VERIFIED |12 distinguishes accepted observation, literature, hypothesis and unsupported speculation |
| RD15 owner memo | VERIFIED |This memo answers ten questions and compares two architectures |
| RD16 research-only Draft PR | VERIFIED |[Draft PR #9](https://github.com/Doquocdung1609/tinyllama-fastapi/pull/9), open/unmerged, correct research head and accepted target;13 new documentation files only |

## Inspection and delivery record

Inspection commands included `git status --short`, `git fetch origin --prune`, `git rev-parse HEAD`, `git merge-base --is-ancestor`, `git branch --show-current`, `rg` and source reads; read-only SQLite queries extracted examples. External paper records/full text were browsed; no unrelated secondary summaries were used as authority. No tests, models, benchmarks or app services were run for this design-only change. Accepted C test results are inherited historical evidence, not claimed as rerun.

Research branch: `codex/topic3-milestone-d-research-blueprint`, target `codex/topic3-milestone-b-sec-corpus`. Delivery validation must check exactly13 new Markdown files, local links and diff whitespace; ensure all changed paths are under `docs/topic3/milestone_d/`, accepted artifacts/main unchanged, clean worktree after commit, Draft PR open/unmerged with correct base/head. Final commit and PR identity are supplied by GitHub/Git at delivery; do not put a self-referential commit hash inside its own content.

Delivery check:13-document inventory, balanced Markdown fences, all relative links resolved, only permitted new paths and `git diff --cached --check` passed. Initial research commit `7210e477cb26f5e11cc0105c283d8a305ffc5dd8` was pushed normally; GitHub created [PR #9](https://github.com/Doquocdung1609/tinyllama-fastapi/pull/9) as Draft, open and unmerged, base SHA `d1d5195b26f77d8fb25c830229c4c3693d4b638f`. This delivery-record update is a subsequent documentation commit. Git warned about future LF→CRLF checkout conversion for these new Markdown files; no historical file was rewritten. No runtime regression was rerun for a documentation-only diff, and no CI success is asserted by this record.
