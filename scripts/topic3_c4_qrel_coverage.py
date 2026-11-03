"""Report provisional judged coverage at K without computing relevance quality."""

from __future__ import annotations

from collections import defaultdict
import json
from pathlib import Path
from hashlib import sha256
import argparse


def sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def rows(path: Path):
    return (json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
            if line)


def run(lock_path: Path, eligibility_path: Path, ranked_path: Path,
        qrel_path: Path, out: Path) -> dict:
    if out.exists():
        raise FileExistsError(out)
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    if (sha(eligibility_path) != lock["private_eligibility_sha256"] or
            sha(ranked_path) != lock["ranked_pool_sha256"]):
        raise ValueError("C4 lock or ranked bytes changed")
    eligibility = json.loads(eligibility_path.read_text(encoding="utf-8"))
    eligible = {r["question_id"] for r in eligibility["all_94"]
                if r["target_filing_proxy_eligible"]}
    qrels = {(r["question_id"], r["chunk_id"]): r["grade"] for r in rows(qrel_path)}
    if len(eligible) != 93 or len(qrels) != 5792 or set(qrels.values()) != {
            "PARTIAL", "UNJUDGED"}:
        raise ValueError("Eligible universe or provisional qrels changed")
    runs = defaultdict(list)
    for row in rows(ranked_path):
        if row["question_id"] in eligible:
            runs[row["index"], row["arm"], row["question_id"]].append(row)
    by_arm = defaultdict(list)
    for (index, arm, qid), hits in runs.items():
        hits.sort(key=lambda row: row["rank"])
        if [r["rank"] for r in hits] != list(range(1, len(hits)+1)):
            raise ValueError("Rank structure changed")
        by_arm[index, arm].append((qid, hits))
    result = []
    for (index, arm), grouped in sorted(by_arm.items()):
        entry = {"index": index, "arm": arm,
                 "eligible_questions": 93, "observed_hit_row_runs": len(grouped),
                 "runs_without_hit_rows": 93 - len(grouped)}
        for k in (1, 5, 10):
            slots = [r for _, hits in grouped for r in hits[:k]]
            partial = sum(qrels[r["question_id"], r["chunk_id"]] == "PARTIAL"
                          for r in slots)
            entry[f"at_{k}"] = {
                "candidate_slots": len(slots), "ai_provisional_partial": partial,
                "unjudged": len(slots) - partial,
                "exact": 0, "human_judged": 0,
            }
        result.append(entry)
    report = {
        "schema": "c4_provisional_original_chunk_coverage_at_k/v1",
        "ranked_pool_sha256": sha(ranked_path),
        "qrel_sha256": sha(qrel_path),
        "question_denominator": 93,
        "qrel_scope": "AI_PROVISIONAL_ONLY_NOT_HUMAN_GOLD",
        "method": "Candidate slots among observed hit-row runs; repeated chunks across arms count once per arm/run; missing runs remain unknown",
        "arms": result,
        "exact_relevance_metrics": "NOT_REPORTABLE",
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("lock_path", "eligibility_path", "ranked_path", "qrel_path", "out"):
        p.add_argument("--"+name.replace("_", "-"), type=Path, required=True)
    r = run(**vars(p.parse_args()))
    print(json.dumps({"arms":len(r["arms"]),"question_denominator":r["question_denominator"],
                      "exact_relevance_metrics":r["exact_relevance_metrics"]}))
