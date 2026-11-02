"""Rerank saved A3 candidates at 10/20/50/100, exposed cases only."""

from __future__ import annotations

import csv
import io
import json
import statistics
import sys
import time
import zipfile
from collections import defaultdict

from topic3_v5r_restore import REPO, SOURCE

sys.path.insert(0, str(REPO))
from app.research_retrieval.faith_r import parse_query, rank_candidates  # noqa: E402

COVERAGE = REPO / "docs/topic3_v5/recovery_live/candidate_coverage.json"
ABLATION = REPO / "docs/topic3_v5/recovery_live/ablation_summary.json"
OUT = REPO / "docs/topic3_v6/V6_EXPOSED_BUDGET_ABLATION.json"


def main():
    coverage = json.loads(COVERAGE.read_text(encoding="utf-8"))
    ablation = json.loads(ABLATION.read_text(encoding="utf-8"))
    questions = {r["id"]: r["question"] for r in ablation["cases"]}
    original = {r["id"]: r["arms"]["A4"]["ids"] for r in ablation["cases"]}
    with zipfile.ZipFile(SOURCE) as archive:
        corpus = {r["chunk_id"]: r for r in
                  (json.loads(line) for line in archive.read("corpus/chunks_frozen.jsonl").splitlines())}
        labels = {(r["case"], r["chunk_id"]): r["final_review_label"] for r in
                  csv.DictReader(io.StringIO(archive.read("research/f10_closeout/f10_current_900_rank_checkpoint.csv").decode("utf-8-sig")))}
    rows = []
    for case in coverage["rows"]:
        if case["arm"] != "A3":
            continue
        slots = parse_query(questions[case["case"]])
        hits = [{"chunk_id": cid, "ticker": corpus[cid]["ticker"],
                 "fiscal_period": f"FY{slots.fiscal_year}" if slots.fiscal_year else corpus[cid]["fiscal_period"],
                 "text": corpus[cid]["text"], "score": 0}
                for cid in case["ids"]]
        start = time.perf_counter()
        ranked = rank_candidates(hits, slots, case["budget"])
        rerank_ms = round((time.perf_counter() - start) * 1000, 3)
        ids = [r.chunk_id for r in ranked]
        if case["budget"] == 10 and ids != original[case["case"]]:
            raise ValueError(f"A4@10 failed to reproduce: {case['case']}")
        judgments = [labels.get((case["case"], cid), "UNJUDGED") for cid in ids]
        rows.append({"case": case["case"], "budget": case["budget"],
                     "known_positive_h1": int(bool(judgments and judgments[0] == "YES")),
                     "known_positive_h3": int("YES" in judgments[:3]),
                     "known_positive_h10": int("YES" in judgments[:10]),
                     "known_positive_in_budget": int("YES" in judgments),
                     "unjudged_in_budget": judgments.count("UNJUDGED"),
                     "rerank_only_ms": rerank_ms, "ids": ids})
    summary = {}
    for budget in (10, 20, 50, 100):
        subset = [r for r in rows if r["budget"] == budget]
        assert len(subset) == 15
        summary[str(budget)] = {"questions": len(subset),
                                "known_positive_h1": sum(r["known_positive_h1"] for r in subset),
                                "known_positive_h3": sum(r["known_positive_h3"] for r in subset),
                                "known_positive_h10": sum(r["known_positive_h10"] for r in subset),
                                "known_positive_in_budget": sum(r["known_positive_in_budget"] for r in subset),
                                "unjudged_positions": sum(r["unjudged_in_budget"] for r in subset),
                                "rerank_only_p50_ms": statistics.median(r["rerank_only_ms"] for r in subset)}
    OUT.write_text(json.dumps({"status": "EXPOSED_DEVELOPMENT_SAVED_CANDIDATE_RERANK",
                               "a4_at_10_reproduced": True, "summary": summary, "rows": rows,
                               "limits": ["Candidate retrieval was measured previously, not rerun here",
                                          "F10 judgments incomplete; known-positive hits are lower bounds",
                                          "Rerank-only timing excludes Qdrant and embedding"]},
                              indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
