# P11 preregistration and freeze state

The issuer-selection rule was committed before P11 acquisition at `d04fd4b53c104cbc5208ff33bcf876ae7bcbc03e`. Dev query/qrel files were constructed from source inspection before new rankings; their hashes and fixed candidate configuration must be committed before any development score. This is a **development freeze only**, with provisional labels.

Final scientific freeze: **NOT MET**. The 3/3/3 source plan is incomplete (ORCL and DE exceeded 6 MiB), validation/held-out queries and qrels are absent, human relevance review has not occurred, and no adaptive finalist has been selected. Held-out AMGN/BKNG are raw-only; no parser, BM25, Dense or scoring access is authorized while these conditions remain. A new versioned protocol, approved before additional acquisition, would be required to alter the source cap or membership. Do not retroactively alter `p11_partition_manifest.json`.

When eligible, freeze raw and derived hashes, issuer partitions, complete qrels, scoring script, BM25/Dense/F policies, candidate budgets, RRF k=60, timeout/fallback rules, one adaptive finalist and paired analysis. Use equal authenticated parent membership for all arms and distinguish channel failure from ranking quality. The historical C/D5 held-outs are immutable and excluded. P11 development results, if run, remain label-dependent and exploratory.
