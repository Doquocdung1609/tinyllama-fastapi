# D5 frozen evaluation — narrowly scoped negative result

## Freeze and one-shot method

D5 runner `scripts/run_d5_frozen_heldout.py` was committed at `0922524475a26a0bc18e077e3256edeba982e1c0`; preregistration was committed at `2e6a343b0b215d3ddd545300ca65f54333870850` **before held-out opening**. The preregistration's SHA-256 is `ce2c362b9cf894b523ec47b1cd6bae87b8f377e5cdc8cc9275247b7a369e71c7`; frozen held-out query/qrel bytes hash `70c52b601f3da535ad12d0041abf04df73832f8e9681058ae73e928e0e5bf843`. The runner verifies the frozen D3 code hash, protocol, policy, no adaptive finalist and D4 configuration. It creates an exclusive access marker before reading held-out bytes; one successful v1 evaluation was run. Both marker and source files remain in the isolated, owner-marked research root, separate from historical owner data.

Data: one Home Depot 10-Q, CIK `0000354950`, accession `0001628280-26-058715`, source SHA-256 `3d638bc025ef9643317d539f63c3891c8db9b47e35a8edd8040928704d0703f1`. Five queries are mechanically labeled from exact source row labels, **zero human adjudicators**. No paraphrases, issuer diversity within held-out, filing-version distinctions or real numeric QA labels. The original accepted C 14-query set and D1/C evaluation artifacts were not used for tuning or changed.

## Results

Raw per-query ranks, candidate IDs, scores, source locators, failures and metric calculations: `D5_FROZEN_HELDOUT_RESULT_v1.json`. BM25 succeeded on 5/5: Recall@5 `0.685714`, Recall@10 `0.809524`, Precision@5 `0.24`, MRR@5 `0.70`, nDCG@5 `0.670731`, group coverage@5 `0.80`, @10 `1.00`. Dense 0/5 valid runs and fixed RRF 0/5 valid runs because the isolated research snapshot is lexical only and Ollama was unavailable; their zero-filled failure-inclusive metrics are **availability diagnostics, not retrieval-quality estimates**. No adaptive finalist qualified in D3, and none was selected after seeing held-out output. No BM25/Dense/Hybrid superiority claim follows from this result.

Per query BM25 Recall@5: net sales `0/9`; total assets `1/1`; current liabilities `1/1`; operating income `3/7`; cash and cash equivalents `1/1`. For net sales, the first three BM25 hits were filing/section text matching the terms and the first exact `Net sales` row was ranked seventh; this is a confirmed lexical ranking failure on the auto-labeled set. Several qrel groups contain multiple literal-label rows, and automatic labels have not been adjudicated for accounting relevance. Across the one held-out issuer cluster, an issuer-cluster confidence interval is **not estimable**. Paired B−D/B−F differences would mostly encode channel failure and are not interpretable as ranking lift.

## Evidence and QA boundaries

All 3 newly acquired official SEC source byte hashes rechecked against the frozen manifest. C provenance checks bound retrieved parent chunks to those bytes. Real D2 exact cell, sign, unit and period correctness: **NOT MEASURED**, as all new sources exceed D2's 250 KiB context cap. D4 real numeric answer accuracy: **NOT MEASURED**; the real local API returned source evidence and abstained. Synthetic QA 4/4 answerable correct and 4/4 unanswerable abstentions (`D4_SYNTHETIC_QA_EVALUATION_v1.json`) remain separate. Offline same-bundle verifier ablation rejected 5/5 deliberate synthetic forgeries while an unchecked draft path would accept them (`D5_VERIFIER_ABLATION_v1.json`); this is not a real LLM comparison.

No retrieval or verifier parameter was tuned on the held-out result. The accepted Milestone C conclusion, BM25 as recommended default on its own evaluated corpus and no demonstrated Hybrid superiority, remains unchanged.
