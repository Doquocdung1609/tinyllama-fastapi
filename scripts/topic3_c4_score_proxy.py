"""Score only a preregistered objective filing-ID proxy from real G3U pool hits."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from hashlib import sha256
import json
from pathlib import Path


ARMS_A = ["AUTHOR_BM25", "AUTHOR_DENSE", "AUTHOR_SPARSE",
          "AUTHOR_BM25_DENSE", "AUTHOR_SPARSE_DENSE", "AUTHOR_RERANK",
          "FAITH_R_A0"]
ARMS_B = ["AUTHOR_BM25", "AUTHOR_DENSE", "AUTHOR_SPARSE",
          "AUTHOR_BM25_DENSE", "AUTHOR_SPARSE_DENSE", "AUTHOR_RERANK",
          "FAITH_R_A1", "FAITH_R_A2", "FAITH_R_A3",
          "FAITH_R_A4", "FAITH_R_A4R"]
EXPECTED = {("A", arm) for arm in ARMS_A} | {("B", arm) for arm in ARMS_B}


def sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def jsonl(path: Path):
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            if line.strip():
                yield json.loads(line)


def quantile(values: list[float], p: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = (len(ordered) - 1) * p
    low = int(index)
    return round(ordered[low] + (ordered[min(low + 1, len(ordered) - 1)] -
                                 ordered[low]) * (index - low), 3)


def score(lock_path: Path, eligibility_path: Path, pool_dir: Path,
          qrel_dir: Path, result_path: Path, summary_path: Path,
          public_path: Path) -> dict:
    if any(path.exists() for path in (result_path, summary_path, public_path)):
        raise FileExistsError("C4 proxy score already exists")
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    if (lock["metric_scope"] != "TRACK_B_OBJECTIVE_TARGET_FILING_PROXY_ONLY" or
            lock["original_single_chunk_exact_qrels"] != 0 or
            sha(eligibility_path) != lock["private_eligibility_sha256"]):
        raise ValueError("Pre-scoring eligibility lock failed")
    eligibility = json.loads(eligibility_path.read_text(encoding="utf-8"))
    by_qid = {row["question_id"]: row for row in eligibility["all_94"]}
    if (len(by_qid) != 94 or
            sum(x["target_filing_proxy_eligible"] for x in by_qid.values()) != 93):
        raise ValueError("Frozen denominator changed")
    manifest = json.loads((pool_dir / "G3U_POOL_MANIFEST.json").read_text(encoding="utf-8"))
    ranked_path = pool_dir / "G3U_RANKED_POOL_SEALED.jsonl"
    blind_path = pool_dir / "G3U_BLIND_REVIEW_POOL.jsonl"
    if (manifest["status"] != "POOL_GENERATED_NOT_SCORED" or
            sha(ranked_path) != lock["ranked_pool_sha256"] or
            sha(blind_path) != manifest["blind_sha256"]):
        raise ValueError("Sealed ranked/blind pool identity changed")
    blind = {(row["question_id"], row["chunk_id"]): row for row in jsonl(blind_path)}
    if len(blind) != manifest["unique_blind_pairs"]:
        raise ValueError("Blind union duplicate/count mismatch")
    qrel_manifest = json.loads((qrel_dir / "G3U_QREL_PREPARATION_MANIFEST.json")
                                .read_text(encoding="utf-8"))
    qrel_path = qrel_dir / "G3U_AI_QREL_PROVISIONAL.jsonl"
    if sha(qrel_path) != qrel_manifest["files"]["ai"]["sha256"]:
        raise ValueError("Qrel input changed")
    grades = {(r["question_id"], r["chunk_id"]): r["grade"] for r in jsonl(qrel_path)}
    if len(grades) != len(blind) or set(grades) != set(blind) or set(grades.values()) != {
            "PARTIAL", "UNJUDGED"}:
        raise ValueError("Qrel coverage or conservative grade set changed")
    runs = defaultdict(list)
    line_count = 0
    for row in jsonl(ranked_path):
        line_count += 1
        qid, arm, index, chunk_id = (row["question_id"], row["arm"],
                                      row["index"], row["chunk_id"])
        if (qid not in by_qid or (index, arm) not in EXPECTED or
                (qid, chunk_id) not in blind or not 1 <= row["rank"] <= 20 or
                row["original_text_sha256"] != blind[qid, chunk_id]["original_text_sha256"]):
            raise ValueError("Ranked row does not match frozen original chunk")
        runs[qid, index, arm].append(row)
    if line_count != manifest["ranked_lines"]:
        raise ValueError("Ranked line count changed")
    for key, rows in runs.items():
        if sorted(row["rank"] for row in rows) != list(range(1, len(rows) + 1)):
            raise ValueError(f"Noncontiguous or duplicate ranks: {key}")
    records = []
    for qid in sorted(by_qid):
        eligible = by_qid[qid]["target_filing_proxy_eligible"]
        target = by_qid[qid]["target_accession"]
        for index, arm in sorted(EXPECTED):
            hits = sorted(runs.get((qid, index, arm), []), key=lambda r: r["rank"])
            target_ranks = [r["rank"] for r in hits if
                            blind[qid, r["chunk_id"]]["chunk_accession"] == target]
            observed = bool(hits)
            first_target = min(target_ranks) if target_ranks else None
            records.append({
                "question_id": qid, "index": index, "arm": arm,
                "source_release_preview": by_qid[qid]["release_preview"],
                "target_filing_proxy_eligible": eligible,
                "run_has_ranked_hit_rows": observed,
                "run_provenance_if_no_rows": "UNKNOWN_ZERO_VS_OMITTED" if not observed else "HIT_ROWS_PRESENT",
                "returned_hits": len(hits),
                "first_target_filing_rank": first_target,
                "hit_at_1": (first_target <= 1) if first_target is not None else False,
                "hit_at_5": (first_target <= 5) if first_target is not None else False,
                "hit_at_10": (first_target <= 10) if first_target is not None else False,
                "latency_ms": hits[0]["elapsed_ms"] if hits else None,
                "top_5_original_chunk_ids": [r["chunk_id"] for r in hits[:5]],
                "top_5_accessions": [blind[qid, r["chunk_id"]]["chunk_accession"]
                                     for r in hits[:5]],
                "top_5_ai_provisional_partial_count": sum(
                    grades[qid, r["chunk_id"]] == "PARTIAL" for r in hits[:5]),
                "top_5_unjudged_count": sum(
                    grades[qid, r["chunk_id"]] == "UNJUDGED" for r in hits[:5]),
            })
    by_arm = defaultdict(list)
    by_run = {}
    for row in records:
        by_arm[row["index"], row["arm"]].append(row)
        by_run[row["question_id"], row["index"], row["arm"]] = row
    arm_rows = []
    for (index, arm), rows in sorted(by_arm.items()):
        evaluated = [r for r in rows if r["target_filing_proxy_eligible"] and
                     r["run_has_ranked_hit_rows"]]
        unknown = sum(r["target_filing_proxy_eligible"] and
                      not r["run_has_ranked_hit_rows"] for r in rows)
        latencies = [float(r["latency_ms"]) for r in evaluated]
        arm_rows.append({
            "index": index, "arm": arm,
            "eligible_questions": 93,
            "observed_runs": len(evaluated),
            "unknown_zero_or_omitted": unknown,
            **{f"hit_at_{k}_numerator": sum(r[f"hit_at_{k}"] for r in evaluated)
               for k in (1, 5, 10)},
            "latency_p50_ms": quantile(latencies, .5),
            "latency_p95_ms": quantile(latencies, .95),
            "latency_scope": "G3U per-arm query including embedding and local Qdrant; cold/warm mixed",
        })
    if sum(row["unknown_zero_or_omitted"] for row in arm_rows) > 104:
        raise ValueError("Missing hit-row count exceeds structural audit")
    pairs = []
    comparisons = [
        ("B", "AUTHOR_BM25", "B", "FAITH_R_A4", "same_index_bm25_vs_a4"),
        ("B", "AUTHOR_BM25_DENSE", "B", "FAITH_R_A4", "same_index_bm25_dense_vs_a4"),
        ("B", "AUTHOR_RERANK", "B", "FAITH_R_A4", "same_index_stage2_vs_a4"),
        ("A", "FAITH_R_A0", "B", "FAITH_R_A1", "system_a0_to_a1"),
        ("B", "FAITH_R_A1", "B", "FAITH_R_A2", "ablation_a1_to_a2"),
        ("B", "FAITH_R_A2", "B", "FAITH_R_A3", "ablation_a2_to_a3"),
        ("B", "FAITH_R_A3", "B", "FAITH_R_A4", "ablation_a3_to_a4"),
    ]
    for left_idx, left_arm, right_idx, right_arm, label in comparisons:
        common = [
            (by_run[qid, left_idx, left_arm], by_run[qid, right_idx, right_arm])
            for qid in sorted(by_qid) if by_qid[qid]["target_filing_proxy_eligible"] and
            by_run[qid, left_idx, left_arm]["run_has_ranked_hit_rows"] and
            by_run[qid, right_idx, right_arm]["run_has_ranked_hit_rows"]
        ]
        wins = sum(int(right["hit_at_5"]) > int(left["hit_at_5"])
                   for left, right in common)
        losses = sum(int(right["hit_at_5"]) < int(left["hit_at_5"])
                     for left, right in common)
        pairs.append({
            "comparison": label, "left": f"{left_idx}:{left_arm}",
            "right": f"{right_idx}:{right_arm}",
            "metric": "OBJECTIVE_TARGET_FILING_HIT_AT_5_PROXY",
            "paired_denominator": len(common),
            "right_win": wins, "tie": len(common) - wins - losses,
            "right_loss": losses,
            "left_hits_on_paired": sum(x["hit_at_5"] for x, _ in common),
            "right_hits_on_paired": sum(y["hit_at_5"] for _, y in common),
        })
    result_path.parent.mkdir(parents=True, exist_ok=True)
    with result_path.open("w", encoding="utf-8", newline="\n") as stream:
        for row in records:
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")
    summary = {
        "schema": "c4_real_g3u_proxy_replay/v1",
        "provenance": "SCORED_EXISTING_REAL_ONE_SHOT_G3U_V2_RANKED_LOG_NO_NEW_G2_QUERIES",
        "eligibility_sha256": sha(eligibility_path),
        "ranked_pool_sha256": sha(ranked_path),
        "blind_pool_sha256": sha(blind_path),
        "qrel_sha256": sha(qrel_path),
        "per_query_arm_sha256": sha(result_path),
        "frozen_questions": 94,
        "objective_proxy_eligible": 93,
        "excluded": 1,
        "expected_arm_question_index_runs": 94 * len(EXPECTED),
        "observed_hit_row_runs": len(runs),
        "no_hit_rows_provenance_unknown": 94 * len(EXPECTED) - len(runs),
        "ranked_lines": line_count,
        "arms": arm_rows,
        "paired": pairs,
        "original_chunk_exact_at_k": "NOT_REPORTABLE_ZERO_EXACT_QRELS",
        "financial_answer_correctness": "NOT_RUN_NO_QUALIFIED_ANSWER_SCORING_INPUT",
        "final_G2_relevance_metrics": "NOT_RUN",
        "method_limits": [
            "Target filing hit is only a document-identity proxy, not answer correctness.",
            "A2/A3/A4 use issuer/fiscal logic; filter gains are not intrinsic ranking gains.",
            "A vs B index contains corrected fiscal metadata on 3516 points across 15 filings.",
            "Author native RRF in this sealed pool uses actual Qdrant default k=2, not explicit k=60.",
            "A4R is exposed development, not independent evidence.",
            "Unknown no-hit-row runs are excluded from denominators, not coerced to misses.",
            "AI-provisional PARTIAL/UNJUDGED do not support EXACT/MRR/nDCG/Recall.",
        ],
    }
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    public = {key: summary[key] for key in (
        "schema", "provenance", "eligibility_sha256", "ranked_pool_sha256",
        "blind_pool_sha256", "qrel_sha256", "per_query_arm_sha256",
        "frozen_questions", "objective_proxy_eligible", "excluded",
        "expected_arm_question_index_runs", "observed_hit_row_runs",
        "no_hit_rows_provenance_unknown", "ranked_lines", "arms", "paired",
        "original_chunk_exact_at_k", "financial_answer_correctness",
        "final_G2_relevance_metrics", "method_limits")}
    public_path.parent.mkdir(parents=True, exist_ok=True)
    public_path.write_text(json.dumps(public, indent=2) + "\n", encoding="utf-8")
    return public


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("lock_path", "eligibility_path", "pool_dir", "qrel_dir",
                 "result_path", "summary_path", "public_path"):
        parser.add_argument("--" + name.replace("_", "-"), type=Path, required=True)
    report = score(**vars(parser.parse_args()))
    print(json.dumps({k: report[k] for k in
                      ("frozen_questions", "objective_proxy_eligible",
                       "observed_hit_row_runs", "no_hit_rows_provenance_unknown",
                       "final_G2_relevance_metrics")}, indent=2))
