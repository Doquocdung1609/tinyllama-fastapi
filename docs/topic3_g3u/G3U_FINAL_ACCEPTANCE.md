# G3U final technical acceptance

**Decision: POOL_ACQUIRED; QRELS_PARTIAL; HUMAN_ADJUDICATION_PENDING; FINAL_BENCHMARK_BLOCKED.** This is a continuation of G3T on existing Draft PR #36. The owner-approved v2 changes only the prospective executable RRF definition for this pool: Qdrant local's actual default 2. The earlier v1 and partial run are immutable and disclosed. No final G2 metrics, tuning, merge or human-gold claim occurred.

| Work | Evidence |
| --- | --- |
| Integrity | G3T handoff 18/18 CRC; 17/17 declared member SHA-256 plus review-input SHA; 47/47 SEC sources; 8,670/8,670 original A/B index members; C1/C2 94 IDs and C2 hash chain |
| Exact-label risk | 71 AI exact proposals; `12_02` and `15_01` held for strict release, leaving 69 candidates before independent unit review. In a systematic 8-question/19-cell historical sample, 13 scale phrases were outside the immediate table or not explicit there. |
| AMD | Three C1 SEC cells are present in original source; the relevant 68/69 original chunks cover only Part II risk/exhibits and omit the Part I financial table. Source exists, original corpus evidence missing; no retrieval-miss claim. |
| Author fidelity | Six pinned author methods, A/B index conditions and FAITH-R arms audited. Stage-2 native internal budget 60 at output 20. Runtime RRF default 2 differs from configured 60; owner-approved v2 and partial exposure recorded. |
| Ranked pool | 1,692 asserted arm executions, 31,760 hit lines, 5,792 unique blind pairs, 3,946 off-target pairs. No method/rank/score leakage. 104 zero-hit arm/question executions lack separate log rows. |
| Qrels | Ranked pool 124 provisional PARTIAL, 5,668 UNJUDGED, zero EXACT/NONE. Separate source-only queue 182 PARTIAL, 17,158 UNJUDGED. Human source/chunk decisions: 0. |
| V7B | Protocol and arm registry locked; synthetic/non-G2 harness and resource reporting implemented. Tier A and Tier H both blocked; final sealed scoring not run. |

The machine-readable [gate matrix](G3U_GATE_MATRIX.json) records U0–U12. [Pool status](G3U_POOL_STATUS_V2_APPROVED.json), [qrel coverage](G3U_RANKED_QREL_COVERAGE_V2_APPROVED.json), [private byte-hash audit](G3U_PRIVATE_HASH_AUDIT_V2_APPROVED.json), [risk overlay](G3U_AI_EXACT_LABEL_RISK_OVERLAY_V1.json), [AMD diagnosis](G3U_AMD_THREE_CASE_ORIGINAL_CHUNK_DIAGNOSIS.md), [v2 protocol](G3U_EVALUATION_PROTOCOL_V2_APPROVED.md) and [failure diary](G3U_FAILURE_DIARY.md) contain the reviewable evidence without committing answer values or sealed ranks. The two blind review handoffs remain outside Git.

Next action: real reviewers adjudicate the 12 source-policy cases and original chunk relevance through the guarded tools. The owner verifies reviewer identity separately. Only then can the Tier A/H scoring gates be reassessed; a separate owner decision is required before any human-certified sealed benchmark.
