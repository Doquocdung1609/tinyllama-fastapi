"""Print a bounded, transparently post-hoc real G3U head-to-head example."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def run(question_id: str, results: Path, blind_pool: Path, eligibility: Path) -> dict:
    allowed = {"V7A_G2_05_01", "V7A_G2_03_01"}
    if question_id not in allowed:
        raise ValueError("Demo case must be one of the two disclosed examples")
    meta = {r["question_id"]: r for r in
            json.loads(eligibility.read_text(encoding="utf-8"))["all_94"]}
    if question_id not in meta:
        raise ValueError("Question absent from frozen eligibility")
    candidate = {}
    for line in blind_pool.read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        if r["question_id"] == question_id:
            candidate[r["chunk_id"]] = r
    rows = {}
    for line in results.read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        if (r["question_id"] == question_id and r["index"] == "B" and
                r["arm"] in {"AUTHOR_BM25_DENSE", "FAITH_R_A4"}):
            rows[r["arm"]] = r
    if len(rows) != 2:
        raise ValueError("Frozen example is missing one comparison arm")
    arms = {}
    for name, row in rows.items():
        arms[name] = {
            "first_target_filing_rank": row["first_target_filing_rank"],
            "latency_ms": row["latency_ms"],
            "top_5": [
                {"rank": i, "chunk_id": cid,
                 "accession": candidate[cid]["chunk_accession"],
                 "source_section": candidate[cid]["chunk_section"],
                 "excerpt": candidate[cid]["original_text"].replace("\n", " ")[:180]}
                for i, cid in enumerate(row["top_5_original_chunk_ids"], 1)
            ],
        }
    return {
        "disclosure": "ILLUSTRATIVE_CASE_SELECTED_POST_HOC_NOT_INDEPENDENT_WIN_RATE",
        "question_id": question_id,
        "question": next(iter(candidate.values()))["question"],
        "target_accession": meta[question_id]["target_accession"],
        "metric": "TARGET_FILING_ID_PROXY_NOT_EXACT_ANSWER",
        "arms": arms,
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--question-id", required=True)
    for name in ("results", "blind_pool", "eligibility"):
        p.add_argument("--"+name.replace("_", "-"), type=Path, required=True)
    print(json.dumps(run(**vars(p.parse_args())), indent=2, ensure_ascii=False))
