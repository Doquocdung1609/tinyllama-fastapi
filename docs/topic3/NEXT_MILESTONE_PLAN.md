# Topic 3 — Exact proposal for Milestone B

Milestone B must build the reproducible financial corpus and metadata layer. It
must not prematurely add reranking, multi-agent QA, or tune retrieval on the
future holdout.

## Proposed scope

1. Define a filing identity model:
   - issuer legal name and ticker,
   - CIK,
   - form type (`10-K`, `10-Q`, amendment),
   - fiscal year and fiscal period,
   - filed/accepted timestamps,
   - accession number,
   - canonical SEC source URL,
   - raw-byte SHA-256, normalized-content SHA-256 and pipeline version.
2. Implement a local SEC EDGAR client:
   - required descriptive User-Agent from configuration,
   - bounded request rate and retry/backoff,
   - conditional/idempotent downloads,
   - acquisition log with status, source URL, timestamp and error,
   - no paid API and no automated large model download.
3. Preserve immutable raw source artifacts and a versioned manifest.
4. Parse a deliberately small English pilot corpus of real 10-K/10-Q filings.
5. Link every text/table chunk to filing identity and source location available
   from HTML/XBRL/PDF; never invent page/bbox values when absent.
6. Detect exact duplicates, amendments, and revised filings without merging
   materially different versions.
7. Add idempotent resume/restart behavior and dry-run deletion/repair reports.
8. Produce corpus statistics and error logs, but no retrieval winner claim.

## Suggested pilot design

- Select several issuers from different sectors and at least two periods per
  issuer so metadata filters and cross-period questions are possible.
- Include 10-K and 10-Q, plus at least one amendment if legally/reliably
  obtainable.
- Freeze a development snapshot manifest before Milestone C.
- Reserve different issuers/filings for the later holdout; do not inspect their
  questions while tuning.

The exact issuer list and acquisition dates should be recorded at execution
time because EDGAR availability is time-dependent.

## Automated tests required

- SEC request headers, throttling, retries and backoff using a local fake server.
- Accession/CIK/form/period parsing from saved real response fixtures.
- Raw and normalized hash stability.
- Same file, renamed file, metadata-only PDF change and genuine revision.
- Interrupted download and interrupted parse recovery.
- Idempotent rerun producing no duplicate document/chunk/vector identities.
- Provenance round trip from result chunk to raw source URL/location.
- Malformed filing, missing table, unavailable source and partial parse logging.

## Deliverables proposed

- `docs/topic3/DATASET_AND_PROVENANCE.md`
- Versioned corpus manifest schema and example generated manifest.
- SEC acquisition/ingestion modules with configuration and tests.
- Corpus build report with actual counts, bytes, timings, failures and hashes.
- Development/holdout partition manifest without answer labels in runtime code.

## Milestone B exit gates

- Every indexed filing has a stable accession-based identity and raw hash.
- Re-running ingestion is idempotent.
- Every chunk can be traced to a filing and source location.
- Metadata fields required by retrieval filters are present and validated.
- Download behavior complies with configured SEC fair-access controls.
- Failures are recoverable and reported without silent data loss.
- No production data is destructively migrated without a reviewed dry run.

Milestone C should start only after these gates pass and the corpus snapshot is
frozen. Explicit user authorization is required before beginning Milestone B.
