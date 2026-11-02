# V7A G3 review-release status

**Historical release checkpoint:** The nine official SEC primary HTML files passed accession/form/index identity checks and are available in one immutable source ZIP. The later 2026-11-02 Agent 1 and Agent 2 post-source submissions are audited in [V7A_G3R_FINAL_ACCEPTANCE.md](V7A_G3R_FINAL_ACCEPTANCE.md). Human adjudication remains pending. The pre-recovery decisions and reviewer inputs below are unchanged.

## Separate blind inputs

| Reviewer | Local input package | SHA-256 |
|---|---|---|
| Agent 1 | `C:\Users\Admin\Downloads\V7A_G3_AGENT1_SOURCE_REVIEW_INPUT_V2.zip` | `e8ef439f232717e26fc0b5c47cc8afa0f15605f239ddb273e6cfed1fc04aaf3c` |
| Agent 2 | `C:\Users\Admin\Downloads\V7A_G3_AGENT2_SOURCE_REVIEW_INPUT_V2.zip` | `b4390d9ca5f355084b5f211aeabfc65f2654742dfc8122d0be082caad2fcdd9b` |

Both V2 packages contain the **same** validated nine-source ZIP (SHA-256 `9ab979c7156b99b1f0ca25747b0ff1ca24771812253f2d1e0cae3deec95c3afb`), the same `SOURCE_READY_18.csv` (SHA-256 `93dab4c2a398de1b81043b5644cdfc411b145dc3e0e75fbfe50981502b5374f0`) and the respective G2 blind question package. The mapping lists exactly two frozen question IDs for each of the nine source filings, without answers. The contained templates are empty. Package CRC and common-source byte identity passed. No Agent 1 or Agent 2 answers, gold labels, F10 labels or model rankings are included. Earlier V1 handoffs remain untouched; V2 is the recommended additive review input. These are local release artifacts ready for separate distribution; delivery to external reviewers is not asserted.

## What remains

The supplied Agent 2 G3 checkpoint is **PARTIAL**: 94 question IDs and 47 accession mappings checked, with 66 `SUPPORTED`, 9 `AMBIGUOUS`, 1 `UNSUPPORTED`, and 18 `SOURCE_UNAVAILABLE`. The 18 source-unavailable questions map exactly two apiece to the nine newly acquired filings. The source bytes are now available; those 18 decisions remain unchanged until Agent 2 independently reopens the primary HTML, records exact row/header/period/unit/source evidence, and freezes a new hashed review file. The nine ambiguous and one unsupported decisions also need source-first review or documented final dispositions.

Agent 1 First Pass (`5dce3eba12dd6894c0bd0ded7ec8ec059e4a68dd6c67f23a5ce7722ba85053b7`) and Second Pass (`5d14fd8813d89943d82ec70d2501fc4b82aeccfc943b7a28cf05024a863e2977`) are now present. Their 32 carried-forward first-pass rows match on every shared field. Agent 2 V2 (`86a19238a99d9a3ec1d7b7975a2c042fced5b6388008486fac18e538f1be12bc`) preserves its Round 1 ledger and evidence byte-for-byte. All checkpoint ZIP CRC and declared output hashes passed.

The owner-requested filename `V7A_G3_SEC_SOURCE_HANDOFF_20261102.zip` is an exact copied alias of the verified `V7A_G3_SEC9_SOURCE_HANDOFF_20261102.zip`, both with SHA-256 `9ab979c7156b99b1f0ca25747b0ff1ca24771812253f2d1e0cae3deec95c3afb`.

Coordinator comparison of the frozen AI outputs yields 70 `AGREED_SUPPORTED_DECISION_ONLY`, 5 decision disagreements, 1 shared ambiguity and 18 jointly `SOURCE_UNAVAILABLE` in the pre-recovery reviews. Detailed value and evidence comparisons, nine human-readable dispute packets and the 18-question raw-source queue are kept **outside Git** at `C:\Users\Admin\Downloads\V7A_G3_COORDINATOR_RECONCILIATION_20261102_V4`; they must not be sent to blind reviewers before each independent post-source delta is frozen. Numeric token equality is not a row/column/period/unit agreement or human gold.

Of the five decision disagreements, four are `SUPPORTED` versus `AMBIGUOUS` metric/wording cases; the fifth is `UNSUPPORTED` versus `NEGATIVE_SUPPORTED` for a bounded negative line-item question, a label-policy difference requiring adjudication. Three additional both-supported questions have partially overlapping numeric token sets because one ledger includes extra comparative periods or a different source table. These are period/scope review cases, not established contradictory values. The private reconciliation has 94 field-comparison rows, nine dispute packets (five status, one shared ambiguity, three period/scope), and a separate 18-question raw-source queue. All 18 raw sources are now available, but their frozen labels remain unchanged.

No post-recovery Agent 1 or Agent 2 review result was supplied. Independent raw-source deltas, adjudication and any human signoff therefore remain outstanding. This branch does not change the frozen 94 questions, corpus, index, F10 labels or FAITH-R algorithm. **G3 FULL and certified gold must not be claimed.**

The application was restarted in Prebuilt mode at `http://127.0.0.1:18110/app/` with the existing `tmp/topic3/demo-workspace`; HTTP 200 and PDF/OCR/SEC READY were observed. Ollama was already running when the launcher started. The app remains running for the owner.
