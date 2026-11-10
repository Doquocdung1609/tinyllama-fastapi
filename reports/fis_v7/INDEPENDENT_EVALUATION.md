# Independent evaluation

## Release decision

The BIDV regression passes. **V7 has not met the general-purpose acceptance gate.** Four numeric questions on financial layouts from three previously unused public reports returned source excerpts and zero answers with bound numeric cells. These failures remain in the denominator.

## Sets and method

- **Development.** BIDV B01–B09 were known before implementation. All nine passed the stated question obligations in the replay workspace. Multi-PDF C05–C09 passed. C01–C04 remain partial because HPG numeric operands retain OCR candidate status. [Answer matrix](ANSWER_MATRIX.csv)
- **Structural regression.** Five generated-PDF checks passed. They cover a previously unseen label, reordered basis columns, a split heading, English units, parentheses, printed dash, a failed accounting identity, a missing period and a changed source digest. These fixtures are development tests, separate from the reports below. [Test file](../../tests/test_fis_v7_statement_cells.py)
- **Independent layouts.** Expected amounts were transcribed from the published financial table rows with PyMuPDF text and printed column headings, separately from FAITH-R retrieval. They were never used by the answer pipeline. The chosen source pages were copied into small PDF excerpts with geometry preserved. The excerpts were uploaded through FastAPI and indexed by the normal product path. This measures unfamiliar table layouts and real answer behavior. It does not measure end-to-end performance on three complete annual reports.

## Independent results

| Source | Original PDF page and expected cell | Excerpt outcome |
| --- | --- | --- |
| Techcombank annual report 2024 | p. 99, total consolidated assets at 31/12/2024, 978,798,549 million VND | FAIL. Correct page found. No numeric cell or answer. |
| Techcombank annual report 2024 | p. 100, consolidated FY2024 net interest income, 35,507,963 million VND | FAIL. Retrieved the preceding page. No numeric answer. |
| FPT annual report 2024 | p. 150, total consolidated assets at 31/12/2024, 71,999,995,678,620 VND | FAIL. Correct page found. No numeric cell or answer. |
| Toyota Integrated Report 2024 | p. 134, FY2024 total assets, 90,114.2 billion JPY | FAIL. Correct page found. No numeric cell or answer. |

**Excerpt coverage:** 3/3 PDFs READY. Target page present in citations for 3/4 questions. Certified exact cells, bound period/unit, exact numeric answers, complete answers and exact-cell citations each 0/4. Unsupported cases emitted no certified amount in 4/4. Table detection and row identification were not separately certified by independent annotation. The full Techcombank file reached READY with 133 pages and 1,081 chunks. The complete Techcombank total-assets request exceeded the 55 s client budget. The saved server response eventually contained excerpts and zero values. The complete FPT and Toyota reports also reached READY. The full-report checks are below. Measured resource costs and replay logs distinguish these runs from the excerpt subset.

## Complete PDF follow-up

| Check | Pages and indexed chunks | Ingest to READY | Observed result |
| --- | ---: | ---: | --- |
| Techcombank total assets | 133 pages, 1,081 chunks | 503 s | FAIL. Client timed out at 55 s. Persisted response cited p. 99 and p. 125 without a bound amount. |
| Techcombank net interest income | Same source | — | FAIL. Cited pp. 106 and 31 instead of p. 100, without a value. |
| FPT total assets | 215 pages, 915 chunks | 516 s | FAIL. Cited pp. 147 and 11 instead of p. 150, without a value. |
| Toyota total assets | 138 pages, 1,136 chunks | 350 s | FAIL. Retrieved PDF pages 135, 134 without a bound amount. |

READY time includes time waiting behind another import on the same machine. No full-report answer produced an exact, verified cell. These checks do not change the V7 release decision.

The V7 reader handles supported restatement bases, continuation and geometry. These independent examples need broader comparative financial statement and summary table support. They include interleaved notes, date/period headers, different layouts and yen scale. The current evidence shows that recovering a page is insufficient to publish a financial number.

- [Techcombank published report](https://techcombank.com/content/dam/techcombank/public-site/documents/bao-cao-thuong-nien-nam-2024-vie.pdf)
- [FPT published report, FPTS copy](https://file.fpts.com.vn/FileStore2/File/2025/04/03/20250403_FPT_250403_Annual_Report_2024.pdf)
- [Toyota published report](https://global.toyota/pages/global_toyota/ir/library/annual/2024_001_integrated_en.pdf)
- [Independent source hashes, queries and results](unseen-api.json)
