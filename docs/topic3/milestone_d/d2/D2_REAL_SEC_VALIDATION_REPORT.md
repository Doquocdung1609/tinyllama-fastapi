# D2 retained SEC source diagnostic

Consumed NVIDIA/Walmart sources are development diagnostics only. No new holdout claim, ranking run or acquisition. Command: `python -m scripts.autonomous_source_audit --index <accepted-readonly-lexical-db>`. SQLite URI uses mode=ro&immutable=1; no FinancialIndex/Qdrant constructor opens owner state.

`D2_RETAINED_SOURCE_AUDIT.json` preserves the first run. `D2_RETAINED_SOURCE_AUDIT_v2.json` adds explicitly instrumented stage timing. Both use C `verified_source` in a bounded sequential child process, validate metadata identity/manifest membership/canonical parent hashes, and compare raw/structured/chunk hashes before and after. Accepted SQLite bytes also remain identical.

| Source | Raw SHA256 | Bytes | C provenance | D2 context |
|---|---|---:|---|---|
| WMT sec:0000104169:0000104169-26-000055 |1c34c37ec615ea572ced3dd5e202b084057d262d55a779951cbfca9c3c25ed82|2324095|VERIFIED|UNSUPPORTED_SOURCE_SIZE |
| NVDA sec:0001045810:0001045810-26-000021 |887d559e6180462ecfe36d4c7bba0d8f04a1f63deaaa743ab945edefd9d074bf|1967930|VERIFIED|UNSUPPORTED_SOURCE_SIZE |

All six blueprint parent IDs are present, canonically identical to C reconstruction and source-verified. JSON records issuer/accession, manifest/generation, payload hash, row/cell coordinates, raw values, accepted column labels, inline facts and exact source locators. Income/cashflow/EPS/fair-value use WMT; balance/segment use NVDA. **D2 typed header/period/unit/sign/value observations are not produced for these oversized snapshots.** Their D2 observed value/header fields are null, rather than invented from a sorted period list. Real D2 exact-cell success:0/6 supported examples;6/6 explicitly unsupported due cap, not a false100% mapping score.

Do not bypass250KB. A future streamed source window must retain whole-source byte authentication, exact structural paths, required context/footnotes and parent equality; no such design is silently substituted here. Opaque XBRL context/unit resource definitions also remain unresolved. D2 source-grounded readiness is limited; the stable repaired API can support an isolated D3 implementation, but the planned real table-aware experiment is blocked until source context support is reviewed.

Measured real C verification v2: WMT3026.42ms (byte reads/hash95.23ms, repeat digest98.41ms, parsing2317.39ms, normalization2.60ms, rechunk320.77ms); NVDA1625.29ms (43.49/40.04/1230.90/4.42/163.03ms). Stages are sequential instrumentation inside C, no claimed new cold-disk baseline. Synthetic D2 stage25-sample p50/p95 context1.600/2.544ms, evidence2.969/4.091ms, bundle2.610/4.256ms, compact serialization0.059/0.104ms in D2_AUTONOMOUS_STAGE_LATENCY.json. No D2 HTTP transport exists. Current serialized filing reparse per candidate is visible overhead; no persistent cache or owner-index change was introduced.
