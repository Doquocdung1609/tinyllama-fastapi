# Live browser acceptance

The browser used Chromium with the production React build and local FastAPI. No financial answers or SEC discovery responses were substituted.

| Flow | Observed result |
| --- | --- |
| Three selected issuers, one named issuer | Opened the Home Depot 10-Q from a COST + HD + PG selection. The answer showed 47,861 and 89,626 million USD over 13 and 26 weeks. The first citation opened the exact 47,861 cell. |
| Narrative citation | Home Depot reported no material changes to previously disclosed risk factors. Opened the signed narrative citation in the viewer. |
| Microsoft lexical-ready 10-Q | Used the explicitly selected 2025-09-30 accession. The response showed 77,673 million USD. The library displayed BM25 ready while Dense remained pending. |
| EDGAR discovery and import | Discovered and imported real Amazon 10-K and PepsiCo 10-Q into a distinct lexical-only workspace. Opened Chat from each filing’s catalog card. |
| Restart and resume | The main library retained its already published sources. In an isolated interruption simulation, the actual PepsiCo lexical generation was still usable after restarting the API. |
| Apple/BIDV and mixed PDF | The existing Apple and BIDV cited-value checks, their joint PDF retrieval, and the mobile picker passed. |
| SEC multi-generation | The existing real two-filing PG comparison passed on separate generations. |
| HPG OCR V3 | Inventory returned 24 rows. The six-task reconciliation remained five PASS and one PARTIAL, matching the earlier baseline. The capital citation highlighted the source cell on page 20. |

The [SEC browser log](browser-log.json) records actual results. The [API replay](api-replay.json) includes 27 successful source-opening observations, including repeated references. Numeric checks compare the original raw cell value and the column location. Screenshot coverage includes desktop at 100%, Chromium-emulated page scale 125%, and the existing responsive mobile picker. The original known-case data and independent score remain separate.

Local checks were 938 Python tests, 37 Vitest tests and a production build. The source branch and both GitHub Actions jobs are verified in the handoff.
