# Milestone C final security review — 2026-10-25

Reviewed source: `a6c3d6ff449e7ba7f783f548340a2b8ab76c1521`; target `b7fd390e39f5ba6a1031ff210181c009dbf362ed`, merge base `c84c060d1bbf507b01badb8073f22cbf53b9b7ec`. The target-only commit adds environment handoff files; candidate merge has no conflicts.

## Controls inspected and exercised

| Area | Evidence | Result |
|---|---|---|
| Mutation authentication | All build/activate/protect/cleanup routes depend on `require_financial_admin`; constant-time Bearer check, token absent configuration denies; live missing token activation returns 401 | VERIFIED |
| Authorization before mutation | Dependency resolves before route side effects; queue/cooldown/body/model validation tests | VERIFIED |
| Qdrant ownership | Kernel lock, second-process rejection and recovery after termination; server mode separate | FIXTURE_VERIFIED |
| Retention | Shared mutation lock and eligibility recheck inside lock; active/pin/evaluation/rollback protections, stale-plan regression and interruption retry | FIXTURE_VERIFIED |
| Provenance cache | Generation/hash/parser/chunker/policy key, bounded LRU, single-flight, every-request SHA-256, fail-closed tamper/TOCTOU tests | VERIFIED |
| Paths and writes | Canonical source identities, bounded Windows paths, atomic replace with temp cleanup; isolated regression data | FIXTURE_VERIFIED |
| SQL/errors | Values parameterized; dynamic columns use explicit allowlist; financial search/mutations return stable codes | VERIFIED_WITH_LIMITATIONS |

Targeted suite before compatibility repair: 59 PASS. After repair persistent + hardening suite: 29 PASS. Full source suite: 195 PASS, 3 SKIP, 1 warning, 73.34 seconds, Python 3.13.2. Core CI on `a6c3d6f`: run `40166961872`, success.

## Integration blocker resolved

Live smoke revealed that the review index was written with qdrant-client 1.20.0, while the owner environment had 1.19.1. The older client rejected persisted `id_tracker: null`; Dense/Hybrid returned 503 and retention could return 500. No index file was edited to bypass validation. Commit `a6c3d6f` pins the tested 1.20 minor line and adds early embedded-client version enforcement plus regression. After installing 1.20.0, exact 320-point membership validation, Dense/Hybrid, retention and authorized activation succeeded.

This repair is a dependency/format compatibility constraint, not an on-disk migration. Historical 1.19 collections must be backed up and tested with the pinned client before operational use; no owner historical Qdrant directory was opened or rewritten by this acceptance run.

## Remaining limits

Controlled local pilot only: read routes retain legacy access; no distributed admission/auth coordinator; Qdrant server TLS/API-key configuration and power-loss/restore tests remain out of scope. Inventory GET endpoints do not uniformly map storage-open failures to structured errors. Local administrator control of both index and manifests is outside the source-tamper threat model. No unresolved critical defect within the controlled single-owner scope was found after the compatibility repair.
