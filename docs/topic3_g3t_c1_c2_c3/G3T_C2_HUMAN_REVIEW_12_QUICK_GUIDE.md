# Human review: twelve priority cases

The twelve-case source-first packet is `G3T_C2_TWELVE_DISPUTE_CASEBOOK.md` in the private C2 handoff (SHA-256 `835a9cfa57dd9ecb21b1a1a4d654d8a70b62be79a0c314d9b9a424ccea046785`). The nine earlier dispute cases and three post-source cases are represented once each; `12_02`, `14_02`, and `15_01` reuse C1 evidence IDs. The public 94-row queue is `G3T_C2_HUMAN_REVIEW_QUEUE_94.csv`.

Start the local review server with the V3 input dataset and a separate human-event path. It shows the source, both independent agent positions, the new AI proposal and its limitation, then an empty human form. Inspect the original SEC page and choose a decision personally, with a source locator and reason. An AI proposal or agreement is not an approval. Save only actual reviewer decisions. The event log is append-only and hash chained, but a self-declared reviewer name is not cryptographic identity proof; a responsible review owner must validate identity outside this tool.

Current input dataset: `G3T_HUMAN_REVIEW_INPUT_20261103_V2.json`, private owner-machine handoff, SHA-256 `694e55134cc20dc204df02c16bb5397af50e2f4a62088ec04213a0ec026de6e2`. Current human events: **0**. The AI ledger must never be imported as human events. Review the twelve first, then the remaining 82. Preserve the ledger and any corrections as separate versioned events.
