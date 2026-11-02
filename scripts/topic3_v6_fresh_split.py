"""Register 30 untouched source-review questions without accessing rankings."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PILOT = ROOT / "docs/topic3_v5/recovery_live/holdout_30_review_queue.csv"
OUT = ROOT / "docs/topic3_v6/V6_FRESH_HOLDOUT_30_UNJUDGED.csv"

DESIGN = {
    ("AAPL", "2024"): [
        "Locate Apple's total net sales in the fiscal 2024 annual filing.",
        "What capital expenditures did Apple disclose for FY2024?",
        "Locate Apple's FY2023 and FY2024 net sales columns in the FY2024 filing.",
        "What research and development expense did Apple report for FY2024?",
        "What net cash from operating activities did Apple report for FY2024?",
    ],
    ("AAPL", "2025"): [
        "What were Apple's FY2025 total net sales?",
        "Locate Apple's capital expenditures for FY2025.",
        "Compare Apple's FY2024 and FY2025 total net sales in the FY2025 filing.",
        "What gross margin did Apple report for FY2025?",
        "What were Apple's FY2025 total liabilities?",
    ],
    ("MSFT", "2024"): [
        "Locate Microsoft's total revenue for FY2024 in the FY2024 filing.",
        "What capital expenditures did Microsoft disclose for FY2024?",
        "Compare Microsoft's total revenue columns for FY2023 and FY2024.",
        "What income tax expense did Microsoft report for FY2024?",
        "What were Microsoft's FY2024 total current assets?",
    ],
    ("MSFT", "2025"): [
        "What total revenue did Microsoft report for FY2025?",
        "What were Microsoft's FY2025 capital expenditures?",
        "Compare Microsoft's total revenue for FY2024 with FY2025 in its FY2025 filing.",
        "What research and development expense did Microsoft report for FY2025?",
        "What total assets did Microsoft report at FY2025 year end?",
    ],
    ("NVDA", "2024"): [
        "Locate NVIDIA's total revenue for FY2024 in the annual report.",
        "What capital expenditures did NVIDIA disclose for FY2024?",
        "Compare NVIDIA's FY2023 and FY2024 total revenue columns.",
        "What research and development expense did NVIDIA report for FY2024?",
        "What net income did NVIDIA report for FY2024?",
    ],
    ("NVDA", "2025"): [
        "What total revenue did NVIDIA report for FY2025?",
        "Locate NVIDIA's capital expenditures for FY2025.",
        "Compare NVIDIA's total revenue for FY2024 and FY2025 in its FY2025 filing.",
        "What gross profit did NVIDIA report for FY2025?",
        "What net income did NVIDIA report for FY2025?",
    ],
}


def main():
    pilot = list(csv.DictReader(PILOT.open(encoding="utf-8", newline="")))
    sources = {(r["source_ticker"], r["sec_report_date"][:4]): r for r in pilot}
    overlap = {r["question"].casefold().strip() for r in pilot}
    output = []
    for key, questions in DESIGN.items():
        source = sources[key]
        for question in questions:
            if question.casefold().strip() in overlap:
                raise ValueError(f"Pilot overlap: {question}")
            output.append({"question_id": f"V6_H{len(output)+1:03}", "question": question,
                           "source_ticker": key[0], "source_accession": source["source_accession"],
                           "source_url": source["source_url"], "sec_report_date": source["sec_report_date"],
                           "label": "UNJUDGED", "adjudicator": "", "source_span": "",
                           "period_column": "", "value": "", "unit": "",
                           "review_decision": "PENDING_HUMAN_SOURCE_REVIEW"})
    assert len(output) == 30 and len({x["question"] for x in output}) == 30
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(output[0]))
        writer.writeheader()
        writer.writerows(output)
    manifest = {"status": "SEALED_DESIGN_UNJUDGED_NO_RANKING_RUN", "questions": 30,
                "source_filings": 6, "issuers": ["AAPL", "MSFT", "NVDA"],
                "sha256": hashlib.sha256(OUT.read_bytes()).hexdigest(),
                "policy": "No ranking or tuning against this split before independent source adjudication"}
    (OUT.parent / "V6_FRESH_HOLDOUT_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest))


if __name__ == "__main__":
    main()
