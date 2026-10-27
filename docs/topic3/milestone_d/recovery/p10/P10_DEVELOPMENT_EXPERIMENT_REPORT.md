# P10 development experiment

The only P10 retrieval experiment was a functional handshake on two previously inspected development questions and three refusal controls. It used one authenticated three-issuer source generation and a newly built compatible vector generation. B/D/F each executed with identical source membership and explicit 40-candidate budget. `p10_handshake_results.json` preserves statuses, top hits, RRF contributions, B/D candidate IDs, generation/manifest IDs and wall/stage times.

Observed first-run wall times (ms): P&G B 939.3, D 299.9, F 437.0; HD B 759.8, D 262.0, F 418.1. These are five small, warm local diagnostics, not p50/p95 estimates for a broad workload. The first B request included source verification/cache warming; arm order and cache state affect comparisons. No retrieval metric was computed, no adaptive finalist was selected, and no final held-out was opened. Do not infer Hybrid superiority or regression from the displayed ranks.
