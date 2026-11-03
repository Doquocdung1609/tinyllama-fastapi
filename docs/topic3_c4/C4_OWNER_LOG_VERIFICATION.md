# C4 owner-log verification and source-release gate

The owner supplied the actual `G3T_HUMAN_REVIEW_EVENTS.jsonl`, SHA-256 `be9cd71e6731aa48287c63078737a6f10e1c4fb00c30c191f8a41f72effa3991`. The existing canonical JSON event validator accepted **102/102** append-only hashes and previous-event links. All 102 point to frozen review input V2 SHA-256 `694e55134cc20dc204df02c16bb5397af50e2f4a62088ec04213a0ec026de6e2`. The 94 unique question IDs match that input. Event IDs are distinct. The last four events are #99 `11_02` APPROVE, #100 `12_01` APPROVE bounded negative, #101 `14_02` REQUEST_CORRECTION, and #102 `25_02` REQUEST_CORRECTION with Meta source. Original events were not edited. Final decisions: **86 APPROVE / 7 REQUEST_CORRECTION / 1 EXCLUDE / 0 AMBIGUOUS**.

The supplied `G3T_HUMAN_REVIEW_101_EVENTS_94_CASES_RECHECK_20261103.md` predates event #102. The supplied 94-row status CSV has the same decision totals but its last-event hash for `25_02` still points to event #13; the other 93 hashes match. C4 regenerates eligibility from the 102-event JSONL, not that stale status row. The earlier G3U double-check intake V1 truthfully reported that the original file was then absent; this C4 verification supersedes that availability limitation without rewriting the historical intake.

The existing release-preview function, applied to the frozen review input and new log, returns:

| Category | Questions | Treatment |
| --- | ---: | --- |
| PREVIEW_APPROVED_NOT_GOLD_CERTIFIED | 67 | Source-review preview only; not original-chunk qrels or independently authenticated gold |
| BLOCKED_BY_SOURCE_STRUCTURE | 19 | Structured source evidence still needs review |
| REQUEST_CORRECTION | 7 | Wording/scope corrections remain blocked |
| EXCLUDED | 1 | Excluded before proxy scoring |
| PENDING | 0 | No missing source-review event |

Reviewer identity is **self-declared in the local UI**. A valid hash chain authenticates file continuity, not the human's independent identity or truth of all SEC assertions. No full 47-source rationale re-audit is claimed. The ranked original-chunk qrels still have **zero EXACT and zero human judgments**.

The [pre-scoring eligibility lock](C4_ELIGIBILITY_LOCK_V1.json) was written before C4 inspected ranked outcomes. It freezes **93/94** non-excluded questions for the objective target-filing ID proxy, while preserving all 94 in coverage. No financial answer correctness or certified relevance score was unlocked.
