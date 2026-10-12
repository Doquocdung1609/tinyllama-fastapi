# GenAI Learning Studio quality hardening — final report

## Decision: PARTIAL

The critical C05/C09 failures are repaired and verified through real FastAPI calls. The production P0 classification regression, persistent conversations, numerical calculations, source citations, Qdrant data and Tiny-SD remain functional. Overall acceptance stays PARTIAL because Vietnamese scanned-table prose CER did not improve, three chart geometry classes remain partial, one new real-PDF structural caption case fails, and no external sealed holdout was provided.

## Verified baseline and safety

- Baseline commit: `1124fba1304c4b8a8f7e610d69043160164ab6bb`; implementation commit: `bb079938b3e9d41e7a1b33d6bc414dae67192f53`.
- Recoverable checkpoint: `checkpoints/quality-hardening-20261012-102242`.
- Production Qdrant before/after: 1,947 vectors; no destructive writes.
- Production SQLite: consistent backup captured; no production conversations were deleted.
- Full suite: **62 passed, 3 skipped**.
- Live health: FastAPI 200, Streamlit 200, Ollama ready, embeddings ready, Qdrant online.
- Browser reload: heading `GenAI Learning Studio` and all **8** navigation items visible after an actual reload; blank-page regression was not reproduced.

## C05 before and after

**Before:** page inventory returned unsupported information. The follow-up selected `table:p1:t2` but described 100/125 and cited `table:p1:t1`. The old evaluator marked this as a pass based only on selected evidence.

**After:** inventory reports two tables and one chart. The follow-up returns: “Bảng 2 trình bày Dòng tiền… Kinh doanh — 2023: 20, 2024: 28. Đơn vị: bảng không ghi rõ đơn vị,” citing only `table:p1:t2`. Structural tests: **3/3 PASS**, including missing-table handling. Real latency: 26–138 ms for deterministic structural paths.

## C09 before and after

**Before:** “Lợi nhuận năm 2024 là 15 triệu đồng đúng không?” returned insufficient information without a citation.

**After:** direct and correction turns both return: “Không đúng… lợi nhuận … năm 2024 là 16 triệu đồng,” with `verification_status=CONTRADICTED`, source cell `{metric=Lợi nhuận, year=2024, value=16}` and exact table citation. Four-way real API cases all pass:

- CONFIRMED: correct value 16.
- CONTRADICTED: claimed 15 versus source 16.
- INSUFFICIENT_EVIDENCE: no value supplied.
- AMBIGUOUS: multiple periods with no year specified.

## Strict evaluator results

- Original persistent workflows: **12/12 PASS**.
- Four added verification statuses: **4/4 PASS**.
- Combined `conversational_assertion_tests.csv`: **16/16 strict PASS**.
- Every row separates context resolution, extraction, prompt evidence, answer correctness, completeness, numerical correctness, citation support and refusal behavior.
- Existing P0 regression: 4/4 answers, Recall@8 100%, evidence-in-prompt 100%, supported citation accuracy 100%, refusal recall 100%.
- Legacy five-case regression still records the prior R01 citation-window disagreement instead of silently upgrading it.

## OCR experiments

Nine controlled configurations used the identical Vietnamese scanned financial table image at 300 DPI.

| Result | Baseline | Best measured |
|---|---:|---:|
| CER | 15.85% | 15.85% |
| WER | 58.14% | 58.14% |
| Header tokens | 4/4 | 4/4 |
| Critical numeric cells | 6/6 | 6/6 |
| Row alignment | 3/3 | 3/3 |

Deskew, contrast, adaptive threshold, line removal, region/row OCR, PSM changes and Vietnamese-only OCR did not reduce CER; several were worse and Vietnamese-only OCR damaged numeric cells. The production configuration was retained. Original and measured outputs are in `ocr_table_before_after.csv`. No textual correction was applied to financial numbers.

Existing broader fixtures still cover clean Vietnamese, Vietnamese/English scanned tables and an image-only chart. The fresh holdout adds bilingual, rotated and low-contrast scanning. Borderless/mixed native pages were also exercised, though their layout remained text-only rather than reconstructed tables.

## Chart hard cases

`chart_hard_cases.csv`: **9 PASS, 3 PARTIAL, 0 FAIL**.

Supported with exact readable labels: single/multiple-series bar, line endpoints, pie maximum, dual-axis refusal, and diagram-versus-chart classification. Remaining limitations:

- Crossing lines: endpoint trends are correct; the crossing coordinate is not inferred from geometry.
- Scatter: labeled point lookup only; correlation and unlabeled coordinates are unsupported.
- Stacked bars: exact labeled segments only; unlabeled stack geometry is unsupported.
- Image-only charts without readable numeric labels return a qualified limitation.
- Flowcharts, organizational graphs and network diagrams are never treated as numerical charts.

## Duplicate audit

The two 971-point production lecture records share both the exact byte SHA-256 and extracted-text fingerprint. This confirms exact duplicates. Current exact-byte uploads reuse the existing document ID and leave vector count unchanged. A dry-run estimates 971 removable duplicate points, but no deletion was performed because old document IDs may be referenced outside local SQLite.

## Generalization

- Newly selected real 10-page CO₂–FDI report: **3/4 strict PASS**. Facts about 19 countries/2000–2022, the FGLS coefficient 0.154 at 1%, and an out-of-document refusal pass with correct pages. REAL03 fails because page inventory identifies “Bảng 1” on page 3 but extracts the caption as “Nhóm” instead of “Cấu trúc mẫu theo nhóm thu nhập”.
- Fresh synthetic `INTERNAL_HOLDOUT`: **4/4 PASS** across a borderless bilingual table, two-company report, mixed table/chart page and rotated low-contrast scan. These cases were not used to change application code.
- No professor-owned or externally sealed holdout was supplied; no independent certification is claimed.

## Acceptance gates

| Gate | Status | Evidence |
|---|---|---|
| G1 production P0 regression | PASS | 4/4, real inference |
| G2 12 persistent workflows | PASS | 12/12 strict |
| G3 useful C05 explanation | PASS | exact table, values, unit status, citation |
| G4 four-way verification | PASS | 4/4 real API |
| G5 OCR accuracy | PARTIAL | numeric cells exact; table prose CER 15.85% |
| G6 calculations/units/formulas | PASS | full suite and deterministic validations |
| G7 chart claims match capability | PASS | safeguards active; 3 classes documented PARTIAL |
| G8 citations support claims | PASS for new strict suites | legacy R01 disagreement retained |
| G9 production data intact | PASS | 1,947 vectors; SQLite backup |
| G10 unrelated PDF generalization | PARTIAL | real 3/4; internal holdout 4/4 |

## Changed implementation and regression risks

| File | Reason and affected behavior | Failing evidence → passing evidence | Material risk |
|---|---|---|---|
| `app/services/calculation_service.py` | Four-way financial claim verification, both table orientations, chart axis/unit guards | C09 refusal → direct/correction CONTRADICTED; chart dual-axis test | Unusual merged headers may remain ambiguous |
| `app/services/conversation_service.py` | Preserve prior hypothesis in correction turns | correction lost 15 → retained hypothesis and verified source | Very long prior questions enlarge resolved query, still bounded by history |
| `app/services/rag_service.py` | Structural navigation and retrieval-only claim sanitization | C05 wrong table → exact metadata path; false numeric guard → source retrieval | Caption quality depends on extraction metadata |
| `scripts/conversation_api_benchmark.py` | Strict claim-level evaluator | false C05/C09 PASS rules → all mandatory dimensions | Hand-maintained gold annotations still require review |
| `tests/test_quality_hardening.py` / `tests/test_conversations.py` | Regression coverage for layouts, statuses, charts and follow-ups | confirmed failures reproduced → 62 passed, 3 skipped | Synthetic fixtures do not cover every PDF producer |
| OCR/chart/holdout scripts | Reproducible controlled evaluation | earlier aggregate claims → per-configuration/per-class rows | Runtime varies with local load |

## Unresolved items

1. REAL03 caption completeness: page/table count and citation are correct, full caption is not.
2. Vietnamese scanned-table prose: CER 15.85%, WER 58.14%; numeric cells remain exact on the verified clean fixture.
3. Exact geometry for unlabeled crossing lines, scatter plots and stacked bars.
4. No external sealed holdout.
5. Resource headroom: 0.74 GB RAM and 8.55 GB disk free in the final snapshot.

No hardcoded answer, page ID or query-specific exception was added. Qwen, nomic embeddings, Tiny-SD, audio/media features, production Qdrant and persistent SQLite remain in place.
