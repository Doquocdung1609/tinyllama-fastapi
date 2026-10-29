# V3R owner audit packet — review pending

Recommendation: **SEARCH_V3R_PARTIAL**. The table below is an audit checklist, not an assertion that an owner has accepted it. Compare each original page image against the source value, original-image window, current/prior/currency column and raw candidate. Record reviewer identity, date and decision outside the agent annotation. Never approve the whole document because one cell is correct.

|Sample|Original source image|Source display|Candidate|Column context|Owner decision|
|---|---|---|---|---|---|
|SEM assets|[PDF p7](source_images/SEM-p7.png)|14,595,895,255,468|14,595895.255468|2025 / KRW / column 1|PENDING|
|SEM liabilities|[PDF p8](source_images/SEM-p8.png)|4,798,551,372,605|4798551372605|2025 / KRW / column 1|PENDING|
|SEM equity|[PDF p8](source_images/SEM-p8.png)|9,797,343,882,863|9,797,343,882,863|2025 / KRW / column 1|PENDING|
|SEM cash_equivalents|[PDF p7](source_images/SEM-p7.png)|2,701,205,916,236|2,701,205,916,236|2025 / KRW / column 1|PENDING|
|SEM inventory|[PDF p7](source_images/SEM-p7.png)|2,412,996,843,057|2,412,996843,057|2025 / KRW / column 1|PENDING|
|SEM pretax_income|[PDF p9](source_images/SEM-p9.png)|895,831,372,804|895,831,372,804|2025 / KRW / column 1|PENDING|
|SEM net_income|[PDF p9](source_images/SEM-p9.png)|730,989,517,218|730.989.517.218|2025 / KRW / column 1|PENDING|
|v3r-pnj-01|[PDF p3](source_images/PNJ-p3.png)|20.168.475.768.890|See raw hits/checkpoint audit|2025-12-31 / VND|PENDING|
|v3r-pnj-02|[PDF p3](source_images/PNJ-p3.png)|17.207.730.777.685|See raw hits/checkpoint audit|2024-12-31 / VND|PENDING|
|v3r-pnj-03|[PDF p3](source_images/PNJ-p3.png)|522.025.257.031|See raw hits/checkpoint audit|2025-12-31 / VND|PENDING|
|v3r-pnj-04|[PDF p3](source_images/PNJ-p3.png)|15.835.506.447.900|See raw hits/checkpoint audit|2025-12-31 / VND|PENDING|
|v3r-pnj-05|[PDF p4](source_images/PNJ-p4.png)|6.892.720.947.176|See raw hits/checkpoint audit|2025-12-31 / VND|PENDING|
|v3r-pnj-06|[PDF p4](source_images/PNJ-p4.png)|13.275.754.821.714|See raw hits/checkpoint audit|2025-12-31 / VND|PENDING|
|v3r-pnj-07|[PDF p5](source_images/PNJ-p5.png)|34.976.042.929.392|See raw hits/checkpoint audit|2025-12-31 / VND|PENDING|
|v3r-pnj-08|[PDF p5](source_images/PNJ-p5.png)|2.829.338.825.192|See raw hits/checkpoint audit|2025-12-31 / VND|PENDING|
|v3r-acb-01|[PDF p7](source_images/ACB-p7.png)|607,875,185|See raw hits/checkpoint audit|2022-12-31 / TRIEU_VND|PENDING|
|v3r-acb-02|[PDF p7](source_images/ACB-p7.png)|527,769,944|See raw hits/checkpoint audit|2021-12-31 / TRIEU_VND|PENDING|
|v3r-acb-03|[PDF p7](source_images/ACB-p7.png)|8,460,892|See raw hits/checkpoint audit|2022-12-31 / TRIEU_VND|PENDING|
|v3r-acb-04|[PDF p7](source_images/ACB-p7.png)|3,981,376|See raw hits/checkpoint audit|2022-12-31 / TRIEU_VND|PENDING|
|v3r-acb-05|[PDF p8](source_images/ACB-p8.png)|549,436,522|See raw hits/checkpoint audit|2022-12-31 / TRIEU_VND|PENDING|
|v3r-acb-06|[PDF p8](source_images/ACB-p8.png)|58,438,663|See raw hits/checkpoint audit|2022-12-31 / TRIEU_VND|PENDING|
|v3r-acb-07|[PDF p10](source_images/ACB-p10.png)|17,114,208|See raw hits/checkpoint audit|2022-12-31 / TRIEU_VND|PENDING|
|v3r-acb-08|[PDF p10](source_images/ACB-p10.png)|13,688,193|See raw hits/checkpoint audit|2022-12-31 / TRIEU_VND|PENDING|

For PNJ p5, the original statement is rotated; the saved original image is intentionally unaltered. The manual qrel windows use original PDF viewport coordinates. PDF viewer rotation and OCR reading transforms were tested. For ACB, the blue native-font text loses characters in “Profit” and some source labels are not recognized; check both original image and raw audit. “VND million” must not be accepted as unscaled VND. Equity and profit retrieval misses remain open findings.

## Acceptance matrix

|Gate|Status|Evidence and boundary|
|---|---|---|
|A|PASS — source content|150 unchanged inventory files;runtime PID lease and two SQLite temporary journals explicitly accounted for;locked Nomic and original OCR languages verified.|
|B|PASS_BOUNDED|7/7 SEM cell locations recovered;14 sampled pages plus actual decorative negatives and synthetic regressions.|
|C|PASS_BOUNDED|84/84 baseline rank replay identical;no lost A0-positive top-five coverage after fragment repair;70 legacy API questions and17+3+4 guards pass their bounded contracts.|
|D|PASS_BOUNDED / broader limits|Checked SEM row/year/KRW/current-column/source windows pass;raw punctuation and unreviewed wider scale interpretation remain limitations.|
|E|PARTIAL|24 post-freeze questions,13/16 positive cell locators at5,8/8 numeric abstentions;no new mixed-image test and no independent human labels.|
|F|PASS_BOUNDED + warning|671 backend,9 frontend,build,pip/compile and3 real Chrome tests pass;actual machine RAM pressure remains a warning.|
|G|PENDING|Owner or independent human must review actual source samples;no self-approval.|

The eight inherited reviewed cells are covered by REVIEW_CONTINUITY_LAYOUT_V2.json. Their source bytes, source display and exact boxes match previous audited reviews, with new lineage events. This is not a new independent human review of OCR. No new SEM,PNJ or ACB cell was automatically certified.

The technical packet contains immutable source SHA/URLs, raw extraction coverage (including the initial failed coordinate audit), before/after ablations, all84 and70 regression results, single-pass24 new questions, policy/label seals, resource samples and nine actual Chrome screenshots. SOURCE_IMAGE_HASHES.json hashes the original-source images. Do not publish original PDFs, tokens, database files, private logs or entire workspaces.

Start on Windows from this repository:

```powershell
.\scripts\run_financial_studio.ps1 -Mode Prebuilt -Workspace 'C:\Users\Admin\Documents\GitHub\tinyllama-fastapi\studio_workspace\search-v3r-development-20261029'
```

Open http://127.0.0.1:8110/app/, use the existing local key privately, choose **Search V3R · bằng chứng theo vùng**, then wait for the prepared-index notice. Old profile preferences remain preserved; V3R is an explicit opt-in. For SEM choose PDF tải lên as the source and Samsung Electro-Mechanics as the document. Candidate results are useful for locating source images; they are not numeric answers. The CEO audited-assets sample demonstrates the separate reviewed-cell state.

Rollback: stop the owned launcher with `.\scripts\run_financial_studio.ps1 -Stop`; launch an existing old workspace with its old code/profile. Old PDF/checkpoint/SEC generations were not replaced. New derived roots and immutable source/index files remain available for inspection. PR23/24/25 must remain Draft, and neither this branch nor those PRs is merged by this task.
