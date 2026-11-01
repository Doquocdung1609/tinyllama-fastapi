# Research failure diary — actual V5 events

2026-11-02, branch from V4 `a0e6d5a4`, experiment H1: audit both ZIPs with CRC/inventory and frozen corpus hash. Observation: all 8,670 dense and sparse vector fields null, original Qdrant snapshots absent. Hypothesis that exported chunks might contain vectors rejected. Action: preserve originals, extract to untracked directory, use saved Top-10 only. Outcome: no live 47-filing author reproduction. Next: obtain native snapshots from owner/Drive. Script: `scripts/topic3_v5_audit_handoff.py`; raw audit: `handoff_audit.json`.

2026-11-02, H2: initial plain `python` could not run pytest (`No module named pytest`) and direct replay script could not resolve `app`. Cause: system Python instead of project `.venv`, plus script import path. Action: use `.venv/Scripts/python.exe`, add repo root to script path. Outcome: 3 targeted tests passed and replay completed. These were execution/setup failures, not retrieval-method trials.

2026-11-02, H3: fixed label-blind same-pool rerank after preregistration. Known-positive top1 rose 3/15→11/15 on exposed F10 development labels; AMZN FY2022/FY2024 still `NO`, Meta CAPEX still `PARTIAL_NOT_GOLD`, INTC FY2024 `UNJUDGED`. Retain as an exploratory arm; do not tune against these failures and then claim an untouched test. Next: source-first human adjudication and independent new test.
