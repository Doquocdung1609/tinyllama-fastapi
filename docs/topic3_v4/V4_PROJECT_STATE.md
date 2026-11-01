# V4 checkpoint

- Source: Draft PR #29, commit `b3eedef92824d4f48c8afe69ec40b4e1c197c3b1`.
- Branch: `codex/topic3-v4-financial-intelligence`. PR #28/#29 were not merged.
- Isolated demo workspace: `tmp/topic3/demo-workspace`; owner workspace, research index and model weights remain local and uncommitted.
- Product: PDF document questions use shared production search, a source-bound answer contract, and the existing reviewed-cell Decimal verifier. The React Research Lab labels saved Topic 3 runs separately from live production comparison.
- Scientific status: `RESEARCH_PARTIAL`. Six exposed machine-prepared questions across two alternative SEC filings cannot establish independent efficacy or reproduce the original 47-filings result.
- Local complete regression: 722 Python PASS (one Starlette deprecation warning), 10 frontend PASS, Vite build PASS. PR #30 GitHub Actions run 41299532098 executed and both `test` and `frontend` passed; PR #29's earlier billing block is historical.
- PDF files, indices, token, and local workspace remain uncommitted. Only screenshots of the local UI are included under `screenshots/`.
