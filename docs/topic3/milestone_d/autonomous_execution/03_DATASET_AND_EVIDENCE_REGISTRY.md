# Dataset and evidence registry

Historical original14/intermediate/issuer-heldout are consumed, never new unbiased holdout. D2 WMT/NVDA source diagnostics reuse consumed issuers only; no new ranking. All new D2 fixtures are synthetic. Fresh research sources/queries/qrels/splits are NOT_FROZEN. No ranking on a fresh set before freeze. Registry additions must name source URL/accession/date/hash and acquisition outcome.


## D3 checkpoint addition

Fresh owned research source registryv2:PG/COST/HD, exact-row freeze86ad3636…; queries5dev/6validation/5heldout, mechanical source labels with0human annotators. JPM excluded by fixed4MB size cap before ranking. Dev/validation scored, heldout NOT_OPENED. Raw sources/structured/chunks/index only in owned research namespace; no C dataset re-ingestion.

## D5 consumed held-out registry v2

The previously unopened five-query HD partition (`70c52b601f3da535ad12d0041abf04df73832f8e9681058ae73e928e0e5bf843`) was opened once after D5 preregistration hash `ce2c362b9cf894b523ec47b1cd6bae87b8f377e5cdc8cc9275247b7a369e71c7`. It is now **consumed**; do not retune and reuse it as a fresh holdout. PG/COST/HD raw hashes revalidated true. The synthetic D4 QA fixture `5e6a46bc75f64eba82cbf95337000627b0aacc9698eb2e989956c4e6acff1778` is distinct from the official SEC source corpus.
