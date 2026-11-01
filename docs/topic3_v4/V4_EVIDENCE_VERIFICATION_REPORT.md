# Evidence verification

- Hòa Phát: real 24-page mixed/scanned parent-company Q4 2025 PDF; 64 indexed chunks in the isolated demo workspace. OCR exposes VND and comparative quarter headers, but the page 5 table OCR is noisy. No financial cell is locally reviewed, so V4 does not report a verified PDF number or calculate from it.
- BIDV: real 8-page mixed revised 2024 statement; 23 indexed chunks. Page 1 explains the State Audit reason. Page 5 is the separate income statement and page 8 the consolidated income statement; both show “Số liệu đã công bố / Điều chỉnh của KTNN / Số trình bày lại” and `triệu đồng`. Distinct pages and scope matter. V4 does not promote these OCR columns into reviewed values.
- Home Depot: the existing SEC iXBRL pipeline verifies the 2026-08-02 total-assets source cell. The displayed 109,384 million USD is normalized to 109,384,000,000 USD by the existing verifier, with source citation.
- Apple FY2025: no Apple PDF found in the isolated workspace; 359,241 million USD and the `SOURCE_UNIT_COLUMN_AMBIGUOUS` PDF case were not retested. The number is not hardcoded into V4.
- Viewer: clicking a BIDV answer citation opened the original PDF on page 1. When exact geometry is not trusted, the UI opens the page without a fabricated highlight. OCR remains `SOURCE_TEXT_UNREVIEWED`.

These checks establish provenance and safe refusal; they do not establish general exact-cell accuracy for PDF scans.
