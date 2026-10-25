# Milestone C source-grounded retrieval quality

The fourteen questions in [MILESTONE_C_QUERIES.json](MILESTONE_C_QUERIES.json) were manually labeled from original SEC table rows before the first retrieval benchmark and committed in bb60a82. Each includes relevant chunk IDs, exact source table/row locators, source values and URL. No LLM answer is relevance ground truth. The manifest, sampling policy, generation and file hash are pinned in [the benchmark](MILESTONE_C_BENCHMARK.md).

Coverage: Apple/company lookup, reporting period/form lookup, sales/assets/cash flow/shares/cash, exact amounts and percentage terminology; Tesla gross profit/receivables/revenue/debt; and amendment-specific shareholder ownership/fees. The target set is biased toward exact source-row retrieval. Some questions reuse facts; semantic alternatives may be relevant but unjudged. It is a development set, not independent holdout or a financial-answer test.

## Macro results at five

| Mode | Recall@5 | Precision@5 | MRR@5 | nDCG@5 | Source correspondence |
|---|---:|---:|---:|---:|---:|
| Previous lexical baseline | 0.911 | 0.271 | 0.786 | 0.822 | 100% |
| Formula/token-matched control | 0.911 | 0.271 | 0.786 | 0.822 | 100% |
| Persistent BM25 | 0.911 | 0.271 | 0.786 | 0.822 | 100% |
| Dense | 0.321 | 0.071 | 0.113 | 0.160 | 100% |
| Hybrid RRF | 0.714 | 0.157 | 0.613 | 0.627 | 100% |

Recall is known target IDs recovered divided by all labeled target IDs; precision counts judged targets divided by five. MRR uses the first judged target rank; nDCG uses binary relevance and the ideal ranking of up to five judged targets. Values are macro averages over 14 questions. Incomplete judgments penalize unjudged semantic alternatives, so these are not exhaustive relevance/precision estimates.

Every BM25 request produced exactly the formula/token-matched baseline top-five IDs, including deterministic ordering. Dense/hybrid outputs have no duplicate IDs and pass source verification. Source validity is assessed for returned evidence, not for all financial statements or absent answers.

## Per-query outcomes

| Query | Original recall/MRR | Persistent recall/MRR | Dense recall/MRR | Hybrid recall/MRR |
|---|---:|---:|---:|---:|
| aapl_sales | 0.750 / 0.500 | 0.750 / 0.500 | 0.000 / 0.000 | 0.000 / 0.000 |
| aapl_assets | 1.000 / 0.500 | 1.000 / 0.500 | 0.000 / 0.000 | 1.000 / 0.333 |
| aapl_cashflow | 1.000 / 0.500 | 1.000 / 0.500 | 0.000 / 0.000 | 1.000 / 0.250 |
| aapl_eps | 1.000 / 1.000 | 1.000 / 1.000 | 0.000 / 0.000 | 1.000 / 1.000 |
| aapl_period | 1.000 / 0.500 | 1.000 / 0.500 | 0.000 / 0.000 | 0.000 / 0.000 |
| aapl_numeric | 1.000 / 1.000 | 1.000 / 1.000 | 0.000 / 0.000 | 0.000 / 0.000 |
| aapl_percent | 1.000 / 1.000 | 1.000 / 1.000 | 1.000 / 0.333 | 1.000 / 1.000 |
| aapl_cash | 0.000 / 0.000 | 0.000 / 0.000 | 0.000 / 0.000 | 0.000 / 0.000 |
| tsla_profit | 1.000 / 1.000 | 1.000 / 1.000 | 0.500 / 0.333 | 1.000 / 1.000 |
| tsla_receivables | 1.000 / 1.000 | 1.000 / 1.000 | 1.000 / 0.333 | 1.000 / 1.000 |
| tsla_revenue | 1.000 / 1.000 | 1.000 / 1.000 | 0.000 / 0.000 | 1.000 / 1.000 |
| tsla_debt | 1.000 / 1.000 | 1.000 / 1.000 | 1.000 / 0.333 | 1.000 / 1.000 |
| tsla_amend_ownership | 1.000 / 1.000 | 1.000 / 1.000 | 1.000 / 0.250 | 1.000 / 1.000 |
| tsla_amend_fees | 1.000 / 1.000 | 1.000 / 1.000 | 0.000 / 0.000 | 1.000 / 1.000 |

BM25 leads this pilot. Hybrid loses exact-row targets/rank under fixed RRF k=60/candidate limit 40; the dense channel's semantic ranking does not align reliably with these narrow row judgments. These results do not isolate model, truncation, query instructions and annotation bias as causal factors. No inference is made that dense is generally inferior for financial language. No RRF weights, query targets or candidate sizes were tuned to improve the reported scores.

Keyword search is the initial UI selection; all three modes remain available. General Chat's known balance-sheet/income-statement confusion remains a separate prompt/model limitation. There is no new financial advisory agent or claim that retrieval alone repairs answer generation. A broader independently labeled query set would be required for general accuracy or hybrid superiority claims.
