# Preregistered evaluation design

**Plan only, not a frozen new dataset.** No D queries, qrels, source collection or scores have been created. This protocol is ready for owner review; execution and dataset acquisition require separate authorization. Selection/freeze precedes rankings. Existing C evaluation bytes stay unchanged.

## Contamination boundary and proposed splits

Original14, intermediate16, MSFT/KO dev8 and NVDA/WMT heldout16 are all consumed. AAPL/TSLA and all documents/near-duplicate amendments used in those sets are excluded from fresh evaluation. They remain compatibility/development diagnostic material with labels disclosed. Audit every old manifest/query artifact before declaring any new issuer untouched; the names below are provisional until that audit.

Proposed manageable pilot: eight new issuers, two source documents each (10-K and 10-Q from distinct report periods), plus original/amended pairs where actually available. Development JPM/PG; validation COST/INTC; final held-out HD/PEP/ADBE/ORCL. This is an intentional sector/form/fiscal-calendar spread, not a claim of corpus availability. Check official SEC metadata and licensing/access policy before acquisition. No download or source ingestion is authorized by this blueprint.

Group all documents, comparative tables, amendments and paraphrases of a source fact from one issuer into one split. A paired amendment adds a third document where needed (target16–20 documents total). Require at least one real linked original/amended pair in validation and one in holdout; if unavailable, propose substitutions based solely on documented availability before query authoring or rankings. If absent, mark that stratum blocked, do not synthesize real amendment evidence or claim its evaluation passed. Record exact accession, form, reporting dates, filed date and selection reason. Prior ingestion quality is an inclusion diagnostic, never a ranking-based convenience filter.

Target144 authored questions:36 dev,36 validation,72 holdout. Twelve primary categories, each3/3/6 questions across splits; secondary tags may overlap but each query has one primary denominator. Distribute across all split issuers/forms; do not let one source dominate. Budget24 human hours minimum for initial annotation plus adjudication; revise scope transparently if infeasible. Holdout has only four issuer clusters: confidence intervals are unstable; this is a pilot, not a strong population-generalization study.

| Primary category | Required distinctions / relevant evidence |
|---|---|
| Exact financial figure | Named line item, value, unit and period; strong lexical control |
| Semantic paraphrase | Human paraphrase without copying row label; same source facts grouped |
| Financial table context | Caption/header/row-group dependency; lexical labels alone insufficient |
| Multi-period | Instant/duration and comparable periods; all required operands |
| Accounting terminology | Source policy/definition text, not LLM world knowledge |
| Segment reporting | Consolidated vs segment, named segment, measurement basis |
| Negative value | Display parentheses/inline sign; raw source annotation |
| Percentages | Relative percent vs points, ratio/unit and denominator |
| Original/amended | Linked accessions and explicit version/as-of request |
| Cross-section evidence | At least two source sections with necessary evidence groups |
| Ambiguous question | Expected clarification, multiple plausible scopes documented |
| Insufficient evidence | Known absent period/item or unusable extraction; expected abstention |

Do not force artificial category counts by mislabeling sources. A source-availability audit may amend counts before freeze, with reason; otherwise block missing strata. English primary; Vietnamese paraphrases, if added, are separately labeled exploratory and grouped with their fact families.

## Source-grounded judgments

Two annotators independently inspect retained source HTML/table and parsed representation without seeing retrieval outputs or model answers; adjudicate disagreements with a source-based record. If only one annotator is available, use delayed reannotation and report the limitation; no claim of independent dual review. Every answerable query stores acceptable scope, required evidence groups, parent chunk IDs, exact row/column/paragraph locators, units/signs/periods, extraction warnings, raw supporting excerpts and human rationale. Relevance:2 directly necessary,1 useful supporting context,0 irrelevant/wrong period/basis. Alternative valid sources within the frozen scope are recorded, not only a single preferred row.

For multi-operand questions record AND-groups of required operands, with OR-alternatives within each. Conventional chunk Recall@k and full evidence-group coverage@k are both reported; finding one of two operands is not complete answer support. Ambiguous/unanswerable queries have no forced relevant chunks: exclude from positive recall denominators and report clarification/abstention separately. Do not count absence in a small candidate pool as evidence that a question is unanswerable.

Qrels completeness: manually review source regions for each question and perform blind pooled relevance review across all preregistered arms before scoring, without exposing arm identities. Lock augmented qrels before computing method metrics; record every addition and audit against source. If a genuinely missed relevant item appears after release, preserve original evaluation, version corrected qrels and rerun all arms uniformly with disclosure; do not selectively upgrade one method. No LLM answers, citations or judgments serve as ground truth.

## Freeze contract

Before any new rankings freeze a signed/versioned run manifest containing:

- Raw source bytes and SHA256; URL/accession, retrieval timestamp and SEC metadata; structured artifacts/chunks and canonical hashes; inclusion/exclusion audit and split mapping.
- Parser/chunker/representation versions; normalization/decoder rules; corpus membership; independent generation/collection identities per incompatible representation and split; no cross-split retrieval leakage.
- Model names/digests/dimension, document/query prefixes, Ollama/runtime versions, actual context/token options and truncation; CPU/GPU environment and dependency lock; exact code commit.
- Query JSON, qrels and evidence-group hashes; annotation guide/adjudication; split embargo; exact scoring scripts/metric conventions, seeds/config hashes and arm selection rule.
- B/D/F controls and at most one selected adaptive candidate; budgets, failures/timeouts, ties, rerank weights; answer prompt/verifier/rounding only if D4 separately authorized.

Raw-byte and canonical LF-normalized hashes must be distinguished for portable JSON/Markdown. Never regenerate a timestamp-bearing manifest and call its raw hash identical. Historical C canonical hash references remain in its freeze document. Dataset freeze is an approval checkpoint, not accomplished by writing this protocol.

## Metrics and statistics

All answerable queries: Recall@5/@10 (binary relevance≥1, also direct-only≥2 sensitivity), Precision@5 (divide by5, missing slots count zero), MRR@5 (first direct-relevant rank), nDCG@5 (gain `2^rel-1`, ideal from complete qrels), evidence-group coverage@5/@10 and query-level failures. Zero-ideal queries are reported separately. Provenance validity = verified returned chunks / all returned chunks; additionally report verified-complete-query rate so empty answers cannot score perfectly. Save per-query ranks and traces, not only averages.

Answer metrics later: all-query supported correctness and conditional answered accuracy, numeric/unit/sign/period correctness separately, citation support per claim, unsupported-claim rate, appropriate abstention on unanswerable and false abstention on answerable queries. Report coverage and risk-coverage curves; fixed human-approved rounding tolerances per unit/source precision. Human judges blind to method; disagreement and adjudication counts reported.

Paired per-query differences for every method comparison. Primary endpoint Recall@5 of one selected candidate vs B; secondary nDCG@5, exact-category noninferiority and cost guardrails. Validation selects the candidate; final holdout runs once without tuning. Bootstrap10,000 replicates seed20261025 resampling issuer clusters, retaining each issuer's question/fact families, for95% intervals of paired differences; also show issuer-level and category-level scores. With only four holdout issuers this interval is descriptive and cannot certify broad generality. No independent-query t-test treating paraphrases as unrelated. Any randomization sensitivity is clustered, not per paraphrase. Exploratory multiple comparisons are labeled; Holm adjustment if reporting confirmatory tests for several methods/endpoints. Lack of significance is not equivalence; noninferiority margins need owner agreement and sufficient data, otherwise conclusion is inconclusive.

## Operations and reproducibility boundaries

Same frozen corpus, warmed model, shuffled fixed query order seed above. Five warmups, then five repeats per answerable query per arm, single concurrency primary. Cold runs: ten fresh-process trials labeled whether OS/model caches are actually cold; never assert cold disk if not controlled. Report distributions across requests and per-query medians; repeated timing samples do not increase independent quality sample size. Separate core search, service (including provenance), HTTP end-to-end, UI interaction and answer generation.

Measure normalization, resolution/filtering, BM25, Ollama connect/identity, embedding, Qdrant, fusion/rerank, provenance byte-hash vs cache reconstruction, serialization and total; stage wall times may overlap and must not be double summed. Compare localhost/127.0.0.1 on identical reachable endpoints via counterbalanced runs, keep-alive/session settings held fixed. No DNS conclusion from one observation. Record cache disabled/cold/warm, returned evidence count/bytes, failures/timeouts, RSS/peak RSS, VRAM, CPU, disk bytes per generation, build time and embedding reuse; optional concurrency2 only after memory budget passes. No historical timing baseline replacement.

Reproduction deliverables later: immutable manifest+queries+qrels+config+environment, exact commands and log hashes, per-query result JSON, stage timings, failure inventory and human annotation audit. Current work produces their specification only. See 09 for controlled ablations and 10 for bounded resource stops.
