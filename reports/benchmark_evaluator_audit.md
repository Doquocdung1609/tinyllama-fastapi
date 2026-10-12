# Benchmark evaluator audit

## Previous weaknesses

- C05 checked only that `table:p1:t2` occurred in selected evidence.
- C09 checked only rewritten-question text and the existence of any citation.
- HTTP 200, evidence retrieval, prompt inclusion, factual correctness, answer completeness and citation support were not separated.
- Keyword checks did not require every mandatory claim or numerical value.
- Service outages could appear as answer failures without a distinct failure category.

## Strict schema

The repaired CSV records test/document/hash/conversation identity, gold pages and claims, selected evidence, actual prompt evidence, user answer, seven independent correctness dimensions, strict status, failure category, latency, model and code commit. PASS requires all mandatory dimensions. Correct refusals are scored as refusals. A citation is correct only if the cited source supports the tested claim.

Gold values are maintained independently in the benchmark script or fixture ground truth. The generation model is not used as the grader. Disagreements are resolved against original PDF text and structured source cells.

## C05 contract

Mandatory: resolved table 2, exact `table:p1:t2` prompt/source, subject Dòng tiền, periods 2023/2024, values 20/28, explicit unit status, and a supporting citation. Merely retrieving table 2 cannot pass.

## C09 contract

Mandatory: prior claim 15 retained as hypothesis, status CONTRADICTED, exact source value 16, source cell metric/year/value, answer states the claim is wrong, and citation resolves to the table containing that cell.

## Interpretation

Development questions seen during repair are regression data. `real_pdf_generalization.csv` is a newly selected real-report evaluation. `internal_holdout_results.csv` is labeled INTERNAL_HOLDOUT; it is not external certification. Any case used for a subsequent code change must leave holdout status and become regression data.
