# Independent unseen SEC evaluation

Two official filings outside the V8.2 development cases were discovered and imported into the isolated SEC acceptance library. The test fixture was sealed before the first product execution with SHA-256 `ebafeaa79de3c9d1922fcaa7043e015a8683967070f49246968dd80d2fc42de9`. Expected operands came from the consolidated source statements, independently of FIS retrieval. [Sealed prompts and source labels](HOLDOUT.json)

| Filing | Current and year-earlier margins | Change | First run |
| --- | --- | --- | --- |
| Adobe 10-K FY ended 2024-11-29 | 31.35%, 34.26% | −2.92 percentage points | PASS |
| Cisco 10-Q ended 2024-10-26 | 17.04%, 29.15% | −12.12 percentage points | PASS |

Both imports published BM25. Both answers had three required calculations and four authenticated source cells, with matching issuer, accession and period in the source viewer. Deltas were calculated from unrounded margins. The first-run results remain separate from later replays. The code changes after this first run addressed unrelated development issues, including F06 and explicit denominator scope validation. [First-run results](holdout-first.json)

This sample tests prior-year margins on two unfamiliar layouts. It does not establish broad narrative or arbitrary-formula coverage. The additional local tests exercise an unseen issuer alias, a 52-week retail-calendar drift, two denominator labels, and an unsupported narrative topic.

- [Adobe official SEC filing](https://www.sec.gov/Archives/edgar/data/796343/000079634325000004/adbe-20241129.htm)
- [Cisco official SEC filing](https://www.sec.gov/Archives/edgar/data/858877/000085887724000030/csco-20241026.htm)
