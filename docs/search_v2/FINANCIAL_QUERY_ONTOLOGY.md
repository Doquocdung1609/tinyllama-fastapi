# Financial query ontology / source scope

`app/product/query_intent.py` is an extensible issuer-independent dictionary and deterministic parser. It contains no company-specific answer, document/page routing rule or financial figure. Normalization uses NFC source text and accent-folded retrieval text including đ→d. Longest concepts consume nested aliases, avoiding fixed vs intangible assets and total vs other liabilities.

| Field | Behavior |
|---|---|
| Entity | Dynamic issuer alias and first filename identifier, intersected with explicit selected document IDs. Unknown names/tickers request clarification rather than certifying another issuer. Ambiguous aliases remain a limitation; no universal company NER claim. |
| Metric | Controlled multilingual phrases; no universal OR→AND substitution. Terms and aliases go into fielded FTS with quoted phrases. |
| Period | Explicit calendar dates/years; calendar year end/beginning phrases resolve to date requests, never invented source headers. Generic multiple source periods cannot create a single verified answer. Fiscal-year/quarter language beyond explicit dates is limited. |
| Scope | Separate/company-parent vs consolidated from source title region; manually entered upload type is not proof. Conflicting or mixed scopes request clarification. |
| Basis | Original vs adjustment vs restated are distinct. Source reviewed facts bind to a particular column. No unspecified basis silently picks restated. |
| Statement | Expected or explicitly requested statement family, plus a lightweight source-title classifier for balance/income/cash-flow/notes. Unknown titles remain UNKNOWN; no claim of a full image-semantic layout classifier. |
| Unit | VND scales/USD/% recognized; only actual reviewed source units can qualify. No automatic FX or guessed scaling. |
| Operation | Lookup/change/growth/ratio/accounting identity describe retrieval needs. Search does not replace the separate Decimal service. |
| Evidence | Related passage, matched unverified row and reviewed answer evidence are separate. Reviewed status requires query-compatible current audited source cells. |

- `assets` (BALANCE_SHEET): tổng tài sản; tổng cộng tài sản; quy mô tài sản; toàn bộ tài sản; total assets
- `fixed_assets` (BALANCE_SHEET): tài sản cố định; fixed assets; property plant and equipment
- `intangible_assets` (BALANCE_SHEET): tài sản cố định vô hình; tài sản vô hình; intangible assets
- `current_assets` (BALANCE_SHEET): tài sản ngắn hạn; current assets
- `noncurrent_assets` (BALANCE_SHEET): tài sản dài hạn; noncurrent assets; non-current assets
- `cash_equivalents` (BALANCE_SHEET): tiền và các khoản tương đương tiền; tiền và tương đương tiền; cash and cash equivalents
- `cash_balance` (BALANCE_SHEET): số dư tiền; cash balance
- `liabilities` (BALANCE_SHEET): nợ phải trả; total liabilities
- `current_liabilities` (BALANCE_SHEET): nợ ngắn hạn; current liabilities
- `noncurrent_liabilities` (BALANCE_SHEET): nợ dài hạn; noncurrent liabilities
- `other_liabilities` (BALANCE_SHEET): nợ phải trả khác; other liabilities
- `other_noncurrent_assets` (BALANCE_SHEET): tài sản dài hạn khác; other noncurrent assets
- `equity` (BALANCE_SHEET): vốn chủ sở hữu; shareholders equity; stockholders equity
- `total_funding` (BALANCE_SHEET): tổng nguồn vốn; tổng cộng nguồn vốn; liabilities and equity
- `inventory` (BALANCE_SHEET): hàng tồn kho; hàng kho tồn; inventories; inventory
- `investment_property` (BALANCE_SHEET): bất động sản đầu tư; investment property
- `net_revenue` (INCOME_STATEMENT): doanh thu thuần; doanh thu bán hàng thuần; net sales; net revenue
- `financial_revenue` (INCOME_STATEMENT): doanh thu hoạt động tài chính; doanh thu tài chính; financial income
- `pretax_income` (INCOME_STATEMENT): lợi nhuận kế toán trước thuế; lợi nhuận trước thuế; profit before tax
- `net_income` (INCOME_STATEMENT): lợi nhuận sau thuế; lãi sau thuế; net income; profit after tax
- `operating_cashflow` (CASH_FLOW): lưu chuyển tiền thuần từ hoạt động kinh doanh; dòng tiền từ hoạt động kinh doanh; tiền từ hoạt động kinh doanh; operating cash flow; operating cash
- `net_cashflow` (CASH_FLOW): lưu chuyển tiền thuần trong kỳ; dòng tiền thuần trong kỳ; net cash flow

Examples are regression inputs, not production routing: total assets ≠ fixed assets; cash equivalents ≠ cash balance; net revenue ≠ financial revenue; after-tax ≠ pretax profit; cash flow ≠ cash balance; liabilities ≠ total funding; original ≠ restated. Narrative questions cannot inherit reviewed numbers merely because a row was retrieved.

Original run bytes (including superseded diagnostics and first test) are retained in MEASURED_RUN_SNAPSHOTS.zip; per-entry hashes are in its manifest. Final result JSON files use one record per line without changing any measured values.
