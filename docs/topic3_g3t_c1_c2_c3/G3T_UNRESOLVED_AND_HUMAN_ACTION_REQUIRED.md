# Unresolved work and required human action

1. A qualified reviewer must adjudicate the three Amazon comparative-scope questions (`12_02`, `14_02`, `15_01`) and other ambiguous/partial/invalid cases using the original SEC locator. The twelve priority packets should be reviewed first. The 13 narrative cases require proposition-level sufficiency checks.
2. Check the three AMD original chunks (`09_01`, `10_01`, `10_02`) manually. The static row/value search did not find them. Do not infer a corpus defect or give retrieval credit before inspection.
3. A real human reviewer must record decisions through the guarded local UI. The current human event count is zero. Review ownership must independently validate reviewer identity because the tool accepts self-declared names.
4. Construct the fixed-depth original-chunk pool for the six author arms and FAITH-R arms under the locked protocol, then judge actual original chunk relevance. The current 17,153 UNJUDGED pairs remain unknown, and zero pairs have EXACT judgments. Do not run/scored a benchmark from them.
5. After actual gold and qrels coverage gates pass, obtain explicit owner signoff for the sealed human-certified final benchmark. Keep any AI provisional research output separately labelled.
