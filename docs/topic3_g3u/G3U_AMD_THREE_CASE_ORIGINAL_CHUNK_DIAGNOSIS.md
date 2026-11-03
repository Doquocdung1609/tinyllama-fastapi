# Three AMD original-chunk diagnoses

The source cells exist in the original SEC HTML at the C1 locators, with verified row, period, printed value, currency and scale metadata. The full private V2 diagnosis (SHA-256 `9e4e5acedc3889e4546091267b5d48c7babff37cdff3cfac2936f3b370dbdee1`) records each source locator, inspected original chunk ID/text hash and minimal neighbor excerpt.

| Frozen question | SEC accession | Frozen chunks | Row phrase found | Target value found | Diagnosis |
| --- | --- | ---: | ---: | ---: | --- |
| `09_01` | `0000002488-25-000108` | 68 | 9 | 0 | `SOURCE_PRESENT_CORPUS_CHUNK_MISSING` |
| `10_01` | `0000002488-25-000166` | 69 | 8 | 0 | `SOURCE_PRESENT_CORPUS_CHUNK_MISSING` |
| `10_02` | `0000002488-25-000166` | 69 | 3 | 0 | `SOURCE_PRESENT_CORPUS_CHUNK_MISSING` |

Both AMD filing chunk sets contain only `Part II - Item 1A. Risk Factors` and `Part II - Item 6. Exhibits`: 66+2 and 67+2 chunks respectively. A row phrase appears in risk text but none of the source financial-table values appears in either filing's frozen chunks, including comma and split-digit variants. Neighbor chunks were inspected. The required Part I financial table is absent from the original corpus. This is an ingestion/section-extraction gap at the frozen-corpus boundary. No frozen chunk was changed or synthesized; no source HTML or sidecar earns an original-chunk hit. **Retrieval miss was not assessed**, because rankings were not used for this diagnosis. Human chunk relevance remains separate.
