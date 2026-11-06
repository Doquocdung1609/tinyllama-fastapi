# SEC question plan

`sec_task_plan.py` builds an auditable `SecQuestionPlan` before any financial values are read. It records the original question, actual selected filing IDs, named/context/focused/comparison/excluded/unselected/eligible issuers, an intent and an explicit task list. Each `SecTask` carries issuer, metric, operation, date, duration, form, accession, scope, currency and required output fields. All task filing IDs come from the selected catalog.

The resolver executes only eligible tasks. A focused issuer missing from selection is rejected. A comparison may finish present issuers while exposing the missing issuer. Numeric tasks bind independently verified source cells. Margin tasks require numerator and denominator to match CIK, filing, start/end dates, scope and unit; `Decimal` computes the percentage. Narrative tasks bind a separate cited excerpt for each requested topic. `answer_completeness` exposes `completed/required` even for partial responses.

Limitations: the planner is rule based and its financial vocabulary is bounded; a new paraphrase can still be missed. Multiple filings for the same issuer with different report dates currently require an explicit choice. A short followup can carry a prior 13-week request to a company with no 13-week cell, in which case it abstains and names the missing operands. These are visible limitations, not silent success.
