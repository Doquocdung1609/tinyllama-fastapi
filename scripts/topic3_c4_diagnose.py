"""Explain frozen A4 filing-proxy failures from read-only index-B metadata."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import zipfile

from app.research_retrieval.faith_r import parse_query


def run(handoff: Path, eligibility: Path, per_query: Path, index_b: Path,
        private_out: Path, public_out: Path) -> dict:
    if private_out.exists() or public_out.exists():
        raise FileExistsError("C4 failure diagnosis already exists")
    with zipfile.ZipFile(handoff) as archive:
        dataset = json.loads(archive.read("G3T_HUMAN_REVIEW_INPUT_20261103_V2.json"))
    questions = {row["question_id"]: row for row in dataset["records"]}
    eligible = {row["question_id"]: row for row in
                json.loads(eligibility.read_text(encoding="utf-8"))["all_94"]}
    runs = {(row["question_id"], row["index"], row["arm"]): row for row in
            (json.loads(line) for line in per_query.read_text(encoding="utf-8").splitlines())}
    from qdrant_client import QdrantClient
    client = QdrantClient(path=str(index_b))
    periods: dict[str, Counter] = defaultdict(Counter)
    try:
        offset = None
        while True:
            batch, offset = client.scroll("financial_docs", offset=offset, limit=256,
                                          with_payload=True, with_vectors=False)
            for point in batch:
                payload = point.payload
                periods[payload.get("accession_number")][payload.get("fiscal_period")] += 1
            if offset is None:
                break
    finally:
        client.close()
    if len(periods) != 47 or sum(sum(x.values()) for x in periods.values()) != 8670:
        raise ValueError("Index B 47-source / 8,670-point metadata changed")
    detail = []
    counts = Counter()
    for qid in sorted(eligible):
        if not eligible[qid]["target_filing_proxy_eligible"]:
            continue
        source = questions[qid]
        slots = parse_query(source["question"])
        wanted = (f"FY{slots.fiscal_year}" if
                  slots.fiscal_year and not slots.comparative_intent else None)
        target_periods = dict(periods[source["accession"]])
        target_match = wanted is None or wanted in target_periods
        row = runs[qid, "B", "FAITH_R_A4"]
        outcome = ("NO_RANKED_HIT_ROWS" if not row["run_has_ranked_hit_rows"] else
                   "WRONG_FILING_ALL_TOP20" if row["first_target_filing_rank"] is None else
                   "TARGET_FILING_HIT")
        counts[outcome, not target_match] += 1
        detail.append({
            "question_id": qid, "form": source["form"], "ticker": source["ticker"],
            "target_accession": source["accession"],
            "fiscal_filter": wanted,
            "target_payload_fiscal_periods": target_periods,
            "target_payload_passes_fiscal_filter": target_match,
            "frozen_a4_outcome": outcome,
        })
    if counts != {("NO_RANKED_HIT_ROWS", True): 26,
                  ("WRONG_FILING_ALL_TOP20", True): 20,
                  ("TARGET_FILING_HIT", False): 47}:
        raise ValueError(f"Unexpected frozen filter diagnosis: {counts}")
    by_form = Counter(row["form"] for row in detail if
                      row["frozen_a4_outcome"] == "NO_RANKED_HIT_ROWS")
    if by_form != {"10-Q": 24, "20-F": 2}:
        raise ValueError("Zero-result source form distribution changed")
    private_out.parent.mkdir(parents=True, exist_ok=True)
    private_out.write_text(json.dumps(detail, indent=2) + "\n", encoding="utf-8")
    public = {
        "schema": "c4_frozen_a4_metadata_diagnosis/v1",
        "read_only_index_b_points": 8670,
        "read_only_index_b_accessions": 47,
        "eligible_questions": 93,
        "target_filing_hit_and_filter_match": 47,
        "no_ranked_hit_rows_with_target_filter_mismatch": 26,
        "wrong_filing_all_top20_with_target_filter_mismatch": 20,
        "no_ranked_hit_rows_by_form": dict(by_form),
        "root_cause": "safe_filters asks for FY<question year> on single-year questions; 10-Q target payloads use Q-YYYY-MM, and the two TSM 20-F FY2022 targets carry FY2023 metadata in index B.",
        "causality_limit": "Metadata mismatch explains target exclusion. It does not prove why every non-target candidate was ordered as observed.",
        "post_score_action": "DIAGNOSIS_ONLY_NO_G2_RERUN_NO_POST_HOC_ALGORITHM_FIX",
    }
    public_out.parent.mkdir(parents=True, exist_ok=True)
    public_out.write_text(json.dumps(public, indent=2) + "\n", encoding="utf-8")
    return public


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("handoff", "eligibility", "per_query", "index_b", "private_out",
                 "public_out"):
        parser.add_argument("--" + name.replace("_", "-"), type=Path, required=True)
    print(json.dumps(run(**vars(parser.parse_args())), indent=2))
