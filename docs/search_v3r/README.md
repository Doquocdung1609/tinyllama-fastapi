# Search V3R evidence package

Start with [final acceptance](V3R_FINAL_ACCEPTANCE.md) and [owner source checklist](V3R_OWNER_AUDIT_PACKET.md). Recommendation remains PARTIAL. The independent-human gate is pending and the three ACB test misses are preserved.

Required reports: [root cause](V3R_EXTRACTION_ROOT_CAUSE.md),[design](V3R_MIXED_PDF_EXTRACTION_DESIGN.md),[coverage](V3R_EXTRACTION_COVERAGE_REPORT.md),[ablation](V3R_RETRIEVAL_ABLATION.md),[new evaluation](V3R_GENERALIZATION_EVALUATION.md),[performance](V3R_PERFORMANCE_REPORT.md),[owner packet](V3R_OWNER_AUDIT_PACKET.md),[acceptance](V3R_FINAL_ACCEPTANCE.md).

Reproduction tools under scripts/:

1. audit_search_v3r_extraction.py --parent <stopped-parent-root> (repeat for all parents) --output <new-json> --raw-directory <new-private-folder>. It resolves exact PDFs from owned parent files and verifies immutable old checkpoint hashes. Do not rewrite old roots.
2. derive_search_v3r_workspace.py --source <parent> (repeat) --destination studio_workspace/search-v3r-<new-generation> --gate <coverage-json> --output <new-ingestion-json>.
3. migrate_v3r_source_reviews.py --root <new-derived-root> --parent <audited-parent> --output <new-continuity-json>. This carries only identical prior source cells with audited lineage;it never certifies new OCR.
4. benchmark_search_v3r.py --root <derived-root> --old-root <owned-baseline-clone> (repeat) --qrels docs/search_v3/SEARCH_V3_QRELS.jsonl --output <new-json> --sec-root <existing-SEC-source> --sec-vectors <existing-SEC-vectors>. Old comparator roots must be isolated clones. All84questions are exposed regression.
5. freeze_search_v3r.py / freeze_search_v3r.py --verify. Never re-freeze after observing test results and call the same test independent. The current24questions are exposed now;future repairs need fresh evaluation sources/questions for a new generalization claim.
6. ingest_search_v3r_sources.py --manifest <source-manifest> --root studio_workspace/search-v3r-<new-root> --output <new-json>. New source hashes are checked;no original source file is modified.
7. check_search_v3r_live.py --output <new-json>, or add --qrels <existing-regression-qrels> for supported API replays. The default token file is read privately and never printed.
8. profile_search_v3r.py --root <stopped-derived-root> --query <exposed-query> --document <actual-document-id> --output <new-json>. A root cannot be simultaneously owned by the API and CLI.

Do not rerun the24new questions and present them as a new independent test. Published results already expose them. The original JSON results preserve actual failed/missed cases and denominators. Screenshots are actual Chrome results,not UI mockups. Public source SHA/URLs permit retrieval if accessible;original PDFs are intentionally not checked into Git.
