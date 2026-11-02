# Topic 3 V6 acceptance and release recommendation

**Overall: EVALUATION_PENDING_HUMAN_REVIEW.** This V6 continuation delivers the executable source-first review infrastructure, frozen algorithms, genuine live pilot, exposed ablations and product QA. It does not deliver independent financial-cell gold or an unbiased final effectiveness score. Keep the stacked PR in Draft; do not merge automatically.

| Gate | Result | Evidence / exact limit |
|---|---|---|
| G0 V5R checkpoint verified | PASS | PR #32 HEAD `571750b`; 8,670 points per index; 3,516 fiscal payload differences; 480 author-method live results; P5 A 150/150, P7L B 90/90, P7L A 88/90 order matches. P3C equivalence remains unproved. |
| G1 Algorithm freeze and leakage boundaries | PASS | Freeze commit `65c32e5`; SHA-256 `d997b79fdad3ecdbf8d0663bcea6f69c77062e3dd8809dcbe181d721421033d0`. Old 15 exposed, old 30 pilot, fresh 30 final-review design separated. |
| G2 Source-first packets and human judgment | PARTIAL | 60 machine-prepared packets, 340 candidate rows validated against 13 SEC HTML snapshots; **0 independent human judgments**. |
| G3 Untouched held-out baseline vs FAITH-R | PENDING HUMAN REVIEW | Fresh 30 questions SHA-256 `01e841d14692477512f1029f2638f353765a9a59f44379dc09783e78bcdcab79` (LF-normalized); no algorithm run on this final split. Pilot 300 live runs are unjudged and explicitly exploratory. |
| G4 Financial-cell and answer accuracy | PENDING HUMAN REVIEW | 0 independently verified cells; all live research hits `UNVERIFIED`; no Recall/MRR/nDCG or answer-accuracy number claimed. FY2037 abstention observed on one negative API probe. |
| G5 Ablation and compute trade-offs | PASS for exposed development only | A0–A5, A4R, feature removals, A2/A3 and A4 budget 10/20/50/100. At k100 A4 known-positive Top-1 drops to 9/15; sidecar scan and memory cost disclosed. No independent effectiveness conclusion. |
| G6 Product regression and browser | PASS with scoped V6 QA | 736 pytest PASS, 1 known deprecation warning; React build PASS; Playwright Research Lab PASS; Prebuilt readiness PDF/OCR/SEC READY; fresh PDF/OCR upload not rerun. |
| G7 Transparent scientific report | PASS | `V6_THESIS_DEFENSE_REPORT.md` separates author critique, metadata repair, retrieval contribution, reused product features and unresolved scientific validity. |

## Exact owner/group review task

Assign two independent human reviewers to the 30 fresh packet HTML files in `V6_FRESH_HOLDOUT_REVIEW_PACKETS/`. For each, open the linked original SEC filing and record answerability, accession, exact statement/row, fiscal column, value, unit/scale, source span and label. Resolve disagreements with a third reviewer while preserving both initial decisions. Freeze the resulting qrels/answer cells with a checksum before running the final algorithms. Then compare all ten locked methods on the same B index, report paired per-question findings and uncertainty. Any post-outcome repair requires a new untouched split. The pilot 30 may be used to rehearse this workflow, never to certify independent success.

No Qdrant snapshot, SEC raw corpus, model cache, secret or private workspace was committed. The product and Ollama are stopped after QA to avoid leaving background load on the owner laptop. No PR was merged.
