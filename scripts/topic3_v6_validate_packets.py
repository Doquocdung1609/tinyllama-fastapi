"""Check each review candidate against the immutable official HTML snapshot."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

from bs4 import BeautifulSoup

from topic3_v5r_restore import REPO

SPLITS = [
    (REPO / "docs/topic3_v5/recovery_live/holdout_30_review_queue.csv",
     REPO / "docs/topic3_v6/V6_SOURCE_FIRST_REVIEW_PACKETS"),
    (REPO / "docs/topic3_v6/V6_FRESH_HOLDOUT_30_UNJUDGED.csv",
     REPO / "docs/topic3_v6/V6_FRESH_HOLDOUT_REVIEW_PACKETS"),
]


def clean(value: str) -> str:
    import re
    return re.sub(r"\s+", " ", value).strip()[:300]


def main():
    tables_cache = {}
    validated = 0
    candidates = 0
    errors = []
    for queue_path, directory in SPLITS:
        queue = list(csv.DictReader(queue_path.open(encoding="utf-8", newline="")))
        manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
        if len(queue) != 30 or manifest["queue_sha256"] != hashlib.sha256(queue_path.read_bytes().replace(b"\r\n", b"\n")).hexdigest():
            errors.append(f"Queue/manifest mismatch: {queue_path}")
        for row in queue:
            qid = row["question_id"]
            packet_path = directory / f"{qid}.json"
            html_path = directory / f"{qid}.html"
            packet = json.loads(packet_path.read_text(encoding="utf-8"))
            if not html_path.is_file() or packet["label"] != "UNJUDGED" or packet["question"] != row["question"]:
                errors.append(f"Packet missing or judged: {qid}")
            if any(value is not None for value in packet["review_fields"].values()):
                errors.append(f"Reviewer field already filled: {qid}")
            acc = row["source_accession"]
            source = REPO / "tmp/topic3_v5r/sec_html" / f"{acc}.html"
            if packet["official_html_sha256"] != hashlib.sha256(source.read_bytes()).hexdigest():
                errors.append(f"Snapshot hash mismatch: {qid}")
            if acc not in tables_cache:
                soup = BeautifulSoup(source.read_bytes(), "html.parser")
                tables_cache[acc] = [
                    [[clean(cell.get_text(" ", strip=True)) for cell in tr.find_all(["th", "td"], recursive=False)]
                     for tr in table.find_all("tr") if any(clean(cell.get_text(" ", strip=True))
                                                            for cell in tr.find_all(["th", "td"], recursive=False))]
                    for table in soup.find_all("table")]
            tables = tables_cache[acc]
            for item in packet["source_first_table_candidates"]:
                ti, ri = item["table_index_zero_based"], item["row_index_zero_based"]
                if ti >= len(tables) or ri >= len(tables[ti]) or tables[ti][ri] != item["row_cells"]:
                    errors.append(f"Original row mismatch: {qid} table {ti} row {ri}")
                candidates += 1
            validated += 1
    result = {"status": "PASS" if not errors else "FAIL", "packets": validated,
              "candidate_table_rows_checked": candidates, "official_html_snapshots": len(tables_cache),
              "human_reviews": 0, "errors": errors[:20]}
    out = REPO / "docs/topic3_v6/V6_SOURCE_PACKET_VALIDATION.json"
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result))
    if errors:
        raise ValueError(f"Packet validation failed: {len(errors)}")


if __name__ == "__main__":
    main()
