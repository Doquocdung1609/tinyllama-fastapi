# Source cells to deterministic claims

Contract `verified-native-operands/v1`: original document SHA, issuer from source, local statement, row definition, column/header box, fiscal year/end, unit/scale, raw Decimal, normalized Decimal, source page/boxes, original retrieved chunk IDs and semantic provenance. Not a human-review stamp or general SEC cryptographic certification of uploaded PDFs.

| Real case | Actual result | Evidence |
|---|---|---|
| Apple-01 | 112,010 million USD, FY2025 | PDF p32, Net income row; FY2025 column September 27, 2025 |
| Apple-02 | Americas, 178,353 million USD | PDF p25; complete five declared regions, totals excluded from argmax; sum checked against Total net sales |
| Apple-03 | 6.43% | p32 Total net sales 416,161 / 391,035; `(416161 - 391035) / 391035 * 100`, Decimal ROUND_HALF_UP to 2 places |

SHA256 `3eb270b22acb7d8d8e9c32a43dc221dec3345f8e4bca02755fdbc1ee16c823de`. Currency proof is the explicit U.S.-dollar presentation sentence on p30 plus the same monetary statement and its local millions header; issuer nationality or a bare dollar sign is insufficient. Fiscal declaration p24 states 2025/2024 fiscal years; actual annual statement headers carry end dates. Segment p25 year headings are bound to these same-source fiscal ends, not filing dates. `period_start` remains absent where not separately derived.

Supplemental lookup: at most four original statement pages may supply headers/cells for a metric named in a retrieved passage. Marked `SUPPLEMENTARY_STATEMENT_LOOKUP`; never counted as a new retrieval hit or ranking improvement. All returned raw cells, row/header/cell boxes and provenance are in `V7P_REAL_APPLE_3_CASES_E2E.json`. No reviewed facts seeded (count=0).

Shared Decimal functions cover extract/difference/growth/ratio/sum/max/min/accounting residual. Eligibility is separate. Automatic native support remains conservative: annual monetary millions with typed context; assets require an instant binder, EPS/attributable/capex/quarters and unsupported units/layouts abstain. Old manual facts missing `TABLE_BOUND_SCOPE_V1` require explicit re-review; no silent migration or rewriting evidence.

Postcondition rejects a producer SUPPORTED label lacking current source membership, hash/page/box or exact operand arithmetic. This is defense in depth behind the source geometry verifier; clients cannot issue verified operands. See permanent new test files and source-derived-negative HTTP records.


Code reviewed/tested: `3e85fdba74737f5a94f555424d283126fe84dc0e`. Starting work-order HEAD: `f3c3fc320d957a4be418054e179e18800f49e5cf`; PR34 base: `cd8deb96cb8c147ca5c090e9c0a323de511c65bd`. Existing Draft [PR35](https://github.com/Doquocdung1609/tinyllama-fastapi/pull/35), branch `codex/topic3-v7p-verified-financial-chatbot`. Same-system Codex adversarial pass, not independent human review. No merge or new PR. Final documentation commit identity is available from Git/PR; this report does not invent a self-referential SHA.

## Final adversarial semantic closure

On the initial implementation, tests reproduced a requested EUR currency being ignored and bare revenue being treated as net sales. The repair refuses unsupported conversion/scale/percentage-point requests and non-equivalent generic metric labels. Segment extrema now require the net-sales metric rather than silently substituting it for segment net income. Explicit restatement basis conflicts are blocked. Permanent tests and real HTTP negatives pass. These fixes narrow claims; they do not introduce FX conversion, restatement synthesis or ranking tuning. Latest focused48/full796/non-integration796 all pass.
