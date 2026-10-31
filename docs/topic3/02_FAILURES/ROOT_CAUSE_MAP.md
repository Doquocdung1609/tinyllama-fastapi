# Failure-to-intervention map

| Failure | Supported mechanism | Controlled intervention to test | No-go condition |
|---|---|---|---|
| F01, F02 wrong row/metric | Same filing and repeated financial language outrank the exact statement row | Index structured row/column candidates while retaining the fixed-size control | Do not infer exact numeric verification from an OCR or lexical match |
| F03 top-10 candidate miss | Target appears in the wider R4 candidate pool and is promoted by Stage-2 | Compare candidate depth and deterministic evidence compatibility with unchanged corpus/vectors | No claim of a neural reranker or held-out gain |
| F04 unsupported year | No 2037 filing in the corpus but a topical P&G hit appears | Check source period availability before numeric answer composition | No silent substitution with 2026/2025 |
| F05 absent issuer | No Apple filing in the common corpus; cross-issuer candidates are returned | Filter availability and reject absent issuer before answer composition | No plausible number with wrong issuer |

These are hypotheses tied to observed outputs. The frozen six-query set is now **exposed development data**. Any design changes tested on it require a different, independently reviewed set for a generalization claim. The existing V3R3 guards may serve as an engineering reference but cannot be smuggled into author baselines.
