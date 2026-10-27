# P11 human reviewer packet

Open `p11_label_review_queue.json`. For each of its 10 development items, inspect the proposed question, canonical source excerpt, exact table ID/row, source structural locator, original row cells, header rows and period/unit observations. Obtain the official SEC filing via the pinned URL and compare the row/column context against the authenticated raw SHA256 in `p11_source_registry.json`. The visible table might not have a stable fragment anchor; use the structural locator and row label as navigation aids.

Record for each item: relevant grade (0/1/2), all additional eligible parent IDs, period kind/end, unit/scale, consolidated versus segment context, evidence group, uncertainty, reviewer identity and timestamp. Keep initial reviewer records separate; adjudicate disagreements later. Do not view BM25/Dense/RRF ranks while judging. Mark unanswerable only after the specified corpus scope is inspected. Neither this packet nor its generated proposal constitutes human review.

The packet currently covers only MCD and CAT, with 10 proposals and zero completed human reviews. Validation and held-out question packets have **not** been authored.
