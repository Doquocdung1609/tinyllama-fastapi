# V7A G3 source-only handoff

**Result: 9/9 official SEC primary HTML responses acquired; 9/9 passed source accession, primary-file and filing-form index checks.** This is source acquisition only. It does not approve any gold answer or complete G3 review.

## Local package

- File: `C:\Users\Admin\Downloads\V7A_G3_SEC9_SOURCE_HANDOFF_20261102.zip`
- ZIP SHA-256: `7a300a6a62da3a49a478c22b69e9803837cca4240c194c10d883fb555dc9c51d`
- Acquisition manifest SHA-256: `071d489f6bfea7af1f9e644512bc86fb78f61a8f59480b6b33000bb9018bf27f`
- Input G3 checkpoint ZIP SHA-256: `e3225aada3a05ef0b9218b7fa885df8600e97eccae3618cba3bb95ffbe505e07`
- Input nine-source CSV SHA-256: `ca4165ad6a31484323e2f49e5c310e849fdae8c90821ba840d65ec624f754095`
- Frozen G2 filing metadata matched the nine accession, ticker, form and exact URL tuples before acquisition.

The ZIP includes the nine byte-preserved SEC primary HTML responses, nine SEC directory listings, nine SEC filing-index HTML pages, a full metadata manifest, a missing-source report and `SHA256SUMS.txt`. The same validated ZIP can be supplied independently to each reviewer; no reviewer's annotations are inside it. The ZIP was checked with CRC, all internal SHA-256 entries, and nine source identity checks. Its hash was unchanged by a second finalization run.

## Boundary and limitation

The primary HTML responses total 67,415,482 bytes, with balanced table tags and closing HTML boundaries. Each SEC-served response is 109 bytes larger than its index-listed primary size and ends with an added script tag. The returned bytes were preserved exactly; byte equivalence to an earlier archival representation is **not established**. Filing indexes list 6–26 separate exhibit files per filing. Exhibit bodies and complete-submission text files were outside this bounded nine-primary-document task and are absent from the package.

No answer values, gold labels, ranking results, corpus chunks or product files were read or changed. The two independent reviewers must verify their own evidence from these sources; this package itself is not a gold judgment.
