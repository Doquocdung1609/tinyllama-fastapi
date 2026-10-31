# Reproduction feasibility

**P0 conclusion: PASS for component identification; exact reproduction NOT FEASIBLE from the accessible artifacts.** The supplied PDF is an image-only 23-page article. The pinned public source supplies implementation/configuration and 25 term-based queries, but omits the 47 filings, 8,609-chunk index, immutable source manifest and independent document-level qrels.

The author stack requires FastEmbed BGE-small (384d), Qdrant/bm25 and SPLADE. The product baseline uses locked Nomic 768d and FTS5/other fusion; changing those would destroy the V3R3 control. Run author methods in an isolated environment and collection. Existing two SEC HTML snapshots can support a bounded **methodological replication**, never an exact reproduction of the 47-filing results. New SEC documents may be acquired only with a real configured contact User-Agent and bounded requests.

The pinned author benchmark has a circular relevance denominator and no verified gold IDs. Scientific comparison requires new source-grounded qrels or independently reviewed annotations; term-overlap scores may be shown solely as an author-algorithm diagnostic. `RESEARCH_COMPLETE` and any claim of outperforming the author are unavailable until valid evaluation and all release gates pass.
