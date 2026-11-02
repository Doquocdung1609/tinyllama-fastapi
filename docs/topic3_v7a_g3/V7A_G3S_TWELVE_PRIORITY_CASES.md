# Twelve priority review cases

These are coordinator recommendations based on preserved SEC source and the two independent AI positions. They are **not human decisions**. Source accessions, hashes, excerpts and original agent fields are in the private G3R nine-case book (SHA-256 `cf60baaee6a2719a49ebd0aa94a3a6ca627f3b442a7c815ba9a56ab5529025f2`) and the G3S review dataset. All human decisions remain blank.

| Question ID suffix | Source-backed issue | Proposed human disposition |
|---|---|---|
| `05_01` | Apple statement uses “Total cost of sales”; frozen question says “cost of revenue.” | Decide whether those terms are equivalent in this scope. |
| `09_02` | AMD “Client” is a business line within Client and Gaming, not a standalone reportable segment. | Conditional support only with the segment qualifier. |
| `12_01` | Amazon consolidated operations statement has no standalone Gross profit row; a narrower table differs. | Bounded `NEGATIVE_SUPPORTED` for consolidated line-item existence only. |
| `12_02` | Amazon current and prior operating-income cells agree, but Agent 1 included a second comparative year. | Define the minimum required comparative set. |
| `14_02` | Amazon 10-Q has three-month and six-month operating-expense pairs. | Fix question period scope before exact scoring. |
| `15_01` | Amazon balance-sheet as-of cell agrees; Agent 2 supplied an extra prior comparison. | Treat prior cell as supplemental. |
| `21_01` | Gross margin appears as USD amount and percentage. | Resolve representation/unit ambiguity by review policy. |
| `24_01` | Source says Cost of sales; question says cost of revenue. | Decide synonym scope and bind the three-month column. |
| `25_02` | Cash flow is year-ended, while frozen question says “as-of.” | Prospective erratum or exclusion from strict period scoring. |
| `30_01` | Microsoft 10-Q has narrower revenue-recognition disclosures than a complete annual policy. | Check if full answer is supported; otherwise partial/source insufficient. |
| `32_01` | Same Microsoft policy-scope issue for a later 10-Q. | Check full proposition; otherwise partial/source insufficient. |
| `38_01` | Tesla accounting-policy question asks for a numeric-style reporting unit. | Mark ambiguous or issue a prospective wording erratum/exclusion. |

For `12_01`, absence is bounded to the actual consolidated statement and is not inferred from a failed keyword search. For `12_02`, `14_02`, `15_01` and `24_01`, the archived HTML contains relevant cells, but the required answer set/semantics still needs a reviewer. Each case links to its accession-specific SEC HTML through the review tool. No majority-AI rule is used.
