# V7A G3 review-release status

**Source acquisition: PASS. Full G3 independent review: PENDING.** The nine official SEC primary HTML files passed accession/form/index identity checks and are available in one immutable source ZIP. This does not change any reviewer decision or constitute gold approval.

## Separate blind inputs

| Reviewer | Local input package | SHA-256 |
|---|---|---|
| Agent 1 | `C:\Users\Admin\Downloads\V7A_G3_AGENT1_SOURCE_REVIEW_INPUT.zip` | `143d505127ebdf062de46927dbab3175d5d5448f3e259d8658b7e4ce90801b81` |
| Agent 2 | `C:\Users\Admin\Downloads\V7A_G3_AGENT2_SOURCE_REVIEW_INPUT.zip` | `9e84a7611b29b89b33dd80f4387d6e94fde83741182e103b40fe403eed8991a3` |

Both packages contain the **same** validated nine-source ZIP (SHA-256 `9ab979c7156b99b1f0ca25747b0ff1ca24771812253f2d1e0cae3deec95c3afb`) and the respective G2 blind question package. The contained templates are empty. Package CRC and common-source byte identity passed. No Agent 1 or Agent 2 answers, gold labels, F10 labels or model rankings are included. These are local release artifacts ready for separate distribution; delivery to external reviewers is not asserted.

## What remains

The supplied Agent 2 G3 checkpoint is **PARTIAL**: 94 question IDs and 47 accession mappings checked, with 66 `SUPPORTED`, 9 `AMBIGUOUS`, 1 `UNSUPPORTED`, and 18 `SOURCE_UNAVAILABLE`. The 18 source-unavailable questions map exactly two apiece to the nine newly acquired filings. The source bytes are now available; those 18 decisions remain unchanged until Agent 2 independently reopens the primary HTML, records exact row/header/period/unit/source evidence, and freezes a new hashed review file. The nine ambiguous and one unsupported decisions also need source-first review or documented final dispositions.

No Agent 1 blind G3 result or post-recovery Agent 2 result was supplied in the local handoff. Independent comparison, conflict adjudication and any human signoff therefore remain outstanding. This branch neither reads answer values for reconciliation nor changes the frozen 94 questions, corpus, index, F10 labels or FAITH-R algorithm. **G3 FULL and certified gold must not be claimed.**

The application was restarted in Prebuilt mode at `http://127.0.0.1:18110/app/` with the existing `tmp/topic3/demo-workspace`; HTTP 200 and PDF/OCR/SEC READY were observed. Ollama was already running when the launcher started. The app remains running for the owner.
