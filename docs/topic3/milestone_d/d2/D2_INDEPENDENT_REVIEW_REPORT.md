# D2 fresh adversarial review

Authorization: TOPIC3_AUTONOMOUS_D2_TO_D5_GATED_EXECUTION_AUTHORIZED. Same Codex system, fresh counterexamples; not independent human review. Original reviewed HEAD `c8d7283bf025e29470acc209961c84b24d576971`; repair implementation `14014d2919a55f9cb087deaf120a4dc5d8498d1e`. Accepted integration remains32c4a4834c5f8a0b34ac28c42f960c862dd8077d.

| Module | Reviewed boundary |
|---|---|
| contracts | Frozen tuple fields, status/numeric coherence; typed structure is not authentication |
| bounds | Iterative size/depth/cycle guards before serialization |
| builder | Physical origins, span hierarchy, completeness, repeated-header and inline correspondence |
| bundle | Single pinned context, explicit D1 period membership, bounded nonrecursive expansion |
| compact | Presentation only, parent/hash retained; not a ranking representation |
| identity | Canonical full payload/view hashing, not an untrusted self-attestation |
| interpretation | Whole-number Decimal, scale/unit/sign; display dimension conflict |
| source | Trusted anchor dependency, raw/metadata/normalized/member checks;250KB source guard |
| package | Exports only, no startup services or production wiring |

Read original98 tests, six fixture families, benchmark and reports. New regression file `tests/test_table_evidence_review.py` has14 cases covering th/td repeated headers, noncontiguous/spanned cells, missing context, nested structure, exact source cap and determinism. The validated minimal original-source inventory produced **4 FAIL/6 PASS**; all14 now pass and original98 remain passing. An earlier draft oracle selected a control row instead of a numeric-label row and overrestricted explicitly labelled change columns; those hypotheses were corrected before classifying findings. They are not counted as defects.

Demonstrated findings: HIGH repeated body header could bind a later FY2024 cell to initial FY2025; HIGH displayed USD/$ could become shares; MEDIUM arbitrary XBRL concept could retain verified context without row correspondence. Each is minimally reproduced in the permanent review suite and repaired conservatively; no accepted B/C parser changed. See targeted ledger for exact functions/behavior.

Compilation passed; focused112 PASS in1.31s; full477 PASS/3 SKIP/1 existing warning in24.64s; core477 PASS/3 deselected/1 warning in35.68s. No disabled tests. Real C source verification succeeded for both retained filings; all six D2 examples are unsupported because source size exceeds the unchanged250KB cap. This is a real-source limit, not six successful D2 mappings.

No demonstrated HIGH/CRITICAL finding remains open after repairs. D2 contracts are eligible for isolated D3 implementation with explicit source-grounded limitations; real-source D2 expansion is not certified. Final delivery HEAD/CI must be verified before D3; exact external metadata is recorded in PR #11 and the next checkpoint event, avoiding self-referential commit IDs.
