# G3U execution and test log

| Check | Actual result |
| --- | --- |
| G3T private handoff | 18-entry ZIP CRC PASS; 17/17 declared file SHA-256 and separate review-input SHA-256 PASS |
| Original SEC archive | 47/47 accession/source hashes PASS; three ZIP CRC PASS |
| Frozen corpus/index replay | 8,670 A and 8,670 B original IDs/text hashes PASS; derivative hashes match G3T |
| AMD diagnosis | Three real filings inspected; 68/69 frozen chunks contain only Part II; target values absent |
| Non-G2 author model smoke | Six methods returned 20 each on A; no G2 quality score |
| Approved v2 ranked pool | 1,692 runner-asserted arm executions, 31,760 hit lines, 5,792 unique blind pairs; structural set/hash/leakage PASS with 104 zero-run provenance limitation |
| Ranked AI qrel preparation | 124 PARTIAL, 5,668 UNJUDGED, 0 EXACT/NONE; 94/94 questions |
| Ranked human UI/API | 5,792 pairs, priority pagination, no rank/score fields, invalid POST HTTP 400, 0 human events |
| Source-only human UI/API | 17,340 pairs, priority pagination, 0 human events |
| Synthetic V7B harness | PASS; no G2 scoring mode |
| Focused G3U adversarial tests | 9 PASS |
| Full Python regression | 763 PASS, 0 FAIL, 0 SKIP; one Starlette/httpx deprecation warning in 27.27 s on final rerun |
| React build | PASS; TypeScript and Vite production build |
| Static reviewer JavaScript syntax | PASS with `node --check` |
| Dependency consistency | `pip check`: no broken requirements after FastEmbed 0.9.1/Pillow 12.3.0 repair |
| Final sealed G2 metric scoring | NOT RUN; Tier A/H gates blocked |

The first G3U test edit produced a fixture-only `NameError`; it was corrected and the full suite rerun. The first ranked pool attempt was stopped on a real RRF protocol discrepancy and preserved as a separate immutable partial checkpoint. GitHub CI results are checked after the final PR commit.
