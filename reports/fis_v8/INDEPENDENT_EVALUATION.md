# Independent SEC evaluation

Two authentic official filings were selected separately from the COST, HD, PG and Microsoft development cases. Expected values, accession, location and question text were frozen in [HOLDOUT_CASES.json](HOLDOUT_CASES.json) before either import or QA. The UTF-8 fixture SHA-256 was `ed6734ffc79614f7ce3f3b532f1a0348bc9c4b1f40e33c1436aadda0d79e5d99`. Numerical labels were transcribed from SEC statement rows and periods. Narrative labels came from the corresponding SEC disclosure, outside FAITH-R retrieval.

| Independent case | Expected evidence | First observed result |
| --- | --- | --- |
| Amazon 10-K annual net sales | 637,959 million USD, FY ended 2024-12-31, consolidated statement | PASS. Exact amount, duration, unit and source cell. |
| Amazon 10-K narrative | Substantive Item 1A disclosure | FAIL. English “risks” entered a generic fallback and returned an exhibit excerpt. |
| PepsiCo 10-Q 12/24-week net revenue | 22,501 and 40,751 million USD, same end date, separate columns | PASS. Both amounts and exact durations from authenticated cells. |
| PepsiCo 10-Q narrative | Part II Item 1A states no material change | PASS. Relevant disclosure and matching accession. |

**First run:** 2/2 official imports published BM25, 2/2 numerical answers and 1/2 narrative answers. Neither import advertised Dense availability. The failing Amazon question exposed an English risk-intent routing gap. The product was corrected to recognize the general risk wording and substantive risk subheadings. The subsequent Amazon answer cited its discussion of intense competition. The repeat achieved 4/4 on these known cases and is kept separate from the independent 3/4 score.

This sample exercises one 10-K and one 10-Q. It provides no coverage claim for arbitrary segments, non-USD numeric formats, or complete financial-document synthesis. Initial and repeat answers, source cells, durations and event logs are in [browser-log.json](browser-log.json).

- [Amazon SEC source](https://www.sec.gov/Archives/edgar/data/1018724/000101872425000004/amzn-20241231.htm)
- [PepsiCo SEC source](https://www.sec.gov/Archives/edgar/data/77476/000007747624000042/pep-20240615.htm)
