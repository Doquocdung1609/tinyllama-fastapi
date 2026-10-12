# Conversational RAG architecture

## Design

- SQLite in WAL mode stores conversations and messages; PDF text is not copied into message rows.
- Every conversation carries 1–20 validated document IDs. Retrieval uses only that scope.
- The resolver keeps bounded recent context for metric, years, pages and source IDs while retaining both original and resolved questions.
- Previous assistant text is conversational context only. Every factual turn calls scoped hybrid retrieval again.
- Deterministic financial operations produce formula, inputs, units, result and evidence IDs before answer rendering.
- Evidence IDs map exactly to prompt chunks and citations are resolved only from included evidence.

## Verification

- Real API multi-turn cases: 12/12 PASS.
- Restart restoration: `True`, 4 messages.
- Duplicate upload: `True`, vectors 36 → 36.
- Unit/integration suite: 55 passed, 3 skipped.
