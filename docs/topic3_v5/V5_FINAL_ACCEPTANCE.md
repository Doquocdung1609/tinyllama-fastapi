# V5 acceptance — 2026-11-02

Decision: `PRODUCT_DEMO_READY / RESEARCH_PARTIAL`; do **not** claim `RESEARCH_EVIDENCE_READY` or `RESEARCH_COMPLETE`.

| Gate | State | Evidence / reason |
|---|---|---|
| G0 assets | PARTIAL | Both ZIPs and corpus hash verified; all 8,670 vectors and native Qdrant snapshots absent |
| G1 baseline fidelity | PARTIAL | Six recorded methods, P7L A/B rows and author source mapped; no live 47-filing rerun |
| G2 failure diagnosis | PASS with qualifications | F01 code circularity, P7G/P7L fiscal filter defect, F10 ranking failures; exact SEC cell ground truth incomplete |
| G3 modular improvement | PASS bounded | Pure same-pool FAITH-R replay, qrel gate, read-only React/API, production routes preserved |
| G4 controlled comparison | PARTIAL | Same Top-10 budget A1/A4; A2/A3/A5 cannot establish separate retrieval/answer gains |
| G5 independent evidence | FAIL/PENDING | 0 newly sealed, human-adjudicated gold questions; exposed F10 labels only |
| G6 working application | PASS | 727 Python tests, React build, Windows Prebuilt launch, live BIDV Compare and actual browser screen |
| G7 defensible report | PASS with limits | Source-to-code, artifacts, failure diary, losing cases and blockers documented |

Research result: 15 exposed development questions, fixed `bm25_dense` Top-10 pool, known-positive chunk top1 3→11; top10 14→14. This is an exploratory ranking result, not exact financial answer correctness. AMZN FY2022/FY2024 and Meta FY2024 CAPEX remain failures, one INTC case becomes unjudged. Human source-first cell adjudication and original Qdrant/vector assets are required before an independent comparison or superiority claim. Repository owner retains final acceptance; no PR merge was performed.
