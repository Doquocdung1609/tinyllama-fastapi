# COMMANDER — FINANCIAL INTELLIGENCE STUDIO V7P FINAL END-TO-END COMPLETION

**AUTHORIZATION:** `V7P_FINAL_VERIFIED_FINANCIAL_CHATBOT_AND_PRODUCT_UX_COMPLETION_AUTHORIZED`

**EXECUTION MODE:** FULL AUDIT → ROOT-CAUSE REPAIR → VERIFIED FINANCIAL QA → METADATA AUTOMATION → SHARED EVIDENCE PIPELINE → UNIFIED CHATBOT → UX REDESIGN → REAL BROWSER TEST → REGRESSION → FINAL ACCEPTANCE

**PRIORITY:** Complete the existing product. Do not stop after a technical checkpoint, a plan, or additional unit tests.

**PRODUCT OBJECTIVE:** A usable financial intelligence assistant that can ingest financial documents, understand their context automatically, retrieve relevant evidence, verify financial values, perform deterministic calculations, answer conversational questions, and navigate to exact PDF/SEC sources.

**RESEARCH OBJECTIVE:** Preserve the existing reproducible FAITH-R scientific experiment, author baselines, frozen SEC corpus and independent benchmark without contamination.

---

# I. CONTINUE THE EXISTING PR #35

Repository:

https://github.com/Doquocdung1609/tinyllama-fastapi

Current Draft PR:

https://github.com/Doquocdung1609/tinyllama-fastapi/pull/35

Branch:

`codex/topic3-v7p-verified-financial-chatbot`

Verified checkpoint:

`539fe77f062c1facb64a9f41f7ef3d9ab98d4c91`

Base:

PR #34 — `codex/topic3-v7a-g2-sec47-question-freeze`

**MANDATORY: Continue PR #35, not a new independent implementation.**

Before editing:

1. Fetch latest PR #35 HEAD and compare against the checkpoint.
2. Inspect local worktree, including untracked and uncommitted files.
3. Preserve the user's earlier V6 demonstration changes.
4. Identify code already implemented in PR #35.
5. Read all `docs/topic3_v7p/` acceptance, source diagnostic and real HTTP response artifacts.
6. Inspect existing V3/V3R/V3R2/V3R3 search modules, source-unit verification, existing product APIs and React components.
7. Build a missing-features matrix from this work order.
8. Implement the missing functionality incrementally rather than overwriting working modules.

Do not reset, clean, discard, force-push or merge automatically.

The user explicitly wants the full V4–V7P application preserved and improved.

---

# II. VERIFIED CURRENT TECHNICAL STATUS

The previous PR #35 checkpoint achieved:

- Ingestion of the actual `NASDAQ_AAPL_2025.pdf`.
- PDF SHA-256:
  `3eb270b22acb7d8d8e9c32a43dc221dec3345f8e4bca02755fdbc1ee16c823de`
- 80 pages, 451 chunks, READY.
- Native PDF table reconstruction using word geometry.
- Source coordinates and table header candidates.
- Diagnostic recovery of Net income 112,010.
- Diagnostic recovery of Americas segment net sales 178,353.
- Diagnostic recovery of total net sales 416,161 and 391,035.
- Diagnostic Decimal growth result 6.43%.
- Proper abstention for FY2037.
- `QUERY_CONTEXT_CONFLICT` for a contradictory company.
- 748 Python tests, 10 frontend tests and successful CI.

**But P0 remains NOT_PASSED.**

The three real Apple API requests still return:

`SOURCE_EXCERPTS`

with no verified numeric answer because:

`NATIVE_CELLS_REQUIRE_CURRENCY_FISCAL_AND_METRIC_BINDING`

The source-cell adapter currently generates candidates, not automatically verified operands.

Frontend auto/advanced semantics, metadata automation, integrated chatbot and real browser acceptance remain incomplete.

These limitations must be resolved rather than merely rewritten in reports.

---

# III. NON-NEGOTIABLE PRODUCT REQUIREMENTS

Preserve:

- React + Vite + TypeScript frontend.
- FastAPI backend.
- Existing local PDF workspace.
- BM25, Dense and Hybrid retrieval.
- Existing V2/V3/V3R2/V3R3 financial search implementations.
- Qdrant integration.
- Existing Ollama integration.
- Vietnamese and English PDF support.
- Existing OCR and PDF Viewer.
- SEC document search.
- Existing source-bound numerical verification contracts.
- Original Research Lab and FAITH-R experiments.
- Windows Prebuilt startup.
- User data and indexed documents.

Do not replace the project with Streamlit.

Do not rebuild the application from scratch.

Do not add paid dependencies or paid model APIs.

Do not claim the SEC FAITH-R algorithm has been validated on arbitrary uploaded PDFs unless actually implemented and tested.

**Primary user experience: Upload PDF → Ask → Receive a verified source-grounded answer.**

---

# IV. PHASE P0 — COMPLETE THE FINANCIAL EVIDENCE ENGINE

## P0.1 — Finalize structured financial cell verification

Continue from:

`app/product/native_financial_tables.py`

Inspect and reuse:

- `app/product/source_units.py`
- `app/product/analysis.py`
- `app/product/financial_labels.py`
- `app/product/query_intent.py`
- `app/product/pdf_extract.py`
- `app/product/region_layout.py`
- Existing Search V3R table and evidence components.

Implement a reusable typed FinancialCellEvidence contract.

Required fields, when source-supported:

- Source document ID and SHA-256.
- Source type: PDF or SEC.
- Exact page/HTML locator.
- Financial statement or section.
- Table ID.
- Row label.
- Financial metric and definition.
- Column label.
- Fiscal period and period kind.
- Source value and Decimal normalization.
- Currency.
- Scale and unit.
- Consolidated, separate, segment or other scope.
- Source text and word geometry.
- Header coordinates.
- Value coordinates.
- Source retrieval references.
- Evidence verification status.
- Extraction method and confidence.
- Explicit unresolved fields.

Do not promote a candidate simply because its row text contains an expected keyword.

A cell becomes `CELL_VERIFIED` only when all fields required for the requested operation have trustworthy source support.

## P0.2 — Bind currency and units correctly

The current adapter marks currency UNKNOWN even when financial table units may be recoverable elsewhere in the same verified document.

Implement a strict but practical source-grounded binder.

Consider:

- Explicit USD / U.S. dollars statements.
- SEC source metadata where authoritative.
- Verified table or statement currency declarations.
- Table heading units, such as dollars in millions.
- Document-level currency where clearly applicable and not overridden.
- Symbol-to-currency mapping only when contextual source evidence supports it.

A standalone `$` is not sufficient proof of USD.

Do not silently infer USD from issuer nationality.

Separate:

- Currency.
- Display unit.
- Scale factor.
- Normalized currency amount.
- Original cell display.

Reject inconsistent currency evidence.

Do not allow a conversion unless an actual conversion rule and required source data are available.

## P0.3 — Bind fiscal period and comparative columns

For each source table, distinguish:

- Fiscal year.
- Fiscal quarter.
- Three-month period.
- Six-month period.
- Nine-month period.
- Year-to-date.
- As-of balance date.
- Filing date.
- Comparative prior-year columns.

Correctly match headers such as FY2025 and FY2024 to their corresponding values.

Do not confuse 2025 with a filing submitted in 2025.

Handle valid equivalent period representations without falsely reporting a conflict.

Do not assume that a financial flow metric is an as-of balance.

When a source does not establish a requested period, return `AMBIGUOUS_PERIOD`.

## P0.4 — Exact metric and accounting-scope verification

Identify the financial metric from the natural-language question.

Examples:

- Net income.
- Total net sales.
- Total assets.
- Segment revenue.
- Operating income.
- Gross profit.
- Capex.
- Net cash provided by operating activities.

Disambiguate consolidated totals from geographic/business segments and narrower subcomponents.

For scope verification, use the relevant statement/table heading and source lineage.

Do not accept a page-wide occurrence of “consolidated” as proof that an unrelated table is consolidated.

Do not equate “Net income” and “Net income attributable to common shareholders” automatically.

Do not equate total capital expenditure and purchases of PP&E automatically.

## P0.5 — Complete numerical operations

Implement or repair deterministic operations over verified operands:

- Extract a single value.
- Difference between two periods.
- Year-over-year growth.
- Growth percentage.
- Ratio.
- Sum of selected source cells.
- Maximum/minimum over a verified complete comparison set.
- Supported comparative analysis.

Use Decimal for financial arithmetic.

For segment ranking, verify the entire relevant set of segment rows. Exclude Total, subtotals and unrelated categories from maximum/minimum comparisons.

Each computed answer must preserve links to all contributing operands.

No LLM-derived arithmetic or financial values.

## P0.6 — Bridge recovered cells into the answer engine

The main implementation blocker is the gap between recovered source cells and `eligible_facts()` / `numeric_answer()`.

Create a trusted automatic-source verification path instead of requiring every valid native PDF table value to be manually approved.

The automatic verifier must:

1. Receive retrieval evidence and document context.
2. Recover or locate source cells.
3. Validate source document integrity.
4. Bind issuer, metric, period, scope, unit and value.
5. Reject ambiguity and contradictory evidence.
6. Produce verified typed operands.
7. Execute deterministic financial operation.
8. Return answer, formula and exact citations.

Manual reviewed facts remain supported as an independent evidence path.

Preserve the strict separation between source candidates, verified source cells and manually reviewed facts.

Do not insert auto-extracted values into the human-reviewed table or claim human approval.

## P0.7 — Mandatory real Apple acceptance tests

Test the real PDF through the actual application, not mocked answers.

**APPLE-01**

Question:

`What was Apple's net income in fiscal year 2025?`

Required result:

112,010 million USD.

Source:

Consolidated Statements of Operations, PDF page 32, FY2025 column.

**APPLE-02**

Question:

`Which geographic segment generated the highest net sales in fiscal year 2025, and how much did it generate?`

Required result:

Americas — 178,353 million USD.

Source:

Segment Operating Performance, PDF page 25, FY2025 column.

Verify the entire five-region comparison set.

**APPLE-03**

Question:

`Calculate Apple's year-over-year total net sales growth rate from fiscal 2024 to fiscal 2025. Show the calculation and round to two decimal places.`

Verified operands:

FY2025 = 416,161 million USD.

FY2024 = 391,035 million USD.

Result:

6.43%.

Include deterministic formula and citations for both values.

All three tests must pass through the real authenticated HTTP endpoint and the actual application evidence pipeline.

No preloaded reviewed facts.

No hardcoded Apple numeric rules in production.

No fake source verification.

A correct final number without correct source-cell evidence is a FAIL.

## P0.8 — Negative and generalization tests

Preserve reliable refusal for:

- Apple FY2037.
- Wrong company.
- Missing document.
- Wrong reporting scope.
- Conflicting user constraints.
- Missing or conflicting units.
- Ambiguous year headers.
- Incomplete table structures.
- OCR values with insufficient confidence.
- Metric-definition ambiguity.
- Unsupported derived calculations.
- A segment table with an incomplete comparison set.

Run at least one non-Apple source PDF case and document whether the same generic extraction works.

For unsupported layouts, return a fallback with a precise reason, the affected source fields, and a safe action for the user; never invent a number or silently downgrade verification.

## P0.9 — Close inherited numerical and configuration gaps

Audit and repair the older `review_fact` scope logic: a generic mention of "consolidated" elsewhere on a page must not validate a table with a different scope. Build a table/statement-bound evidence lineage for both auto-verified and manually reviewed facts, without retroactively claiming old manual facts were checked by the new policy. Apply a documented migration/compatibility strategy to existing reviewed facts.

Reconcile `AnalysisRequest` defaults (historically assets/EXTRACT/SEPARATE), parsed question intent and optional explicit user settings. An omitted setting means AUTO, never an implicit contradictory filter. If the user explicitly selects a company, period, statement scope or operation which contradicts the selected document or question, report `QUERY_CONTEXT_CONFLICT` with the field(s), before computation. Implement five-way/representative matrices covering: pure auto; explicit matching values; explicit conflicts; omission with document context; multiyear and company-scoped questions. Distinguish fiscal year, fiscal end date and filing date; do not invent exact fiscal dates.

Ensure the recovered native table path is generic and source-scoped: the same typed verifier works when the retrieved page is relevant but the precise cell is outside the first returned text chunk, while preventing unbounded page fishing and fake retrieval credit. Retain source hash, page and chunk linkages. Add normal/negative tests for header wrapping, percentages adjacent to currency values, false totals, parentheses, EPS/share-count units, duplicate labels, unverified currencies, conflicting footnotes and units, segment-set completeness, PDF bytes changed after indexing, and OCR-only unsupported data.

**P0 GATE:** APPLE-01/02/03 `SUPPORTED` with values, formula where applicable, verified exact cell(s), report period/statement, currency/scale and click-through source. Negative cases abstain or return specific conflicts. Real authenticated HTTP and untouched source PDF are mandatory. If this fails, do not mark the product complete.

---

# V. PHASE P1 — DOCUMENT LIBRARY, AUTO-METADATA AND TRUSTWORTHY UPLOAD UX

## P1.1 — Remove metadata entry as a prerequisite

Inspect `app/product/api.py`, PDF workspace metadata persistence and `frontend/src/Studio.tsx` Library flow. Default UI = **select/drop PDF and upload**; do not force issuer, fiscal year or document type fields. Preserve optional advanced manual correction for uncertain fields and the existing API's backwards compatibility.

Build a generic source-first metadata extraction pipeline for Vietnamese and English annual/quarterly reports, 10-K/10-Q, financial statements, prospectuses and generic documents. Collect candidates from filename (low trust), cover/title, report heading, fiscal-year disclosures, statement/date headers, SEC/filing identifiers where actually present, and existing document/corpus provenance. Produce `issuer`, `ticker` where known, `document_type`, `report_period`, period kind, fiscal end/date where supported, `reporting_scope`, `currency` only if source-supported, `confidence`, `source_page`, `source_snippet`, `method`, `status` and conflicts. Treat the entity/year in filename as a hint, not authoritative verification.

States: `AUTO_CONFIRMED`, `NEEDS_REVIEW`, `UNKNOWN`, `USER_CORRECTED`, and conflicting metadata. Missing metadata must not block ingestion/search; only block operations that logically require it. For ambiguous metadata, show a brief inline review panel, not a mandatory long form. User correction must persist as a separate auditable provenance layer, never rewrite document bytes or disguise manual edits as inferred source facts. Separate document-level metadata from statement-level financial units. Avoid misleading document-level USD propagation into VND tables.

## P1.2 — Make upload visibly successful

Show selected filename (full accessible name plus truncation tooltip), file size, file icon, Replace/Remove before submission, and immediate acknowledgement after selecting or dropping. Differentiate `SELECTED`, `UPLOADING`, `UPLOADED`, `PROCESSING`, `OCR`, `INDEXING`, `READY`, `FAILED`, `INTERRUPTED`, and `RETRY_QUEUED` using actual backend state, not cosmetic timers. Distinguish "file selected" from "uploaded" and "indexed/answerable". Display upload progress only if measured; where the API cannot measure intermediate bytes, use a stage-based indeterminate indicator, not fictitious 100%.

Handle duplicate SHA/document IDs, same filename with different bytes, malformed PDF, oversize file (> existing 20 MiB limit unless intentionally changed/tested), missing OCR, retry, network interruption, upload cancellation if supported and reload persistence. Never erase an existing index on failure. Make labels/error recovery understandable in Vietnamese. Provide drop-zone keyboard access, aria-live statuses, focus indicators and mobile-responsive states.

## P1.3 — Metadata-assisted context selection

After upload, select the new document in the assistant context (without unexpectedly including other issuers). Keep document selector clear: filename, recognized company and period, READY state and whether numerical verification is supported. Show source-backed filters only when relevant. Use the selected document's metadata in the API rather than requiring the user to retype issuer or period. Provide optional multi-document selection for comparisons, enforcing disambiguation and origin/source limits.

**P1 GATE:** Upload real Apple PDF with only file selection and zero manual metadata; visible name/status and automatic issuer/year/type (or honestly flagged uncertainty) survive refresh. A second real non-Apple/Vietnamese file is supported. Incorrect metadata never produces a silently confident financial answer.

---

# VI. PHASE P2 — ONE SHARED EVIDENCE SERVICE, AUTO-ROUTING AND ALGORITHM TRANSPARENCY

## P2.1 — Unify search and answer plumbing, not just labels

Audit `/studio/search`, `/studio/unified-search`, `/studio/analysis`, `/studio/sec/analysis`, PDF workspace, `frontend_api.py`, `assistant_answer.py`, Search V2/V3/V3R/V3R2/V3R3 and the separate SEC research/FAITH-R backend. Reuse the existing engines. Build a typed service boundary such as `EvidenceQuery → SourceResolver → RetrievalAdapter → CellVerifier → OperationPlanner/DecimalCalculator → AnswerComposer` with one traceable `EvidenceBundle` contract and capability-aware adapters for uploaded PDF and SEC. Prefer extracting shared logic without breaking endpoint compatibility. Do not replace retrieval or claim two algorithms are identical because the UI looks unified.

Each evidence item has source kind, document/filing ID, SHA/accession if applicable, retrieval generation, engine actually run, original rank/chunk/parent ID, page or HTML section, table/row/column/box when available, metric/period/scope/unit, evidence eligibility, reason/uncertainties and a stable viewer URL or locator. Prevent cross-issuer and cross-document leakage by default. If source=ALL, do not combine incomparable raw BM25 and cosine magnitudes; preserve adapter/source identities, rank-based fusion where used and an explicit cross-source policy. Do not let a source-verification lookup be counted as an additional retrieval success on the frozen benchmark.

## P2.2 — Implement a truthful AUTO profile

**User-facing default:** `Tự động (khuyến nghị)`, hybrid/search configuration chosen by backend capabilities and question, not fixed legacy baseline. For a new ordinary PDF workspace, choose the best actually READY/compatible verified production engine; V3R3 is usable only with matching derived generation/index/capabilities. Fall back through documented supported paths (e.g. V3 → V2 → baseline) only when appropriate, disclose the effective profile and degradation, and never silently fabricate a V3R3/FAITH-R run. If a profile depends on a prepared derived workspace, expose readiness/rebuild controls or a safe fallback rather than failing obscurely.

Route user queries based on intent and required evidence: document QA, numerical extract, period comparison, growth, segment ranking, multi-company research, or explanatory summary. Explicit user constraints override automatic choices only if consistent and supported. Clarify only truly ambiguous selection; otherwise answer with support/abstention. Keep exact version identifiers, retrieval trace and evidence verdict in an Advanced/Research explanation panel.

## P2.3 — Keep SEC FAITH-R distinct and scientifically honest

FAITH-R (Fiscal-validated Attribute & Table-aware Hybrid Retrieval) is the research improvement hypothesis for the frozen SEC corpus. Determine what code executes it, which experiments and indexes it is compatible with, and its actual readiness. Integrate it through a clean source-specific adapter **only where implemented, tested and reproducible**, not by renaming PDF Search V3R3 or V3. For arbitrary user-uploaded PDFs, expose the real product pipeline and its verification status. Label any FAITH-R-inspired architecture as inspired/experimental when not proven to reproduce the research model. Make the effective algorithm and reason visible under technical details. Do not change the frozen model/baselines solely to make product demo appear superior.

## P2.4 — API and data contracts

Implement a stable typed `AskRequest` and `AskResponse`/`EvidenceBundle` using either an additive `/studio/chat` endpoint or a backwards-compatible `/studio/analysis` extension. Keep existing consumers working. Example (adapt field names to existing schema; do not hardcode the example):

```json
{
  "question": "Calculate Apple's total net sales growth from FY2024 to FY2025",
  "source": "USER_UPLOADS",
  "document_ids": ["actual-document-id"],
  "search_profile": "auto",
  "conversation_id": "optional-session-id"
}
```

The response MUST distinguish `SUPPORTED` verified numeric answers, `SOURCE_EXCERPTS` text-only/unverified, `INSUFFICIENT_EVIDENCE`, `QUERY_CONTEXT_CONFLICT`, `AMBIGUOUS_PERIOD`, `UNSUPPORTED_OPERATION`, and source/index unavailable states as appropriate. Contain readable answer, decimal strings (not JS floats), display unit/currency, calculation/formula/operands, source verification status, exact citations, reason/warnings, effective profile, engine/adapter, source generation and latency breakdown. Do not expose private paths, credentials or internal arbitrary stack traces.

**P2 GATE:** assistant and search use the shared evidence service; the same verified source evidence references survive search → chat → numeric answer → viewer, and honest profile/capability traces prove what ran. Legacy API smoke tests stay green.

---

# VII. PHASE P3 — UNIFIED FINANCIAL CHATBOT: QUESTION, ANALYSIS, COMPANY RESEARCH

## P3.1 — A single primary chat, not three confusing products

Replace three parallel top-level experiences (**Hỏi đáp tài liệu**, **Phân tích số liệu**, **Nghiên cứu doanh nghiệp**) with ONE prominent **Trợ lý tài chính** chatbot. Preserve their valid capabilities as natural conversational intents/tools inside that chat. Do not simply hide broken features or delete the research/analysis backend.

Primary layout: document/source context bar; message thread; multiline question composer; send/retry/cancel control if supported; sample questions; status/working indicators; answer with direct source buttons; formula/operands for calculations; next-question follow-ups retaining verified context. Useful example prompts: “Apple đạt lợi nhuận ròng bao nhiêu FY2025?”, “Doanh thu năm 2025 tăng bao nhiêu so với 2024?”, “Khu vực nào có doanh thu cao nhất?”, “Tóm tắt các rủi ro chính với trích dẫn”, “So sánh biên lợi nhuận 2024–2025 nếu có đủ số liệu”. Natural English equivalent questions must work.

## P3.2 — Deterministic finance, disciplined language generation

Natural-language interpretation may use the installed local Ollama model as an optional helper for intent classification and fluent explanations, but must not invent numeric operands, units, source references, calculations or `SUPPORTED`. No paid API; graceful deterministic fallback when Ollama unavailable/VRAM insufficient. Explain verified numbers from the evidence bundle, never from the model's unconstrained memory. For open-text summarization/risks, every material factual claim must be grounded to accessible document passages; clearly distinguish excerpts from verified financial cells. Support evidence-specific refusal instead of hallucinations or bland generic answers.

Fix the current tendency to echo raw first retrieval snippets as a pseudo-answer. Structure concise, readable answers with supporting evidence and any limitations. When there are multiple qualified sources, reconcile period/scope/currency; where contradictory, present the discrepancy rather than silently choosing a number.

## P3.3 — Conversational context and source control

Context is session-scoped, bounded and not allowed to override a newer explicit question or document selection. Follow-ups like “Còn năm 2024?”, “Tốc độ tăng trưởng thì sao?” and “So sánh với năm trước” resolve referents only from an unambiguous prior verified context. Explicit source/issuer/period changes must invalidate stale candidates and calculations. Require explicit selection or a useful disambiguation if multiple documents/issuers match. Do not coerce unavailable data into a confident response.

Do not store sensitive uploaded content or model outputs in an unrelated shared research dataset. Show last-used source and active document in every chat, and allow reset without deleting PDFs. Limit history/resource use to suit a local Windows laptop.

## P3.4 — Company research as a sourced orchestration

Support research questions about company profile/financial trends/segments/risks where data exists. Compose transparent multi-step retrieval and grounded synthesis with source coverage and dates; never promise real-time market or SEC updates unless a verified live source is configured. Avoid turning the app into a trading adviser. Optional comparisons must name the issuer, document, fiscal year, metric definition and currency for each statement; do not compare non-comparable fiscal/accounting scopes as if equivalent. Retain original asynchronous research job as a secondary advanced feature where useful, but make the primary UX conversational.

**P3 GATE:** all three business intents work through the same chat with real documents; Apple-01/02/03 pass via this chat; an unsupported/misleading question visibly abstains; a follow-up maintains the correct issuer/period and citations; Ollama offline does not cause invented figures.

---

# VIII. PHASE P4 — PRODUCT UX / IA REDESIGN AND PDF SOURCE NAVIGATION

## P4.1 — Navigation and progressive disclosure

In `frontend/src/Studio.tsx`, `frontend/src/api.ts`, `frontend/src/studio.css` and related components, redesign around these plain-language destinations:

1. **Trợ lý tài chính** (default home/chat).
2. **Kho tài liệu** (upload, metadata, processing, list).
3. **Bằng chứng & Nguồn** (search/explore; optional if the result card already provides it).
4. **Research Lab** (scientific comparison, advanced algorithm controls).
5. **Cài đặt / Trạng thái hệ thống**.

This is a suggested information architecture, not a license to discard old routes or existing capability. Preserve URL/route compatibility and provide redirects/links when necessary. The goal is fewer competing top-level features, not fewer working capabilities.

Ordinary users should NOT have to choose BM25/Dense/Hybrid, six V2/V3 profiles, RRF k, issuer, period, analysis operation, accounting scope or separate/consolidated just to ask a plain question. In Basic mode show the question, active document(s), source type and optional simple filters. Advanced section reveals method/profile/top-k, manual constraint overrides, diagnostics with plain explanations and guards against mismatched configs. Research Lab is the legitimate location for controlled methodology comparisons and ablation settings.

## P4.2 — Make evidence understandable

Numeric answer card: conclusion first; then source unit and fiscal period; expand to verified operands and deterministic formula; clickable citations for each operand; verification badge/text with accurate semantics; transparent warnings. Text-only support must never be styled as fully verified quantitative proof. Display small evidence context before/after target line or cell rather than an unexplained huge text wall. For comparative answers, show a compact evidence table with source rows and periods.

## P4.3 — PDF and SEC navigation tests

Clicking a citation MUST open the actual same-source PDF at the correct 1-based page, with row/value/column header highlights where geometry is trustworthy, and a visible document title and page number. Handle rotation, zoom and coordinate transforms via existing PDF.js geometry helpers; ensure text-only fallback remains clear if precise box absent. Guard against 0-based vs 1-based confusion and display-page vs printed-form-page differences. SEC citations must navigate to the original authorized source URL and useful section/filing context where supported; no fabricated DOM coordinate. Preserve browser back navigation from viewer to the originating answer with source/scroll state.

## P4.4 — Usability, accessibility and visual coherence

Reuse current React/Vite/shadcn patterns rather than rewriting styling stack. Responsive desktop/tablet/mobile; visible focus states, labels, keyboard actions, loading and empty/error states; long filenames and bilingual/diacritic text; no inaccessible icon-only controls; consistent status terminology. Prevent UI crashes from absent optional fields or source generation. Avoid rendering raw debug JSON to nontechnical users. Keep the interface demo-ready and understandable in Vietnamese, while accepting both Vietnamese and English questions.

**P4 GATE:** an unfamiliar user can select PDF, see its name/stage, ask a question, inspect a formula, and click into the exact source without understanding search algorithms or filling redundant forms; tested in an actual browser, not merely by type-checking.

---

# IX. PHASE P5 — KEEP RESEARCH LAB AND SCIENTIFIC FROZEN EVALUATION INTACT

## P5.1 — Immutable scientific assets

Preserve PR #34 base, SEC-47 10-company immutable accession manifest, 8,670-product-corpus provenance vs the author's 8,609 chunks, frozen question design, G2/F10 sealed holdouts, all independent adjudication and human-approved gold protocols, accepted/rejected qrels, baselines and research algorithm configurations. Preserve exact Git object hashes before/after for frozen artifacts; list any legitimate changed research file explicitly and justify. Do NOT adapt G2/F10 answers or qrels to improve product answers, do not inspect sealed labels for product tuning, do not backfill ground truth from model predictions and do not claim human approval automatically.

## P5.2 — Reproducibility and boundaries

Research Lab must show the *actual* author baseline vs improved runs and methods only when outputs are available, including corpus/index generation, config, metrics, latency/compute and qualifications. Include R0 BM25, R1 Dense, R2 SPLADE (only if implemented), R3 BM25+Dense RRF, R4 Dense+SPLADE (if implemented), R5 three-way RRF (if implemented), R6 stage-2 reranking (actual model or accurately labelled heuristic), and corresponding FAITH-R improvements/ablation only where supported by executable evidence. Do not fabricate missing SPLADE, learned reranker, an independent held-out score, or statistical superiority. Show `NOT_RUN`, `NOT_IMPLEMENTED`, `NOT_ADJUDICATED` truthfully.

Preserve the scientific separation of retrieval quality, exact cell/attribute accuracy, verified QA accuracy, abstention, latency/RAM/indexing, and subjective UX. Product acceptance must not be substituted for independent research validation. A single Apple demo is not scientific proof of superiority. If the existing research validation is incomplete, report that explicitly and leave frozen gates intact.

**P5 GATE:** no frozen manifest/labels/hash mutation, no benchmark contamination, legacy research tests rerun, algorithm lineage readable and no unsupported superiority claim.

---

# X. PHASE P6 — PERFORMANCE, SECURITY, PERSISTENCE AND LOCAL DEPLOYMENT

1. **Resource safety:** preserve 20 MiB upload and bounded pages/table/OCR/search budgets unless revised with evidence. Local Windows 11 / GTX 1650 Ti 4 GB VRAM/limited RAM must run baseline features, with Ollama optional, no required cloud model or paid subscription. Avoid GPU overload and repeated model downloads; expose capability/readiness diagnostics.
2. **Task robustness:** concurrent upload/index/answer operations must not corrupt workspace or frozen research indexes. Use bounded queues, cancellation/retry semantics where supported, atomic metadata/index write patterns, idempotent hash handling and recoverable errors. Do not break offline/local mode.
3. **Access/security:** all private `/studio` document, chat, upload, search and source endpoints retain bearer-token checks; never embed token in frontend bundle, logs, file names, browser screenshots or PR artifacts. Validate PDF MIME/content/signatures, path safety, file size and user-scoped document IDs; prevent unauthorized source exposure and arbitrary filesystem/network reads.
4. **Source integrity:** source bytes immutable with SHA checks; derived metadata/version/generation tracked separately; no phantom auto-verification from OCR low confidence; no SQL injection or direct path concatenation in viewer; no blind untrusted source instruction execution.
5. **Persistence and compatibility:** after restart, uploaded document list, metadata corrections, readiness, indexes and reference links remain usable without destructive reindexing; when algorithm/index version changes, migrate or clearly require non-destructive re-preparation. Existing API/tests/startup scripts continue working.
6. **No-cost constraints:** use existing dependencies and open/free local components. Any new package requires license, Windows compatibility, disk/RAM impact and documented install/recovery. No paid SEC/LLM API. Refrain from unrequested live external finance/trading calls.

**P6 GATE:** startup, restart, upload, QA, browser and security smoke tests pass in documented Windows-compatible local procedure. Any environment-specific unavailable step is marked BLOCKED with reproducer, not PASS.

---

# XI. PHASE P7 — REAL VERIFICATION MATRIX, NOT REPORT-ONLY TESTING

## P7.1 — Backend tests

Add focused tests for metadata provenance/override, currency–scale, fiscal-binding, statement and segment scope, unique/comparative column selection, five-way AUTO/explicit setting combinations, verified operands, Decimal operations, retrieval-linked source hashes, missing/ambiguous cases, cross-document conflict, session follow-ups and privacy. Existing baseline 748 Python tests is a **checkpoint**, not a guaranteed new exact total; report actual collected/passed/skipped/fail counts per environment. Run full suite without weakening assertions, and identify pre-existing vs new failures.

## P7.2 — Actual HTTP integration

Use real FastAPI/Uvicorn with the existing auth token, a fresh isolated product workspace, real Apple PDF SHA and one separate non-Apple (prefer HPG/Vietnamese) document; actual embedding/vector engine where feasible. Save sanitized HTTP request/response JSON and source hashes, index generation, actual effective search profile and verification trace. Specifically repeat Apple-01/02/03 and negative FY2037, wrong issuer, wrong reporting scope, ambiguous unit and malformed/comparative-table examples. HTTP200 with `SOURCE_EXCERPTS` does NOT count as APPLE PASS.

## P7.3 — Frontend / browser E2E

Run build, TypeScript checks and full frontend tests. Run real Playwright/Chromium browser steps for authentication, drag/drop and file chooser, selected file name visible before upload, no mandatory metadata form, status transition/reload, automatic metadata and correction, normal chat, follow-up context, conflicting constraints, source citation → correct PDF page and actual cell highlight, alternate source SEC, Basic vs Advanced and Research Lab. Save screenshots **from the executed browser**, trace/videos on failure, and structured test result with environment/tool versions. Do not count an old screenshot or mocked browser state as current PR #35 acceptance.

## P7.4 — Regression / quality / observability

Verify no meaningful regression of existing search APIs, BM25/Dense/Hybrid, V3R3 verified-cell controls, OCR safeguards, Qdrant, optional Ollama, SEC research, document provenance and Windows launcher. Record bounded latency and peak RAM/disk for sample scenarios, distinguishing warm and cold where possible; no invented performance targets. Inspect error boundaries and fallback messaging. Provide exact commands and reproducible logs.

## P7.5 — Required acceptance matrix

| Gate | Real acceptance, NOT a mock | Result to record |
|---|---|---|
| A0 | APPLE-01 exact verified net income 112,010 million USD, FY2025, PDF p32 | PASS/FAIL/BLOCKED |
| A1 | APPLE-02 Americas 178,353 million USD, complete 5-region argmax, PDF p25 | PASS/FAIL/BLOCKED |
| A2 | APPLE-03 (416,161−391,035)/391,035 × 100 = 6.43%, source both operands | PASS/FAIL/BLOCKED |
| A3 | FY2037, wrong issuer, mixed periods, unknown currency/scope and source tamper refuse safely | PASS/FAIL/BLOCKED |
| A4 | PDF upload with no metadata entry, filename visible, actual status and persisted metadata | PASS/FAIL/BLOCKED |
| A5 | Generic non-Apple PDF case, no Apple-specific logic | PASS/FAIL/BLOCKED |
| A6 | Normal chat handles document QA, calculation, sourced company research and follow-ups | PASS/FAIL/BLOCKED |
| A7 | Search/chat/viewer share source IDs and open precise PDF/SEC evidence | PASS/FAIL/BLOCKED |
| A8 | AUTO chooses/labels actual engine; advanced modes retained and explainable | PASS/FAIL/BLOCKED |
| A9 | Browser E2E actually executed on current HEAD with capture | PASS/FAIL/BLOCKED |
| A10 | Python frontend/HTTP regressions and Windows/local compatibility | PASS/FAIL/BLOCKED |
| A11 | SEC-47/G2/F10 and human-approved research freeze unchanged | PASS/FAIL/BLOCKED |

Acceptance is **not** a majority vote. A0–A3 (financial truth), A4, A6–A9 and A11 are hard blockers for `V7P_PRODUCT_ACCEPTED`. A5 must be honestly evaluated; a constrained unsupported non-Apple layout can be documented as a capability limitation, but falsely reporting success is a blocker. Unavailable infrastructure can be BLOCKED with evidence, never a fabricated PASS. Do not announce `RESEARCH_COMPLETE` solely because product gates pass.

---

# XII. PHASE P8 — IMPLEMENTATION ORDER, CHANGES, DOCUMENTATION AND PR HANDOFF

## P8.1 — Order of operations

Start with a short worktree+HEAD audit and preservation/feature-gap matrix. Execute in dependency order, not arbitrary UI-first order:

- **Milestone M0:** verify latest PR #35 HEAD, current branch, uncommitted changes, upstream diffs, research freeze hashes; update gap matrix.
- **M1:** finish P0 typed source cell verification/Decimal bridge; real Apple 3/3 + negatives, complete five-way settings matrix; only then claim P0 PASS.
- **M2:** P1 auto-metadata, corrected PDF upload/file visibility, persisted status and duplicate handling.
- **M3:** P2 shared evidence service, honest capability/algorithm AUTO selector, normalized API response.
- **M4:** P3 one chatbot with three question intents, contextual follow-ups and local Ollama graceful fallback.
- **M5:** P4 UX simplification and exact PDF/SEC evidence navigation; no lost old routes.
- **M6:** P5/P6 research freeze, local security/performance and Windows stability.
- **M7:** P7 authenticated HTTP, real browser acceptance and regressions, then documentation and PR status.

If a later stage reveals a P0 issue, return to root-cause repair and rerun dependent gates; do not present cosmetic completion as final. Test incrementally after each milestone. A task list or one more partial checkpoint is not task completion.

## P8.2 — Expected code areas (inspect actual code before changing)

Backend: `app/product/native_financial_tables.py`, `analysis.py`, `assistant_answer.py`, `query_intent.py`, `financial_labels.py`, `source_units.py`, `pdf_extract.py`, `region_layout.py`, `workspace.py`, `api.py`, `frontend_api.py`, search adapter modules, and relevant research QA integration. Frontend: `frontend/src/Studio.tsx`, `api.ts`, `studio.css`, PDF viewer/geometry utilities, route/navigation and test files. Create focused new modules instead of one giant `Studio.tsx` or circular Python imports where maintainability requires. Keep versioned schemas and safe migrations.

## P8.3 — Required new evidence reports in `docs/topic3_v7p/`

- `V7P_FULL_GAP_AND_ROOT_CAUSE_MATRIX.md`: every old item and new request mapped to code, before/after behavior and proof.
- `V7P_FINANCIAL_CELL_BINDING_AND_ARITHMETIC.md`: exact source→header/row→unit/period→verified operand→Decimal answer chain.
- `V7P_UPLOAD_METADATA_UX_QA.md`: sources/precision, manual override, selected file UI, upload/restart screenshots.
- `V7P_SHARED_EVIDENCE_AND_ROUTING.md`: adapter interfaces, actual engine routing, PDF vs SEC vs FAITH-R scientific boundary, fallback truth table.
- `V7P_CHATBOT_END_TO_END_QA.md`: real questions in English/Vietnamese, source ID, follow-up, abstention, Ollama-on/off behavior.
- `V7P_BROWSER_E2E_EVIDENCE.md` and captured real screenshots/traces, avoiding secrets.
- `V7P_RESEARCH_FREEZE_HASH_AUDIT.md`: SEC-47, G2, F10, research/holdout integrity.
- `V7P_REGRESSION_PERFORMANCE_AND_SECURITY.md`: exact commands, passes/skips, local resources and issues.
- `V7P_FINAL_ACCEPTANCE.md`: gate table A0–A11, exact HEAD, conditional verdict and known limitations; do not overwrite historical evidence, link it.

Add sanitized machine-readable HTTP/chat/source evidence JSON and Playwright results. Avoid huge raw PDF/debug files and binary indexes in Git commits; retain reproducible source hash and location instructions instead. Keep docs concise but audit-ready.

## P8.4 — Git and status discipline

Continue **only existing PR #35** (`codex/topic3-v7p-verified-financial-chatbot`) unless a branch mismatch is proven; inspect before pushing. Commit coherent milestones with tests. Do not modify PR #34, merge PR #35, force push, stash/clean/reset another worktree, mutate old local owner data, or turn Draft into Ready without explicit authorization. Preserve uncommitted local work. Update the PR body/checkpoint with what was truly implemented and real gate evidence.

If any requirement is fundamentally blocked by missing source/file/tool environment, implement as much as safely possible, document exact blocker and reproduction, leave gate `BLOCKED` rather than claiming completion. Prioritize trustworthy end-to-end user functionality over adding superficial tests.

---

# XIII. FINAL DEFINITION OF DONE AND FINAL CODEX RESPONSE

The task is complete only if: a person on the existing React app can upload a real financial PDF **without metadata busywork**, clearly see filename and processing, use **one chatbot** to ask ordinary questions, get **source-grounded and correctly verified** values/formulas (including Apple 3/3), click through to exact PDF/SEC evidence, and optionally enter Research Lab to inspect the **actual** baseline/improvement configurations and independent-evaluation state — without changing any frozen research/holdout data.

The final Codex response MUST include:

1. Exact repository, branch, PR URL, starting HEAD and ending HEAD, list of commits changed.
2. Summary per M0–M7 of what changed (file paths, API contracts, UI behavior) and remaining work, with no generic `done` claims.
3. A0–A11 acceptance table with PASS/FAIL/BLOCKED, actual Apple three outputs and source-cell proof, negative results and non-Apple generalization outcome.
4. Exact test commands and results (Python, frontend, HTTP, Playwright/browser), screenshots and sanitized evidence artifact paths; environment/tool versions and limitations.
5. Actual runtime `AUTO` selection and distinct SEC FAITH-R vs uploaded PDF algorithm path; no research superiority claim without locked, independent validation.
6. Frozen-manifest/benchmark integrity verification and whether human adjudication is still pending.
7. One concise Windows local run guide: clone/checkout PR branch, dependencies, env/token, backend+frontend startup, PDF upload and test questions. Never include real tokens in logs.
8. Honest verdict: `V7P_PRODUCT_ACCEPTED` **only when hard gates pass**, else `V7P_NOT_ACCEPTED` with the precise blockers. `RESEARCH_COMPLETE` requires its own independent scientific acceptance and must not be inferred from V7P.

**EXECUTE THE WORK. This is an implementation and independent verification work order, not a request to propose another plan. Correct the gaps left by the previous Codex session, keep the existing project and all user work, and do not stop at source diagnostics or a screenshot-only demo.**