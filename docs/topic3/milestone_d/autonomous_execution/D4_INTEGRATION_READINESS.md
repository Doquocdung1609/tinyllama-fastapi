# D4 checkpoint and integration readiness

Status: **D4_DETERMINISTIC_ONLY**. The separate research package, API and UI are opt-in; accepted Financial Search, Chat/RAG routes and BM25 default are unchanged. Unit/in-process fixture verification passed, and no historical owner corpus or vector store was mutated. D4 is suitable for Draft PR review as a bounded prototype.

Real SEC numeric QA is blocked by D2's unchanged source-size ceiling. Dense/fusion quality is blocked by absent compatible local Ollama. The synthetic fixture is useful for arithmetic and safe failure checks but cannot establish real-world financial-answer correctness. Before any production activation, source-size-safe real D2 context extraction, independent source labeling, model identity and broader issuer/period testing are required. D5 may run a once-frozen heldout lexical diagnostic and safe live API/UI checks, while preserving these blockers. No merge authorization is implied.
