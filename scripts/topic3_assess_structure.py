"""Assess exposed SEC retrieval candidates without certifying financial values."""

from __future__ import annotations

import json
from pathlib import Path

from app.topic3.evidence_policy import assess_candidate


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "docs/topic3"


def main() -> None:
    chunks = {}
    for path in sorted((DATA / "03_IMPROVEMENTS/source_chunks").glob("*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            chunk = json.loads(line)
            chunks[chunk["chunk_id"]] = chunk
    issuers = {c["filing_id"]: c["metadata"]["ticker"] for c in chunks.values()}
    qrels = {q["id"]: q for q in map(json.loads, (DATA / "01_REPRODUCTION/PROVISIONAL_SOURCE_QRELS.jsonl").read_text(encoding="utf-8").splitlines())}
    results = json.loads((DATA / "03_IMPROVEMENTS/STRUCTURE_BM25_RESULTS.json").read_text(encoding="utf-8"))
    records = []
    for record in results["records"]:
        q = qrels[record["id"]]
        assessment = assess_candidate(q["query"], q["ticker"], [h["chunk_id"] for h in record["hits"]], chunks, issuers)
        records.append({"id": q["id"], "answerable_source_candidate": q["answerable"], **assessment})
    output = {"status": "EXPOSED_MACHINE_REVIEW_ONLY", "numeric_answers_certified": 0, "records": records}
    path = DATA / "03_IMPROVEMENTS/CONSERVATIVE_EVIDENCE_ASSESSMENT.json"
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(records, ensure_ascii=False))


if __name__ == "__main__":
    main()
