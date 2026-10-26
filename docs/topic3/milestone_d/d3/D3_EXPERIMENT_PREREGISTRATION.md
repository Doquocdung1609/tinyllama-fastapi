# D3 bounded experiment preregistration

Blueprint06/09 inspected before policy implementation. Seven arms only; no learned router, new model or weight sweep. k1=1.5/b=.75 accepted C,40 candidates/channel, RRF60, top5/10, table top20, row/role0.05. A exact/table≥5 positive hits uses B; otherwise fixed2:1 exact/table/comparison,1:1 semantic/cross-section. R routes by D1 category; unresolved scope stops. Unknown finite terminology is a documented risk, not tuned after results.

Selection guardrails fixed before any fresh ranking: no source/scope safety regression; exact and overall Recall@5 within0.02 of B; nDCG improvement>0; paraphrase Recall@5 gain≥0.05; p95≤1.5×F. All baseline availability/category/resource prerequisites must hold; otherwise no finalist. Frozen protocol selected_finalist=null because these prerequisites were unavailable. No winner was selected from favorable dev outputs.

Before ranking, acquisition plan fixed JPM/PG dev, COST validation, HD heldout, one latest eligible10-Q each,4MiB/document,1request/s,0retries,10s requests. JPM exceeded budget; fixed remaining groups were retained. v1 probe incorrectly treated that local budget failure as global source failure; v2 classification preserves v1, records the size cause and continues only the fixed plan. No result-guided source substitution.

Feasible diagnostic reduction is explicit:3 issuers/3 documents,5dev+6validation+5heldout questions, exact literal table-row category only, versus planning144/12categories. Mechanical qrels contain every exact-matching row-label parent in its filing, grade2; one OR-group per row metric. No generated answer or numerical financial claim is ground truth. Human annotators0; no independent human adjudication. This is an exploratory source-backed retrieval diagnostic, not the full proposed financial evaluation.

`prepare_research_dataset` writes immutable raw/structured/chunk/manifests/query files and freeze before index/ranking. `run_d3_diagnostics --freeze-protocol` hashes all D3 runtime metric/policy modules before ranking. Dev/validation runner cannot select heldout. Heldout remains embargoed until D5. Initial preparation caught a string-versus-enum status assignment before writing the freeze; the enum repair and repeat-write protection are regression-tested. No owner source was reingested.

Required broader source judgements, period/paraphrase/negative/amendment strata and all B/D/F comparisons remain blocked. New diagrams/docs cannot supply that missing evidence. No consumed C query or qrel was used to tune policy.
