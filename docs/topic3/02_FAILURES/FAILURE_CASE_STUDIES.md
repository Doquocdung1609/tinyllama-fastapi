# Five observed failures in the bounded author-method run

All five records in `FAILURE_CATALOG.jsonl` link a frozen question ID, source file hash/locator, expected author-chunk ID, actual Top-1 ID, run arm and Top-10 target rank. The underlying SEC rows are original public HTML; the target labels were prepared by Codex and are **not independent human gold**. The negative examples show retrieval behavior, not a verified wrong numeric answer.

| Case | Observed result | Source target | Diagnosis and limit |
|---|---|---|---|
| F01 P&G net sales | BM25 Top-1 is segment discussion; consolidated statement NET SALES row is absent Top-10 | P&G Q1 FY2027, three months ended Sep 30, 2026, 2026 row `23,276` USD millions, author chunk `..._0003` | Wrong financial row priority. Other relevant chunks may exist; no exhaustive recall claim. |
| F02 P&G total assets | BM25 Top-1 is other asset/goodwill material; balance-sheet row appears Rank 2 | P&G Sep 30, 2026, TOTAL ASSETS `133,132` USD millions, chunk `..._0006` | Correct document and topic do not guarantee correct metric at Rank 1. |
| F03 Home Depot total assets | SPLADE+Dense target missing Top-10; the same Stage-2's Top-20 candidate pool allowed the author deterministic reranker to place it Rank 1 | Home Depot Aug 2, 2026, Total assets `109,384` USD millions, chunk `..._0000` | Candidate depth and downstream ordering matter. One case does not prove general improvement. |
| F04 unsupported year | P&G BM25 returns a 2026/2025 filing for a 2037 query | No 2037 source in locked two-filing corpus | A retrieval hit must not become a financial answer. Requires period and source-availability guard. |
| F05 absent issuer | BM25+Dense returns Home Depot for an Apple 2025 question | No Apple source in locked corpus | Requires issuer availability guard or abstention; retrieval alone has no numeric certification. |

The paper's own example of lexical/semantic divergence motivates these checks, but none of its source-specific results were copied as local measured findings. The measured Top-10 records and qrels hash are in `../01_REPRODUCTION/RETRIEVAL_RESULTS.json`. Five cases span four source-positive retrieval failures plus two no-answer conditions; source/period/unit correctness still requires independent review.
