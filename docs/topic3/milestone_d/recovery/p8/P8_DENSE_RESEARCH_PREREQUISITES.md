# P8 Dense/RRF prerequisites

The pinned research snapshot exposes B-channel lexical retrieval only; `FrozenResearchSnapshot.search` rejects non-B channels and there is no compatible research vector collection in this snapshot. A read-only check found the Ollama executable installed but `http://127.0.0.1:11434/api/tags` unreachable. Model digest, vector dimensions, normalization and document/query prefixes therefore cannot be verified as compatible. Dense and RRF remain BLOCKED; no C-equivalent vectors or comparative metrics are claimed.

A future study needs a separately versioned compatible model/vector generation, issuer-separated sources, source-grounded qrels, annotation rules and independent label audit before a new held-out is frozen. Do not reuse the consumed D5 held-out or select a strategy using its observed outcomes. No model download or index build was performed in P8.
