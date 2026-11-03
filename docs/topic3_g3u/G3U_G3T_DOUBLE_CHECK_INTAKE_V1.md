# G3T double-check intake: 94 rationales / 98 exported events

Received on 2026-11-03, after the G3U v2 pool handoff. This is a **versioned evidence overlay**, not an edit to G3T, G3U v2, the frozen G2 questions, or any human event. The three supplied files are an external audit memo and two CSV exports. The original `G3T_HUMAN_REVIEW_EVENTS.jsonl` is not in the supplied files, private G3T handoff ZIP, Downloads search, or repository. The export's claimed 98/98 original event hash-chain verification is therefore **not independently repeatable here**.

The intake script checked the three input SHA-256 hashes, ZIP CRC, 94/98 row counts, 94 identical G2 IDs, 116 C1 numeric-cell counts, exact frozen question text, ticker, accession/source URL and C2 AI label for every row. Within the exports, event order is 1–98, each question's latest order/decision/SHA string matches its history row, and the 98 SHA strings are distinct and shaped correctly. This is **internal export consistency**, not a recomputation of canonical event hashes or proof of human identity. See [machine-readable intake](G3U_G3T_DOUBLE_CHECK_EXPORT_INTAKE_V1.json).

| Latest state reported by external export | Count |
| --- | ---: |
| APPROVE | 85 |
| REQUEST_CORRECTION | 7 |
| AMBIGUOUS | 1 |
| EXCLUDE | 1 |

These are **reported** source-review decisions. They are not imported into the repository's human ledger, not 85 independently authenticated approvals, and not original-single-chunk qrels. The previous G3U report's zero-human count describes its then-available checkpoint; this intake is newer and still unverified at original-event level. The ranked blind pool remains 124 AI-provisional PARTIAL / 5,668 UNJUDGED / zero EXACT/NONE, with no final G2 benchmark.

## Errata packets for the original reviewer

| Question | Export finding | Required review |
| --- | --- | --- |
| `V7A_G2_12_01` | Latest APPROVE rationale reportedly copied from Amazon `12_02` operating income, while this question asks a bounded negative about standalone gross profit. | Inspect the original latest event and earlier event #3 against the primary SEC statement. If correct, append a new human event with the bounded negative rationale; preserve both old events. |
| `V7A_G2_14_02` | Latest AMBIGUOUS rationale reportedly discusses Intel gross margin rather than Amazon operating expenses. | Inspect original event #8 and earlier #7, including 3M/6M scope. Append a human correction or ambiguity decision with the right evidence. |
| `V7A_G2_25_02` | Latest REQUEST_CORRECTION rationale and URL reportedly discuss Microsoft revenue recognition instead of Meta operating cash flow. | Inspect original event #13 and earlier #12, then append a new human decision with the Meta source and period semantics. |
| `V7A_G2_24_01` | Prior event #10 reportedly had a copy error; latest event #11 reportedly corrected it. | Verify original #11 and retain the full history. No new event needed if it checks out. |
| `V7A_G2_11_02` | Latest REQUEST_CORRECTION reportedly requires an extra FY2020 comparison. Frozen v1 rubric requires current plus immediately prior period unless wording demands more. The latest rationale reportedly omits two mandatory C1 values. | Apply the locked v1 rule, verify current/prior cells and full rationale, then have the reviewer decide. Any three-period requirement needs a separately versioned rubric; do not retroactively edit v1. |

The input memo also reports 112/116 C1 values mentioned in complete rationales. The supplied history CSV stores only explanation excerpts, so that ratio cannot be independently recomputed from these files. Likewise, no full SEC-wide truth audit or reviewer authentication has been performed.

**Release state:** `HUMAN_EVENT_ORIGINAL_REQUIRED; THREE_ACTIVE_ERRATA_REVIEW_PENDING; ONE_POLICY_REVIEW_PENDING; HUMAN_GOLD_NOT_PROMOTED; ORIGINAL_CHUNK_QRELS_UNCHANGED`. On receipt of the original event JSONL, rerun the existing canonical hash-chain and evidence-SHA validator against the frozen G3T review input V2, verify the five affected full events, then request genuine reviewer corrections. Do not synthesize event #99 or later from CSV excerpts.
