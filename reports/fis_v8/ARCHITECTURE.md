# V8 product architecture

1. **Select.** The authenticated catalog and the actual request’s filing IDs bound the query. The resolver uses catalog company names, tickers and known aliases. One named company is scoped inside a mixed selection. An unnamed multi-company request that cannot be bound asks for clarification.
2. **Retrieve.** Numeric QA projects financial rows from signed canonical parent IDs. An exact label and supported iXBRL concept must agree. Search preserves signed navigation IDs and shows readable text. Narrative QA filters tables and hidden resources, ranks actual risk or management disclosure and quotes a bounded source sentence.
3. **Verify.** The product reader rehashes the HTML, checks the indexed source and parses the original cell, context, visible header, currency and scale. The product adapter supports declared thousands, millions and billions of USD. It keeps per-cell duration and dimensions and uses Decimal with independent recomputation.
4. **Compose.** Different durations at the same end date are listed separately. Cross-period change uses comparable operands. The orchestrator returns individual supported or blocked tasks. Operating and gross margins require independently bound operands with the same filing, period and scope.
5. **Publish.** The product worker publishes BM25 before Dense and records real progress. Explicit Dense requests skip unavailable partitions and report which filing is pending. A lexical-only filing remains usable for Search and Chat.
6. **Recover.** The parent supervises the worker using durable event/receipt times. A stale child is bounded to the worker owned by this API. A restart reconciles the interrupted job to the published state and retries from the existing snapshot.

## Limits

Coverage is bounded by supported labels and iXBRL layouts. Arbitrary segments, custom issuer extension taxonomies, financial observations without visible unit proof, arbitrary cross-issuer metric-to-clause binding and document-wide synthesis remain incomplete. The risk route provides grounded extracts or a clear material-change summary. It does not promise exhaustive coverage of each filing section. The Dense watchdog recovery includes a simulated interruption, separate from the observed successful live Dense run in the second workspace.

## Replay and rollback

Run the application using the existing local launcher and the matching workspace. Set `FIS_V8_URL`, `FIS_V8_HOLDOUT_URL`, and optionally `FIS_V8_SKIP_HOLDOUT=1` before running `node scripts/fis_v8_browser.cjs`. The script reads the existing local API token without printing it. Holdout imports were run in an isolated product workspace with lexical-only indexing. Roll back by reverting the V8 code commit and rebuilding the frontend. Both published source generations remain separately auditable.
