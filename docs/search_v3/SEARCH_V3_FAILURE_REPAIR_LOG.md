# Search V3 failure and repair log

|Family|Source finding / layer|Repair / counterexample|Final result|
|---|---|---|---|
|F1 Income statement|HPG original page5 has pretax and financial-income rows;V2 early guard/hard filtering hid them|Related retrieval separated from answer eligibility;source-title OCR-tolerant candidate metadata;raw labels/values never rewritten|q015/q021/q022 now have source R@5=1;unverified income cells remain unverified|
|F2 Metric disambiguation|Nested fixed/intangible/current assets and revenue types|Existing distinct ontology retained;additive controlled aliases/fuzzy row candidates only;exact longer concepts dominate|Functional counterexample tests PASS;not universal coverage|
|F3 Cross-page|Assets and liabilities/equity on separate HPG pages|Multi-metric candidate diversification;source operands retained individually|q066 source coverage R@5=1;not an automatic accounting calculation|
|F4 SEC|PG main NET SALES row exists;accepted parser heading is company name rather than statement title|Read-only authenticated-parent reranking,exact-label preference and sibling-concept statement candidates;no generation/header/value fabrication|q059/q060/q062 recovered within5;q061 still misses5;all SEC results remain non-numeric source evidence|
|F5 False abstention|Natural capitalization/ordinary phrasing triggered V2 filters;CEO 'của CEO vào cuối năm' initially declined a reviewed cell|Retain related sources;clarify eligibility separately;generic 'vào' is allowed|2reviewed development asset queries eligible;retrieval empty-result rate alone does not prove relevance|
|F6 Entity/scope/basis|A post-freeze 'Apple total assets...' and Vietnamese variant falsely inherited HPG cells|Critical conservative unresolved-query vocabulary eligibility guard;uppercase/lowercase/no-preposition regression|4new probes,17source cases,3Decimal checks PASS;V3.1 freeze invalidated and36labels demoted|
|New unseen extraction gap|SEM pages7/8/9 have native headers but image statement bodies;all7gold values absent from checkpoints|No post-test repair/tuning;preserve failed source evidence and images|FAIL financial extraction completeness;requires a separately validated mixed-image extraction repair|

The unsafe V3.1 code/lock and first labels are in archive/POLICY_V31_INVALIDATED.zip and V31 manifests. No36-query measurement was executed under that unsafe policy. Final24source-unseen queries were annotated after the repaired freeze and executed without a policy change. Some final misses are genuine extraction defects;other false matches/abstentions are provisional until independent source adjudication. No labels were changed to raise the candidate's score.

Actual70-query V2 regression findings (exposed,not independent):

- q015: R@5=1.000,MRR@5=1.000.
- q021: R@5=1.000,MRR@5=1.000.
- q022: R@5=1.000,MRR@5=1.000.
- q059: R@5=1.000,MRR@5=0.250.
- q060: R@5=1.000,MRR@5=0.250.
- q061: R@5=0.000,MRR@5=0.000.
- q062: R@5=1.000,MRR@5=0.250.
- q066: R@5=1.000,MRR@5=1.000.

Product regressions:651backend PASS (1Starlette/httpx deprecation warning),7frontend PASS,TypeScript/Vite build PASS,pip check PASS. Windows Prebuilt source/highlight/worker MIME/baseline comparison/in-flight stale-response test PASS36.6s;separate unreviewed candidate-row test PASS3.5s. Six real screenshots are retained. Node warned NO_COLOR is overridden by FORCE_COLOR;not a product failure. Source-image/current-prior/currency boxes are not all independently reviewed. No independent owner audit was invented.
