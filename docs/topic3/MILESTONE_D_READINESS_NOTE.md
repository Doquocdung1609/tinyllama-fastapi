# Milestone D research readiness — planning only

Milestone C is accepted at `69e6866552d15571858b44707d59a453443fae9c` for a controlled local pilot. No Milestone D implementation or PR is created by this note.

Research problems to resolve before selecting a new implementation:

1. Hybrid can lose BM25 exact-row hits when overlapping irrelevant candidates receive two RRF contributions. Preserve BM25 default and pre-register a small set of fusion strategies for development only.
2. Dense representations confuse adjacent financial rows, repeated headers and boilerplate. Evaluate compact table-row/context representations without stripping signs, units, periods or provenance.
3. Query intent may call for different retrieval paths, but any intent-routing rule must be selected on development data and evaluated once on a fresh holdout.
4. Grounded answer generation needs its own source-coverage, numerical/sign/unit/period verification and abstention evaluation. Retrieval hit rates are insufficient ground truth for answers.
5. Broader issuers, forms, periods and original/amended filing pairs need frozen source bytes and pooled human source judgments. Existing NVDA/WMT holdout is consumed and must not be used to tune.
6. Operational work remains local: external job/admission coordination, Qdrant server auth/TLS, backups/restore, power-loss recovery and larger bounded scaling tests need separate authorization and acceptance gates.

A future proposal should freeze hypotheses, development/held-out assignments, metrics, model/representation identity and resource budgets before experiments. Owner approval is required to begin the next milestone.
