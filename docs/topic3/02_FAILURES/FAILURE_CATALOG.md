# Failure catalog

Five observed, source-located cases and their actual Top-10 outcomes are in `FAILURE_CATALOG.jsonl` and explained in `FAILURE_CASE_STUDIES.md`. They cover wrong consolidated-row priority, wrong metric at Rank 1, stage-1 candidate-depth miss, unavailable future period and absent issuer. The two negative cases are **retrieval risks**, not demonstrated wrong numeric answers. Source target labels are machine-prepared and need independent review. The script `scripts/topic3_failure_catalog.py` rebuilds the catalog from frozen qrels and measured retrieval records.
