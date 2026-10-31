# Confirmed gaps, hypotheses and dependencies

## Confirmed

1. Original author code's `BenchmarkRunner` derives relevant IDs only from each method's own retrieved top-k. The reported Recall@10 is therefore not corpus recall; it becomes 1 when any returned item passes the term threshold and cannot count missed relevant chunks. `Precision@10`, MRR and nDCG use the same generated term-overlap judgment. This is a confirmed measurement defect, not evidence that hybrid search cannot work.
2. The class named `NeuralReranker` never loads or executes `model_name`; it computes regex/token/metadata feature scores. Paper descriptions of neural cross-feature attention do not match this pinned code.
3. The 47 raw author filings and 8,609 chunks are absent from the pinned public checkout. The local two SEC HTML and nine PDF reports have different dates and issuers. Exact reproduction is unavailable.
4. The public README's quality table differs from its committed `data/benchmark_report.md` (for example BM25 Recall@10 0.8133 versus 0.9600), without raw per-query outputs to adjudicate. The PDF's CPU latency claims also differ from that report by orders of magnitude. Treat all as author-reported variants.
5. `fastembed` was absent from the product `.venv`; original dependencies are being installed into a separate environment. The author configuration has `research@example.com` as a placeholder SEC contact and must not be used for live downloads.
6. Three additional documents named by the work order (`Markdown đã dán (1)(20261031-061653).md`, `Văn bản đã dán (2)(1).txt`, `Markdown đã dán (3).md`) were not found in the supplied files, Downloads, or accessible attachments checked. Their contents have not been assumed.

## Hypotheses to test

- Structure-aware rows and source-grounded period/unit alignment can improve exact financial evidence over fixed-size chunks on a locked common corpus.
- Author-style BM25 + Dense fusion may beat single arms on some vocabulary-mismatch questions, but the original published 96% is not a valid comparison target without independent qrels.
- On this 16 GiB Windows host, sequential model loading and bounded batches may permit a small SPLADE methodological replication; a full 8,609-chunk run may exceed safe RAM during live product use.

## External/human dependencies

- A source-verified independent annotation set and reviewer signoff are needed for a held-out scientific claim.
- Exact original corpus snapshot and historical model digests are needed for exact reproduction; neither is in the public checkout.
- GitHub Actions for PR #28 failed before test steps because of account billing/spending limits, not test failures.
