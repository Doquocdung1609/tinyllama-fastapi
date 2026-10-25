# Milestone C integration report

Status: **MILESTONE_C_ACCEPTED_WITH_DOCUMENTED_LIMITATIONS**

Accepted scope: controlled local Financial Intelligence pilot. Owner authorization: `TOPIC3_MILESTONE_C_OWNER_ACCEPTANCE_AND_CONTROLLED_INTEGRATION_AUTHORIZED`, resumed under `TOPIC3_MILESTONE_C_UI_ACCEPTANCE_RECOVERY`.

## Exact integration identity

| Item | Value |
|---|---|
| PR | https://github.com/Doquocdung1609/tinyllama-fastapi/pull/8 |
| Final PR state | CLOSED, merged=true, draft=false |
| Source branch | codex/topic3-milestone-c-persistent-hybrid |
| Expected starting source | a6c3d6ff449e7ba7f783f548340a2b8ab76c1521 |
| Final source | 4dfe5141dfc4ba8caf612caba72d3d7e8bdf164b |
| Target branch | codex/topic3-milestone-b-sec-corpus |
| Target before merge | b7fd390e39f5ba6a1031ff210181c009dbf362ed |
| Merge base | c84c060d1bbf507b01badb8073f22cbf53b9b7ec |
| Accepted merge commit | 69e6866552d15571858b44707d59a453443fae9c |
| Accepted tree | a2ed0487c94dfc8e88b0d93e7e0473c059c0e197 |
| GitHub CI candidate | b1feeca006a8a061d2a19ad86bf60d52305f7db4 |
| CI run / job | 40168878980 / 121095478636 |
| main before/after | ceaa8acfcfaea8056e45b859a0fc44d6381fb22a |

Source advanced after the expected checkpoint only by `3ac69a3` (live acceptance evidence) and `4dfe514` (LF checkout policy and explanation). No retrieval algorithm, query judgment or historical metric changed. Qdrant compatibility repair is `a6c3d6f`; its full regression passed before this resume.

## Candidate and CI verification

An isolated worktree merged current target with final source using `git merge --no-commit --no-ff`. No conflicts, unresolved files, dependency/route/configuration conflict or competing code commit was found. Target-only commit adds environment handoff files. Historical B integration `bde80f6` is an ancestor.

`git fetch origin refs/pull/8/merge` confirmed both parents (target b7fd390, source 4dfe514). Its tree exactly equals the tested local candidate and final merge tree. GitHub job logs confirm checkout of `b1feeca`, dependency installation, compileall, and actual pytest execution. CI result: **194 passed, 1 skipped, 3 deselected, 1 warning in 7.30s**. The extra Linux skip is the Tesseract-dependent multimodal test; the three deselections are opt-in real image/SAPI/ffmpeg integrations. There were no failing checks. Merge used the standard GitHub endpoint with expected source SHA and `merge_method=merge`, without protection override, squash, force-push or branch deletion.

## Commands and observed regression

Python 3.13.2, owner venv with qdrant-client 1.20.0. `SCORE_THRESHOLD=0.55` matches owner configuration.

```powershell
python -m compileall -q app scripts
python -m pytest -q
python -m pytest -q -m "not integration"
```

| Phase | Result |
|---|---|
| Pre-repair initial candidate full | 194 PASS, 3 SKIP, 1 warning, 20.66s |
| Targeted security/ingestion/search/persistent | 59 PASS, 1 warning, 19.94s |
| Compatibility-repaired source full | 195 PASS, 3 SKIP, 1 warning, 73.34s |
| Evidence candidate full | 195 PASS, 3 SKIP, 1 warning, 24.97s |
| Final fresh candidate core | 195 PASS, 3 deselected, 1 warning, 23.32s |
| Exact merge commit full | 195 PASS, 3 SKIP, 1 warning, 23.95s |
| Exact merge commit core | 195 PASS, 3 deselected, 1 warning, 34.13s |

The +1 from 194 is the embedded-client compatibility guard regression. No old test was deleted or disabled. Warning: Starlette/httpx TestClient deprecation. Real-media opt-in tests were not rerun in this acceptance; local Tesseract-dependent core did pass.

## Live product and scientific checks

The old stopped Windows input session was left stopped. A new authorized browser opened explicit Streamlit URL, verified URL/title, exercised BM25, Dense and Hybrid, inspected issuer/form/period and partial warning, expanded provenance JSON, and opened SEC source in another tab. Legacy Chat/RAG pages were accessible. Isolated fixture upload reached READY and real embedding/Qdrant retrieval returned page/table/bbox evidence. See `MILESTONE_C_PRODUCT_SMOKE_TEST.md` and screenshots.

After checkout of exact merge commit, FastAPI and Streamlit restarted. Live post-merge HTTP checks: health/datasets/BM25/Dense/Hybrid/Chat/RAG = 200; missing-token activation = 401; invalid generation = 409. Five unique financial hits per mode had VERIFIED provenance and correct ticker/generation. Post-merge UI returned Walmart Note 2 EPS table and source controls. `reports/milestone_c_acceptance/postmerge_smoke.json` and `financial_search_postmerge.png` preserve this evidence.

Scientific freeze rechecked byte hashes and independently recomputed held-out metrics from saved ranked IDs and qrels. BM25 remains recommended default. Fresh checkout initially exposed CRLF hash drift; explicit LF attributes repaired portability without changing frozen Git blobs. Cache recheck on same fixed corpus (6 questions, 3 modes, 18 measurements per arm) gave disabled/cache total p50 **1473.13/212.86 ms**, provenance p50 **1302.68/80.34 ms**. This confirms the mechanism; original 1558/238 ms evidence remains untouched. The recheck ran alongside isolated regression work and is not a clean comparative throughput claim.

Post-integration hash audit distinguishes original workstation CRLF hashes from canonical LF blob hashes. Scientific freeze has an appended canonical table; all ten pinned artifact Git blobs compare identical between `4eee5de` and `69e6866`. Existing hash tables are retained as historical evidence rather than silently replaced.

## Data integrity

Owner historical directories were never used by smoke API/index operations. Six existing owner files under `financial_corpus` and `qdrant_data` were SHA-256 inventoried before final integration and again after merge/workflow smoke; all identical. These include registry/WAL/SHM and legacy knowledgebase meta/storage/lock. Only those available files are claimed live-preserved. SEC experiments used retained isolated `C:\msch`; no historical collection, SEC snapshot or manifest was deleted. Source commits and accepted B merge remain reachable from target. Main was unchanged.

## Gate ledger

| Gate | Status | Evidence |
|---|---|---|
| G01 Git baseline | VERIFIED | source/target/base/parents above; fetched immediately before merge |
| G02 Security | VERIFIED_WITH_LIMITATIONS | FINAL_SECURITY_REVIEW; fixture isolation, live 401 and authorized activation |
| G03 Current-head CI | VERIFIED_WITH_LIMITATIONS | run 40168878980; actual merge-candidate checkout, one missing-Tesseract skip |
| G04 Full regression | VERIFIED_WITH_LIMITATIONS | 195 PASS, 3 opt-in media SKIP |
| G05 UI smoke | VERIFIED | new explicit-URL browser, pre/post screenshots |
| G06 Three retrieval APIs | VERIFIED | live pre/post HTTP and generation/provenance assertions |
| G07 Provenance/SEC locator | VERIFIED_WITH_LIMITATIONS | source section/row/path matches; link opens whole filing, no highlight |
| G08 Mutation authorization | VERIFIED | missing 401, authorized isolated activate 200; default-deny tests |
| G09 Historical integrity | VERIFIED_WITH_LIMITATIONS | all six available owner historical file hashes unchanged |
| G10 Scientific freeze | VERIFIED_WITH_LIMITATIONS | pinned hashes, recomputed metrics, small/subset evaluation limits |
| G11 Integration candidate | VERIFIED | CI/local/final trees equal a2ed0487… |
| G12 Correct target merge | VERIFIED | 69e6866 normal merge, exact two parents |
| G13 Post-merge regression | VERIFIED_WITH_LIMITATIONS | full/core pass, opt-in media exclusions |
| G14 Acceptance record | VERIFIED | MILESTONE_C_OWNER_ACCEPTANCE.md and this report |
| G15 Main untouched | VERIFIED | ceaa8ac before/after |
| G16 No Milestone D code | VERIFIED | readiness note only |

## Remaining limitations

Pilot local scope only. No multi-node coordination, server TLS/key management, disaster-recovery/power-loss certification, broad SEC completeness, general answer accuracy or universal Hybrid superiority. Embedding/table representation and RRF overlap bias remain research issues. Older Qdrant storage requires separate backup/compatibility validation; no automatic migration was attempted. Acceptance record is a documentation-only follow-up to the exact tested merge commit above.
