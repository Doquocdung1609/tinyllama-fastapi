# C4 verification log

| Check | Actual result |
| --- | --- |
| G3U / PR head | PR36 Draft at `4f1622e` before C4; PR35 detached worktree at `b5c6e1b`; no frozen tracked file changed |
| Owner log | SHA `be9cd71e...`; canonical chain 102/102 PASS; 94 unique IDs; all evidence SHA = G3T input V2 |
| Status CSV | 94 IDs and totals agree; `25_02` latest hash stale relative to event #102 |
| Eligibility | 93 objective proxy eligible, 1 excluded; source preview 67, structural blocked 19, review correction 7 |
| Ranked pool | Original G3U SHA `93c9dcf...`; 31,760 hit rows, 1,588 observed run rows, 104 without hit/run provenance |
| Qrel gate | 0 EXACT/human; exact/MRR/nDCG/Recall rejected |
| Read-only B metadata | 8,670 points/47 accessions; 46 target filter mismatches (26 no hit rows, 20 wrong filing Top-20) |
| Product PR35 | 2 local PDFs READY, OCR READY, SEC unavailable; six search HTTP 200/5 results; HPG unsupported consolidated chat returns `QUERY_CONTEXT_CONFLICT` |
| React UI | Six actual screenshots saved outside Git; BIDV 3-way live compare, HPG scanned page 5 viewer |
| Focused C4 tests | 5 PASS |
| Full Python suite | 768 PASS, 0 FAIL, 0 SKIP, one existing Starlette/httpx deprecation warning in 39.87 s |
| PR35 frontend | `npm ci` and `npm run build` PASS, 2,695 modules, 0 npm vulnerabilities |
| Syntax and dependency | C4/G3U intake `py_compile` PASS; `pip check` no broken requirements |
| GitHub CI | Verify after PR36 commit; do not preclaim |

No paid service, SEC refetch, new G2 retrieval run, model tuning, original human event write, final relevance benchmark, PR merge or PR35 tracked edit occurred.
