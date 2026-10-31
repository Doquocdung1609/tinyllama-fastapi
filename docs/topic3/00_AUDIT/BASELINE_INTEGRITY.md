# Baseline integrity and evidence limits

The research branch `codex/topic3-reproduction-improvement` was created from Draft PR #28 head `f5b3b619be12aa0b6d8f7e62b349eb8a634e57ef`; PR #28 itself is Draft and stacked on PR #27 head `006d056d47ce1e417befd965937e38536045850a`. No reset or merge occurred. Existing untracked `output/` and `tmp/search-v3r3/` were preserved.

The pinned paper, original author commit, author 25-query YAML hash, two available SEC HTML hashes, nine owner-PDF hashes and three V3R3 artifact hashes are recorded in `REPOSITORY_INVENTORY.json`. The V3R3 workbook audit recorded 26 blank human decisions and 30 matching source references (`../../search_v3r3/BASELINE_AUDIT.json`). Historical 178-query metrics remain exposed regression, including the recorded `LOW_MEMORY_DEFERRED` final prewarm. No independently reviewed gold was inferred.

The author Git repository includes `data/benchmark_report.md` but no 47-filing raw corpus, chunk file, or per-query benchmark run. Its 25-question YAML contains term lists, not stable relevant chunk IDs. This prevents an exact replay of published retrieval metrics even if the FastEmbed model weights become available. All future comparisons must lock a new corpus, dataset generation, model digests and qrels before changing a policy.
