# E2E test matrix

24 requested scenarios are planned in test_matrix.json. Actual HTTP and browser workflow NOT_TESTED at this checkpoint. Unit/in-process tests will never be relabeled live UI. Synthetic and public-source runs require separate source identities/results.

## D5 observed v2

The prior line describes the initial checkpoint. The completed [24-scenario ledger](D5_E2E_VALIDATION_REPORT.md) now distinguishes LIVE_HTTP, LIVE_UI, FIXTURE, PARTIAL and NOT_TESTED. There were 21 actual Uvicorn HTTP calls and new-browser Streamlit observations in synthetic and official SEC modes. Scenario 21 live concurrent query/publication remains NOT_TESTED. Official link presence was observed, but navigation landing after click was not confirmed. The [machine matrix](test_matrix.json) has an appended v1 outcome event; its initial `live_ui` and `real_http` fields are historical initial-state fields.
