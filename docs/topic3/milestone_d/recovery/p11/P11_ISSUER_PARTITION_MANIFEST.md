# P11 issuer-disjoint partitions

Pre-acquisition partition commit: `d04fd4b53c104cbc5208ff33bcf876ae7bcbc03e`; `p11_partition_manifest.json` SHA256 `e62477557a96f316dd96238d4203831aabd8e8cef95956ab112fd9c20b7e78d7`. Dev: ORCL/MCD/CAT; validation: SBUX/UPS/TXN; held-out: DE/AMGN/BKNG. All C/D5 and inspected P&G/HD/COST/JPM issuers were excluded. No issuer occurs in more than one P11 partition.

Observed usable source membership is **2 dev, 3 validation, 2 held-out raw-only**. ORCL and DE were over the fixed source-byte cap. The planned 3/3/3 split is therefore incomplete. Do not call this a complete independent evaluation corpus or substitute issuers based on outcomes. The held-out raw bytes are locally sealed from parser/index/evaluation scripts; no held-out questions or qrels exist.
