# Wrong/refused answer casebook: public index

The full **121-row** private casebook is `C:\Users\Admin\Downloads\C4R_PRIVATE_20261103_V1\C4R_WRONG_ANSWER_CASEBOOK_PRIVATE.md`, SHA-256 `add1d80d63ab1a91f4b79def3cd9c0ac147d7ca4ec840ba30b1310f95b54cde9`. It covers every wrong/refused English-holdout output across nine methods and both answer tracks, with question, source reference value, period, unit, locator, candidate IDs, returned literal or abstention and code location. The complete machine-readable paired ledger is in the private ZIP; its SHA is published in the [public scorecard](C4R_HOLDOUT_SCORECARD.json). The public repo does not contain reference answer values.

| Failure type | Actual finding | Action |
| --- | --- | --- |
| Source-enriched abstention | Stage-2 missed AMD 10-Q `0000002488-25-000108` in Top-5, so the common answerer could not inspect its source cell. A5_BASE retrieved the filing and returned the reference cell. | Retain both outputs; no baseline hiding. |
| Other source-enriched abstentions | Six author methods have 1–3 refusals on the 12 facts, according to the [scorecard](C4R_ANSWER_LEVEL_SCORECARD_VI.md). | Every row and error code preserved. |
| Original-only refusal | All nine methods refuse 12/12 because the frozen chunk representation lacks verified iXBRL column/context binding. | Keep `ORIGINAL_CHUNK_COLUMN_CONTEXT_NOT_VERIFIED`; do not infer a value from a nearby number. |
| Wrong numeric value | **0 observed** in the 12 source-derived facts; this does not establish a general wrong-answer rate. | Keep negative controls and future broader questions. |

There is no A5 loss relative to Stage-2 in this small holdout; the known C4 A4 losses remain documented separately. The source-derived reference has no human signature, and source-enriched answers are distinct from original-chunk qrels.
