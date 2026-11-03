# C1 failure taxonomy

The source archive itself passed 47/47 raw-byte verification. A source fact and a retrieval result remain different objects.

| Status | Meaning in this audit |
|---|---|
| `SOURCE_MISSING` | Requested fact absent from the accession-specific primary source after bounded review; no such finding was made automatically. |
| `SOURCE_PRESENT_CORPUS_MISSING` | Requires exhaustive or sufficiently robust frozen-chunk inspection. Three AMD segment questions have no row/value static match and remain `STATIC_TEXT_NOT_FOUND_REQUIRES_MANUAL_CORPUS_CHECK`; this audit does not overstate absence. |
| `PARSER_OR_TABLE_CHUNKING_LOSS` | Requires source and chunk comparison; suspected for AMD segment tables, not proven. |
| `FISCAL_METADATA_MISMATCH` | A/B fiscal correction affects 3,516 points/15 filings as frozen history; not inferred from a missing qrel. |
| `METRIC_SCOPE_PERIOD_UNIT_AMBIGUITY` | Eleven cases split into eight multiple-locator IDs/11 cells and three Amazon required-answer scope IDs. |
| `RETRIEVAL_MISS` | **NOT ASSESSED**: no sealed G2 ranked methods were run. |
| `SOURCE_AND_CHUNK_PRESENT_BUT_UNJUDGED` | Eight of the 11 focus cases have a static matching original chunk; relevance has not been certified. |
| `QUESTION_INVALID_OR_UNANSWERABLE` | Meta `25_02` and Tesla `38_01` have wording conflicts; Microsoft interim policy cases are partial under current evidence. |

The complete 94-question C1 ledger, 11 value-bearing case records, 13 narrative passages and source/corpus diagnostics are held outside Git and hashed in `G3T_PRIVATE_EVIDENCE_MANIFEST.json`.
