# Scientific claim/evidence matrix

| Claim | Evidence | Status |
|---|---|---|
| One real P&G SEC net-sales cell has authenticated source, exact physical coordinate, quarter, USD scale and source locator | `real_sec_probe_v1.json`; committed raw hash; C reconstruction; adapter tests | VERIFIED_WITH_LIMITATIONS |
| Two real comparable P&G cells support Decimal extraction, comparison, absolute and percent change | Four supported probe operations, same parent/table/row/fact/unit | VERIFIED_WITH_LIMITATIONS; explicitly selected source |
| Missing period produces no numeric claim | Fifth probe case, 2024 period absent | VERIFIED |
| All six retained SEC table families work | Earlier six D2 v1 cases remain oversized and unrecovered | NOT_TESTED / unsupported |
| Dense/RRF/adaptive quality | Ollama unreachable; no compatible research vectors or valid D/F runs | NOT_TESTED |
| Automatic question-to-answer research product | D1 column metadata uncertainty, target lexical rank 28, no live API/UI path | NOT_VERIFIED |
| General numeric-answer accuracy or false-abstention rate | No new labeled representative dataset | NOT_TESTED |
| New held-out improvement | Consumed D5 held-out preserved; new freeze not created | NOT_TESTED |
| Production readiness or hybrid superiority | No supporting study | NOT_CLAIMED |

The historical C conclusion remains: BM25 is the recommended default on its evaluated corpus; Hybrid superiority was not established. This checkpoint does not modify that conclusion or the accepted scientific blobs.
