# Question validity and overlap

The 94 G2 questions remain unchanged. The frozen [G2 overlap audit](../topic3_v7a_g2/V7A_QUESTION_OVERLAP_AUDIT.csv) has eight `POTENTIAL_SOURCE_CELL_OVERLAP` rows across six unique questions: `02_02`, `05_01`, `05_02`, `29_02`, `31_02`, `40_02` (all with `V7A_G2_` prefix). Each row matches accession, metric and period in a reference set. Exact question wording is marked unseen, while provisional cell/document/issuer-unseen status is false for these rows. This does not establish contamination of every question, nor justify describing the whole set as cell-, document- or issuer-unseen.

Three post-source questions remain unresolved: Microsoft `30_01` and `32_01` request a full revenue-recognition policy from a 10-Q whose source may support only narrower judgments; Tesla `38_01` asks for a reporting unit for an accounting-policy disclosure. Historical `25_02` uses “as-of” for a year-ended cash-flow measure. These require human disposition or prospective errata. Any exclusion must explicitly change the evaluation denominator in a versioned release; the frozen wording must not be silently altered.

Source verification and overlap inspection did not run FAITH-R or any sealed retrieval configuration. Original F10 Policy B still credits only retrieved original single chunks.
