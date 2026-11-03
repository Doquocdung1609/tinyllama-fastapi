# C4R failure register: public redacted view

The private 93-row register is `C:\Users\Admin\Downloads\C4R_PRIVATE_20261103_V1\C4R_R0_FAILURE_REGISTER_PRIVATE.json`, SHA-256 `cfa17d0b1b1511172a7e218cd50cfc659307e94d1e15e153874ce992504ec19c`. It preserves each question ID, ticker, accession, form, report date, old target payload fiscal values, parsed slots, old/A5 filters, actual A5 attempt status and candidate IDs. Gold accession is used **after inference** for this diagnosis, never in A5 retrieval.

| Priority | Reproduced failure | Count or evidence | Repair / result |
| --- | --- | --- | --- |
| P0 | Old FY filter excludes valid target metadata | 46 of 93 eligible G2; 26 no ranked rows and 20 wrong-filing Top-20 in old A4 | A5 has issuer/form scope and no hard FY period; 46/46 target metadata compatible. |
| P0 | Query ontology incomplete | Old code recognizes chiefly revenue/CAPEX; many distinct financial metrics collapse to UNKNOWN | New typed English/Vietnamese ontology; 40 contrastive cases. |
| P0 | Numeric row is not a verified cell | Original SEC chunks flatten header/period/column association | Original-only answerer abstains; separately marked iXBRL source-enriched answerer binds concept/context/unit and cited element. |
| P1 | Sidecar quota silently ineffective | When base returns 60, appended sidecar rows were truncated | Reserved slots; dev test includes five new original IDs, no Top-5 change on four dev questions. |
| P1 | G3U empty-run provenance | 104 arm×question combinations lack per-run output records | New A5 emits explicit `COMPLETED_EMPTY`, `COMPLETED_WITH_HITS`, `ERROR` and attempts. Old record remains unchanged. |
| P1 | Three AMD facts absent from original chunks | `09_01`, `10_01`, `10_02` source-first C1/G3U audit | Kept `CORPUS_MISSING_SOURCE`; source-enriched track is separate. No original-chunk EXACT claim. |

Reproduce with `python -m pytest -q tests/test_topic3_c4r_a5.py` and `python -m scripts.topic3_c4r_g2_diagnostic` using the frozen G2 paths in [run commands](C4R_FINAL_ACCEPTANCE.md). The 94 G2 questions are **post-exposure regression diagnostics**. The original 26 missing-row cases remain `UNKNOWN_ZERO_VS_OMITTED` for the G3U run, even though the new A5 run logs all requests.
