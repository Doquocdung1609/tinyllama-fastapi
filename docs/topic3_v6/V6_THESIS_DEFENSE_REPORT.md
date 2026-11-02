# Instructor-facing defense: Fiscal-validated Attribute & Table-aware Hybrid Retrieval

## Author claims → code audit

The pinned author's six search methods execute on genuine SEC filings. Its Stage-2 `NeuralReranker` path is a fixed extractor/feature score, not an executed ColBERT model. Its text chunker does not establish a verified row × fiscal column × unit × value relation. The original evaluation uses self-derived keyword terms; a universal precision guarantee is unsupported by its code or the observed failures. These are methodological critiques of the author, documented with source paths and hashes in the checkpoint/code audit, not claims about its intentions.

## Verified counterexamples → hypotheses

The restored A index has incorrect fiscal metadata on 3,516 of 8,670 points; B changes only that payload field. Saved P7L target-filing Top-10 moves from 0/90 on A to 90/90 on B across six author methods. This suggests a metadata defect can dominate financial retrieval even when text/vectors are unchanged. On exposed development questions, original unfiltered BM25+Dense often selects another filing, and relevant-looking passages can lack the exact requested cell. Amazon's percentage/expense passage, Meta's 2025 CAPEX forecast and Tesla's narrative without an aligned amount are concrete cases.

Hypothesis: issuer/fiscal constraints improve *filing selection*; same-corpus row-like candidate expansion improves *candidate entry*; metric/row signals improve *ranking*; verified financial answering additionally requires source-cell parsing and human-reviewed ground truth. Each is a separate question. Better accession hit cannot be substituted for correct answer.

## Experiments → improvements and trade-offs

Index A/B all-point validation found identical point IDs, text and vector signatures, with fiscal metadata-only changes. The six original methods were rerun live 480 times on P5/P7L. P5 A matches historical Top-10 150/150, P7L B 90/90, P7L A 88/90. Two A differences are near-tie rank inversions; exact P3C equivalence remains unproved.

On 15 **exposed, incompletely judged** P7L/F10 questions, A0/A1/A2/A3/A4/A5 known-positive Top-1 is 1/1/3/3/10/10; Top-10 candidate entry reaches 15/15 in A3. A4R is a post-hoc repair reaching 13/15 Top-1 on the same exposed cases but regressing Amazon FY2023 from YES to UNJUDGED. Removal of A4 metric-relation features returns Top-1 to 3/15; issuer/fiscal feature removal has no additional effect once A2 hard filters them. Larger A4 candidate pools can lower Top-1 from 10/15 at k=10 to 9/15 at k=100. A3 incurs a full 8,670-payload sidecar scan and increased memory. No A4 column-year or unit feature actually exists, so such ablations were not fabricated. A5 verifies zero financial cells.

V6 froze all candidate code first, prepared 60 source-first review packets with 340 table-row candidates checked against 13 official SEC snapshots, and ran 300 live searches on 30 **unjudged pilot** questions. The only pilot proxy is whether a preselected accession appears: original BM25+Dense 16/29 at Top-1 versus A2 25/29 and A4R 29/29. The hard issuer/year filter directly favors this proxy, and a correct filing may still contain the wrong row or value. This is **not independent relevance improvement**. The 30-question fresh final split has been frozen but deliberately not queried or scored.

## Independent evaluation → scientific validity limit

Zero questions have been independently adjudicated; zero exact financial cells are certified. Therefore ordinary Recall/MRR/nDCG, financial-cell accuracy, answer accuracy and a confidence interval for improvement are **pending**, not zero-valued results. The group must have two human reviewers inspect original SEC filings independently, record exact row/column/value/unit and answerability, resolve disagreements, freeze qrels by hash, then run the untouched final split once. Any repair after its outcomes requires another fresh split. Thirty questions from six filings remain a small, clustered sample even after review; uncertainty must be reported.

## Contribution boundaries

The new research contribution is the fiscal-validated filter, same-corpus table-aware candidate sidecar and transparent metric/row reranking, together with explicit separation of retrieval, source evidence and answer verification. Correcting fiscal metadata is a **data repair**, not proof of a new ranking algorithm. V4 React/FastAPI, Vietnamese PDF/OCR, Financial Assistant, Qdrant workspace, verified-cell answer logic and SEC viewer are **reused product infrastructure**, not newly claimed research results. The live Research Lab and source links make the comparison inspectable but are not scientific validation by themselves.

Recommendation: **EVALUATION_PENDING_HUMAN_REVIEW**. Present the code audit, genuine SEC counterexamples, locked algorithm, exposed ablations, independent-review protocol and unresolved limitations honestly. Do not present the post-hoc 13/15 or accession pilot 29/29 as an independently verified financial-answer success rate.
