# D2–D5 recovery checkpoint v1

Authorization: `TOPIC3_D2_D5_TARGETED_RECOVERY_AND_REAL_SEC_E2E_AUTHORIZED`. Branch: `codex/topic3-d2-d5-real-sec-recovery`, stacked on D5 `0c6f98e6217e8c7db3162cedd5c0ae827f36e4c1`. PRs #11–#14 and the consumed D5 held-out are retained. This checkpoint does not merge, change main, alter accepted production defaults, or edit accepted corpus/Qdrant data.

The implemented recovery is deliberately narrow: `real-sec-cell-observation/v1` derives an iXBRL cell from a complete C-authenticated SEC source and a committed D3 source registry; `real-sec-cell-request/v1` performs explicit source/period arithmetic with Decimal. It is not wired into default Financial Search, D3 ranking, or the D1→D3→D2→D4 HTTP pipeline. The earlier D2 v1 cap and historical results remain unchanged.

Evidence identity: committed registry `docs/topic3/milestone_d/d3/D3_FRESH_EXACT_ROW_FREEZE_v1.json`; research manifest `86ad36365fbfb813e78e14246a48ae5735d7a8a1218f73daa4289caa98b215d0`; lexical generation `8f0a7ba5ed851313a9948ddb465753c54012d94f9c36942239f7b2ec15b5e2fb`. Probe output: `real_sec_probe_v1.json`. Research root is owner-marked, isolated local data, not the accepted owner corpus.

Go/no-go: **NO-GO for full D2–D5 owner acceptance**. One real SEC cell family is supported; Dense, fair new evaluation, automatic QA and live UI remain unverified. See individual reports for bounded evidence.

Checkpoint commits: `2d5c1521cdf098c79a8e085e70c8ac25e3274c51` introduced the bounded adapter and initial evidence; `4ec3adf4d7bd993883cfe1387c9003f621de0746` added visible-unit/scale verification and its regression. Draft recovery PR: [#15](https://github.com/Doquocdung1609/tinyllama-fastapi/pull/15), targeting the unmerged D5 branch. The HTTP smoke evidence is an additional documentation checkpoint. Final PR HEAD and CI identity must be read from GitHub after this checkpoint is pushed; earlier CI does not validate later commits.
