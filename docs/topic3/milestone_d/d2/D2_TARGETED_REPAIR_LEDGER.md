# D2 targeted repair ledger

Original source c8d7283bf025e29470acc209961c84b24d576971. Repair14014d2919a55f9cb087deaf120a4dc5d8498d1e. New source-based synthetic regression oracles, not financial market facts.

| ID / severity | File/function and preconditions | Original observed / expected | Narrow repair and regression |
|---|---|---|---|
| AR-D2-01 HIGH | builder.build_table_evidence; initialFY2025, data row, repeatedFY2024 header, later90 | VERIFIED_CONTEXT with periodFY2025 / must not certify stale header | Detect intervening source header spanning the value column; clear period and mark REPEATED_BODY_HEADER_UNRESOLVED. `test_repeated_body_header_cannot_reuse_original_period` th/td |
| AR-D2-02 HIGH | interpretation.units; rawUSD100/$100 under Shares header | SHARES×1000 verified / dimension conflict | Explicit displayed currency against shares is CONFLICTED_CONTEXT; no effective value. `test_displayed_currency_cannot_become_share_count` |
| AR-D2-03 MEDIUM | builder._inline_checks; Net sales row with OperatingIncomeLoss concept | GenericAMOUNT role verified / concept-row correspondence unverified | Any supplied concept name carries INLINE_CONCEPT_ROW_CORRESPONDENCE_UNVERIFIED; existing explicit EPS/fair conflicts remain conflicts. `test_unknown_xbrl_concept_must_not_claim_metric_correspondence` |

Before accepted oracle set:4 FAIL/6 PASS; after:14 new PASS,98 original PASS. Additional four controls test repeated td header, nested table refusal,250001-byte cap and stable repeated reads. No broad rewrite, accepted parser change, new index, ranking change or relaxed guard. Source-limited and opaque-XBRL limitations stay explicit rather than being repaired by guessing.

Tests/commands and CI delivery are in the review/readiness reports and PR #11. Original D2 implementation reports/measurement JSON are preserved as historical evidence, not relabeled after repair.
