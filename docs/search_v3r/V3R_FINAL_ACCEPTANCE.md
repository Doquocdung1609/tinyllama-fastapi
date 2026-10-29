# V3R final acceptance — PARTIAL

Authorization: SEARCH_V3R_EXTRACTION_AND_RETRIEVAL_REPAIR. Base: Draft PR25, exact `0a5a692be073cb4f43229d4b1a8e5c4293221fb1`. Branch: `codex/financial-search-v3r-recovery`. No merge performed. The repository owner retains acceptance authority.

The repair recovers omitted mixed-PDF financial image regions, preserves source geometry/confidence/ancestry, distinguishes technical completion from financial review, and adds an opt-in region-context search profile. Seven omitted SEM cells are located in the correct checked current-year KRW windows; only3/7raw strings have exact punctuation, so they stay unreviewed. An additional split-image CEO regression was reproduced and repaired using preserved source words. Every original V3 baseline top-ten rank list remains identical; all84questions are now regression only.

Final exposed R@5 improves from0.6429 to0.7476 by literal source matching, or0.8143 using the separately reported signed-digit source-cell locator. The latter is never used to repair financial facts. No old positive loses top-five source coverage after the fragment fix. The supported API also replays70older questions with R@5=0.9821, plus17source-context,3Decimal/abstention and4entity guards.

After full policy freeze,24new PNJ/ACB questions ran once. Source-cell hit@5 is13/16 (PNJ8/8,ACB5/8);8/8negative contexts withhold numeric claims. No independent human reviewer participated, no new mixed-financial-image source was validated, and ACB label/English scale limitations remain. No policy was tuned after this test. Hence **SEARCH_V3R_PARTIAL**, not SEARCH_V3R_LOCKED or broad financial-accuracy acceptance.

|Gate|Status|Evidence and boundary|
|---|---|---|
|A|PASS — source content|150 unchanged inventory files;runtime PID lease and two SQLite temporary journals explicitly accounted for;locked Nomic and original OCR languages verified.|
|B|PASS_BOUNDED|7/7 SEM cell locations recovered;14 sampled pages plus actual decorative negatives and synthetic regressions.|
|C|PASS_BOUNDED|84/84 baseline rank replay identical;no lost A0-positive top-five coverage after fragment repair;70 legacy API questions and17+3+4 guards pass their bounded contracts.|
|D|PASS_BOUNDED / broader limits|Checked SEM row/year/KRW/current-column/source windows pass;raw punctuation and unreviewed wider scale interpretation remain limitations.|
|E|PARTIAL|24 post-freeze questions,13/16 positive cell locators at5,8/8 numeric abstentions;no new mixed-image test and no independent human labels.|
|F|PASS_BOUNDED + warning|671 backend,9 frontend,build,pip/compile and3 real Chrome tests pass;actual machine RAM pressure remains a warning.|
|G|PENDING|Owner or independent human must review actual source samples;no self-approval.|

## Actual verification

* Windows backend: **671 PASS**,0FAIL,0SKIP; one existing Starlette/httpx deprecation warning.
* Frontend: **9 PASS**; TypeScript/Vite build PASS.
* Python compile and pip dependency check: PASS.
* Actual Chrome/Prebuilt: **3 PASS**,0FAIL,0SKIP; PDF worker JavaScript MIME,source highlight,mixed selectable OCR,reviewed/candidate distinction,coverage warnings and stale response covered. Nine real screenshots are retained.
* Initial source-window annotation failure and initial fragment regression: recorded, repaired before freeze and retained as evidence. The wrong-document performance attempt is explicitly INVALID and excluded from final metrics. Failed public download attempts are recorded as acquisition limits.
* Full independent human acceptance,new mixed-source generalization and exhaustive financial cell review: **PENDING/SKIP**,not reported as PASS.

Background preparation took58.31s on the final owner run. Warm repeated-query p95 was1.529s; the first final HTTP request was5.126s. An unprepared full-index query remained71.13s and is moved to visible startup preparation. Actual machine-wide RAM pressure was observed (minimum12.6MiBavailable in one concurrent run); no unrelated processes or models were stopped to hide it. See the performance report for resource boundaries.

The technical source-recovery work and bounded demonstration flows are reviewable. Unrestricted financial-question accuracy and unconditional presentation readiness are **not** established. Demonstrate checked CEO/HPG/BIDV cells and candidate-only SEM retrieval with explicit limitations; finish owner source audit and check free RAM before acceptance.

All eight required reports and reproduction tools are included. Credentials, original PDFs,private logs and workspaces remain local. Existing SEC data and locked Nomic768were preserved; the only inventory differences are documented runtime lock/journal metadata. No paid OCR,new large model,SPLADE,new agent framework or Milestone C feature was introduced.
