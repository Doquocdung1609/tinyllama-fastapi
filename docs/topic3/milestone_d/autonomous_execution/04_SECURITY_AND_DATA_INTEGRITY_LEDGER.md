# Security and data integrity ledger

D2 HIGH repeated-header and currency-dimension findings repaired with permanent tests; concept correspondence remains explicitly unresolved. Owner index opened only via read-only SQLite URI; C byte verification child processes use reads only. Raw/structured/chunk/index hashes unchanged after diagnostics. No owner Qdrant directory opened. Accepted baseline Git blobs preserved. Python schema/hash validation is not authentication of an untrusted anchor.


## D3 checkpoint addition

D3 development regressions now block provenance-error fallback, unverified explicit cell-period scope and nested C guard calls. Source/identity failure never uses operational Dense fallback. All new I/O source paths constrained to owned root. Model/collection identity remains required. Existing C/D1 files untouched; PRs remain Draft.

## D4/D5 security snapshot v2

Separate research API is default-deny without configuration, Bearer-protected when configured, bounded to 16 KiB requests and one concurrent query; no mutation route. A fail-first non-ASCII Authorization 500 was fixed and locked as 401. Actual unauthenticated HTTP returned 401. D4 reconstruction rejected altered source-bound claim/citation; D5 offline synthetic ablation rejected 5/5 deliberate forgeries. All 550 accepted baseline Git blobs were unchanged, and three newly owned SEC raw hashes rechecked true. Real owner index/Qdrant history was not modified. Live publication/read concurrency and broad penetration testing remain unverified.
