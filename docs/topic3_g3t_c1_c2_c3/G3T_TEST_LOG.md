# G3T verification log

| Check | Result |
| --- | --- |
| G3T scripts Python compilation | PASS |
| SEC-47 raw source verifier | PASS: 47/47, all three input ZIP CRC PASS |
| Focused G3T and G3S review tests | 10 PASS, 0 FAIL |
| Full `python -m pytest -q` | 754 PASS, 0 FAIL, 0 SKIP, 1 warning in 40.13 s |
| Warning | `StarletteDeprecationWarning` from installed `fastapi.testclient`: `httpx` with `starlette.testclient` deprecated; unrelated to G3T changes |
| Local reviewer service | `READY`, 94 questions, 0 events; API returned 94 records with AI proposal fields |
| Human decision events | 0; no form submit or synthetic event |
| Sealed retrieval benchmark | NOT RUN: qrels and human gates blocked |
| Private handoff ZIP | CRC PASS, 18 entries; all 17 manifest-listed files matched SHA-256 |

The focused adversarial fixtures reject a modified AI hash chain, duplicate/missing 94-question records, AI ledger reuse as human events and an AI-labelled forged event. A four-filing clustered-bootstrap dry run is synthetic, deterministic and explicitly not G2 evaluation.
