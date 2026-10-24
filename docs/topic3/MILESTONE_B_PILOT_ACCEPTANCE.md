# Milestone B pilot acceptance — 24/10/2026

**ACCEPTED — VERIFIED_WITH_DOCUMENTED_LIMITATIONS FOR FINANCIAL CORPUS PILOT**

Owner authorization: TOPIC3_MILESTONE_B_PILOT_ACCEPTANCE_AND_MILESTONE_C_CONDITIONAL_IMPLEMENTATION. This accepts the scoped pilot after successful controlled integration, not production readiness or perfect financial answering.

## Integration identity

- Original target base: `de01cbd4157fcbfdcac3201aed7e2f89ba3b3044`.
- Initially reviewed source: `bf7be205a03292eac8b08bd2ee8f8df7fb8161c6`.
- Source after required path-validation repair: `bdd12d895a7942ca7763bda7f81e3e735153aa6a`.
- Exact local candidate merge tested: `22563b6cbdb5e1adeefbb72613118056c4fd8e04`, parents target/source above.
- PR #7 merged by normal merge commit into `codex/topic3-milestone-b-sec-corpus` at 2026-10-24T15:49:54Z.
- Actual integration commit: `bde80f6d672f1744b54ec669300a86844139c54f`.
- The fetched integrated tree equals the tested candidate tree. `main` is unchanged. No admin override, force-push or branch-protection bypass.

GitHub's first synthetic merge ref still referenced the old source, so it was not used as verification evidence. A local isolated merge candidate from the current exact parents was constructed and tested; the actual GitHub result was compared against it after merging.

## Executed gates

1. Source/security review identified a required path-validation defect; fixed and regression-tested on the PR branch before integration. See MILESTONE_B_INTEGRATION_REVIEW.md.
2. Candidate full regression, with RUN_REAL_MEDIA_TESTS=1: **169 passed / 0 failed / 0 skipped / 2 warnings**, 26.50 seconds.
3. Fetched merged branch full regression: **169 passed / 0 failed / 0 skipped / 2 warnings**, 25.49 seconds.
4. Apple audit: 40 tables, 4,762 cells, no mismatches, 28 financial-context cases and 12 provenance samples; 566 chunks with stable IDs/manifest. Whole-filing PARTIAL remains.
5. Real Tesla original/amendment, original raw/manifest preservation and repeat ingestion passed.
6. Controlled restart/recovery, source tamper detection, status consistency, API path safety and historical-preservation regression passed.
7. Real legacy Chat/RAG smoke: all five checks pass. Existing isolated Qdrant collection remains online with exactly 3 vectors, dimension 768, before/after integration. Only `independent-verification` exists in this machine's Qdrant directory; owner's historical `knowledgebase` was not transferred, initialized, overwritten or deleted.
8. Eight historical manifest/raw-file checks remain valid. No private configuration, raw corpus, weights, databases or vector files are committed.

Commands: `.venv/Scripts/python.exe -m pytest -q -rs` with real-media/OCR settings documented in the environment report; `scripts/audit_preserved_corpus.py`, `scripts/verify_milestone_b.py`, `scripts/audit_live_amendment.py`, and `scripts/verify_local_integration.py` with the isolated roots recorded in earlier evidence. Outputs are preserved under `tmp/milestone_b_verification/integration-*` (ignored).

The two warnings remain Starlette/httpx and Diffusers/NumPy deprecations. Missing GitHub CI checks were not counted as passed CI.

## Retained limitations

- Four administrative/navigation tables retain conservative partial extraction; no forced READY conversion or automatic completeness certification.
- Historical derived-chunk API lookup is active-revision-only; immutable files/manifests remain accessible locally.
- Real 10-K/A is verified; 10-Q/A remains fixture-tested; recovery is controlled, not an OS power-loss experiment.
- Representative pilot source evidence is not all-issuer or production-scale validation.
- General Chat can confuse financial concepts; grounded advisory accuracy is not accepted here.
- At this acceptance point, SEC chunks are not yet semantically indexed. That work belongs to conditionally authorized Milestone C.

All Milestone C entry conditions are satisfied by the recorded integrated code and the scoped pilot acceptance. The follow-up documentation-only acceptance commit is the C branch base; its code tree matches the tested merge. Record both that exact base and the integration commit in Milestone C reports. Milestone C's PR must remain Draft/unmerged.
