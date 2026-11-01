"""Create a sealed, source-linked UNJUDGED review queue; never infer gold."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import zipfile
from pathlib import Path

from topic3_v5r_restore import REPO, SOURCE


# These are question proposals, not answers or labels. No values are supplied.
DESIGN = [
    ("AAPL", 2024, "What were Apple's FY2024 net sales?", "EXACT_CELL"),
    ("AAPL", 2024, "What cash and cash equivalents did Apple report at FY2024 year end?", "BALANCE_SHEET"),
    ("AAPL", 2024, "What was Apple's FY2024 operating income?", "EXACT_CELL"),
    ("AAPL", 2024, "How did Apple's net sales change from FY2023 to FY2024?", "COMPARATIVE_COLUMN"),
    ("AAPL", 2025, "What were Apple's total assets at the FY2025 reporting date?", "BALANCE_SHEET"),
    ("AAPL", 2024, "How did iPhone sales compare with Apple's total net sales in FY2024?", "TOTAL_VS_COMPONENT"),
    ("MSFT", 2024, "What was Microsoft's FY2024 total revenue?", "EXACT_CELL"),
    ("MSFT", 2024, "What was Microsoft's operating income in FY2024?", "EXACT_CELL"),
    ("MSFT", 2024, "What research and development expense did Microsoft report for FY2024?", "METRIC_DISAMBIGUATION"),
    ("MSFT", 2025, "What cash and cash equivalents did Microsoft report at FY2025 year end?", "BALANCE_SHEET"),
    ("MSFT", 2025, "Compare Microsoft's net income in FY2024 and FY2025.", "COMPARATIVE_COLUMN"),
    ("MSFT", 2025, "What will Microsoft's net income be in FY2037?", "UNSUPPORTED_FUTURE"),
    ("NVDA", 2024, "What total revenue did NVIDIA report for FY2024?", "EXACT_CELL"),
    ("NVDA", 2024, "How much FY2024 NVIDIA revenue came from data center operations?", "SEGMENT_VS_TOTAL"),
    ("NVDA", 2024, "What was NVIDIA's FY2024 operating income?", "EXACT_CELL"),
    ("NVDA", 2025, "Compare NVIDIA's total revenue between FY2024 and FY2025.", "COMPARATIVE_COLUMN"),
    ("NVDA", 2025, "What was NVIDIA's FY2025 net cash from operating activities?", "CASH_FLOW"),
    ("AMZN", 2024, "How did Amazon's FY2024 net product sales differ from total net sales?", "TOTAL_VS_COMPONENT"),
    ("AMZN", 2024, "What were Amazon's total operating expenses in FY2024?", "EXACT_CELL"),
    ("AMZN", 2023, "Compare Amazon's total net sales in FY2022 and FY2023.", "COMPARATIVE_COLUMN"),
    ("META", 2024, "How much advertising revenue did Meta report for FY2024?", "SEGMENT_VS_TOTAL"),
    ("META", 2024, "How do Meta's FY2024 property purchases differ from capital expenditures including finance leases?", "ACCOUNTING_DEFINITION"),
    ("META", 2024, "What was Meta's FY2024 net cash from operating activities?", "CASH_FLOW"),
    ("TSLA", 2024, "What FY2024 revenue came from Tesla's energy generation and storage segment?", "SEGMENT_VS_TOTAL"),
    ("TSLA", 2023, "Compare Tesla's total revenues in FY2022 and FY2023.", "COMPARATIVE_COLUMN"),
    ("TSLA", 2023, "What portion of Tesla's FY2023 revenues came from automotive activities?", "TOTAL_VS_COMPONENT"),
    ("INTC", 2024, "What net income did Intel report for FY2024?", "EXACT_CELL"),
    ("INTC", 2024, "What was Intel's FY2024 gross margin?", "METRIC_DISAMBIGUATION"),
    ("AMD", 2024, "What was AMD's FY2024 operating income?", "EXACT_CELL"),
    ("AMD", 2024, "What FY2024 revenue did AMD attribute to its data center segment?", "SEGMENT_VS_TOTAL"),
]


def main() -> None:
    with zipfile.ZipFile(SOURCE) as z:
        audit = list(csv.DictReader(io.StringIO(z.read("audit/p7g_fiscal_metadata_audit.csv").decode("utf-8-sig"))))
        exposed = {json.loads(line)["query"].casefold() for line in z.read("baseline/p5_query_results.jsonl").splitlines()}
        exposed |= {json.loads(line)["question"].casefold() for line in z.read("audit/p7l_full_raw_top10.jsonl").splitlines()}
    cik_by_ticker = {"AMD": "0000002488", "INTC": "0000050863", "AAPL": "0000320193",
                     "MSFT": "0000789019", "AMZN": "0001018724", "NVDA": "0001045810",
                     "TSLA": "0001318605", "META": "0001326801"}
    rows = []
    for i, (ticker, year, question, category) in enumerate(DESIGN, 1):
        if question.casefold() in exposed:
            raise ValueError(f"Exposed duplicate: {question}")
        source = next((r for r in audit if r["filing_id"].startswith(cik_by_ticker[ticker] + "_")
                       and r["sec_form"] == "10-K" and r["sec_report_date"].startswith(str(year))), None)
        if source is None:
            raise ValueError(f"Source filing missing: {ticker} {year}")
        rows.append({"question_id": f"V5R_H{i:02}", "question": question, "category": category,
                     "source_ticker": ticker, "source_accession": source["accession"],
                     "source_url": source["source_url"], "sec_report_date": source["sec_report_date"],
                     "exact_source_span": "", "metric_definition": "", "period_column": "",
                     "value": "", "unit": "", "label": "UNJUDGED", "adjudicator": "",
                     "review_decision": "PENDING_HUMAN_SOURCE_REVIEW"})
    out = REPO / "docs/topic3_v5/recovery_live/holdout_30_review_queue.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    manifest = {"status": "SEALED_DESIGN_UNJUDGED", "questions": len(rows),
                "sha256": hashlib.sha256(out.read_bytes()).hexdigest(),
                "rule": "No evaluation or tuning on these questions before human source adjudication",
                "source_level": "filing URL only; exact cell spans pending reviewer"}
    (out.parent / "holdout_30_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest))


if __name__ == "__main__":
    main()
