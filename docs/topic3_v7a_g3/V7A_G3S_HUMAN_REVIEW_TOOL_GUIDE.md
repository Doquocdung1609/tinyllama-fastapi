# Local human review tool

The review interface is a small local application at `http://127.0.0.1:18747/`. It shows all 94 frozen questions with issuer/filing coverage, source hash and link, original SEC excerpt, both frozen Agent positions, candidate source locators, coordinator note and priority. It does not auto-approve. Browser smoke on this machine loaded the 94-question queue, filtered a Tesla unresolved case, opened its evidence and displayed the form; the real event count remained **0**.

Run from the repository root in PowerShell:

```powershell
python scripts/topic3_v7a_g3s_review_tool.py --dataset 'C:\Users\Admin\Downloads\V7A_G3S_PRIVATE_REVIEW_DATASET_20261102_V2.json' --events 'C:\Users\Admin\Downloads\V7A_G3S_HUMAN_REVIEW_EVENTS_20261102.jsonl' --html 'tools\g3s_review\index.html' --port 18747
```

The reviewer must enter their own ID/name, action, reason, evidence reference and explicit acknowledgement. Available actions are approve, reject, ambiguous, request correction and exclude; flagged wording requires an erratum ID for release. Each saved event has a UTC timestamp, evidence version SHA-256, prior-event hash and its own hash. The event log is append-only outside Git. Loading/filtering the UI writes no event. All 94 are currently pending. A synthetic fixture tested saving and tamper detection; it is not a human approval.

Preview a separately approved subset only after genuine review:

```powershell
python scripts/topic3_v7a_g3s_review_tool.py --dataset 'C:\Users\Admin\Downloads\V7A_G3S_PRIVATE_REVIEW_DATASET_20261102_V2.json' --events 'C:\Users\Admin\Downloads\V7A_G3S_HUMAN_REVIEW_EVENTS_20261102.jsonl' --export 'C:\Users\Admin\Downloads\V7A_G3S_REVIEW_PREVIEW.json'
```

The preview records pending, blocked, approved and excluded IDs and states that any partial subset is selected by review progress. It is not a final benchmark or exhaustive qrels. Keep the private dataset and any reviewer-identifying event file outside Git. The public [queue](V7A_G3S_HUMAN_ADJUDICATION_QUEUE.csv) contains only IDs, source mapping, AI decisions and blank human fields.
