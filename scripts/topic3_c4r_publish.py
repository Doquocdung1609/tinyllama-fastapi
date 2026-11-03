"""Publish redacted C4R failure/answer summaries; keep values off Git."""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict
import csv
import hashlib
import json
from pathlib import Path

from app.research_retrieval.faith_r_a5 import plan_query, retrieval_filters


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def create(private_dir: Path, c4_dir: Path, source_manifest: Path,
           public_dir: Path) -> dict:
    private_register = private_dir / "C4R_R0_FAILURE_REGISTER_PRIVATE.json"
    casebook = private_dir / "C4R_WRONG_ANSWER_CASEBOOK_PRIVATE.md"
    public_stats = public_dir / "C4R_G2_POST_EXPOSURE_SUMMARY.json"
    if any(p.exists() for p in (private_register, casebook, public_stats)):
        raise FileExistsError("C4R publication exists; refusing overwrite")
    c4 = json.loads((c4_dir / "C4_FAILURE_DIAGNOSIS_PRIVATE.json").read_text(encoding="utf-8"))
    eligibility = {x["question_id"]: x for x in
                   json.loads((c4_dir / "C4_JUDGED_ELIGIBILITY.json").read_text(encoding="utf-8"))["all_94"]}
    g2 = {r["question_id"]: r["question"] for r in
          csv.DictReader((Path("docs/topic3_v7a_g2/V7A_SEC47_QUESTION_ONLY.csv"))
                         .open(encoding="utf-8-sig", newline=""))}
    a5 = {r["query_id"]: r for r in
          (json.loads(x) for x in
           (private_dir / "C4R_G2_POST_EXPOSURE_A5_BASE.jsonl").read_text(encoding="utf-8").splitlines())}
    sources = {s["accession"]: s for s in json.loads(source_manifest.read_text(encoding="utf-8"))["sources"]}
    if len(c4) != 93 or len(a5) != 94:
        raise ValueError("C4/G2 case counts changed")
    register = []
    counters = Counter()
    for old in c4:
        qid = old["question_id"]
        row, target = a5[qid], eligibility[qid]["target_accession"]
        source = sources[target]
        plan = plan_query(g2[qid])
        new_filter = retrieval_filters(plan)
        target_ranks = [h["rank"] for h in row["hits"] if h["accession"] == target]
        if old["target_payload_passes_fiscal_filter"] is False:
            counters["old_metadata_excluded"] += 1
            if new_filter.fiscal_periods is not None or new_filter.tickers != [source["ticker"]] or (plan.form and new_filter.document_types != [source["form"]]):
                raise ValueError("A5 still metadata-excludes target")
            counters["a5_filter_target_compatible"] += 1
        for k in (1, 5, 10, 20):
            counters[f"a5_target_hit_at_{k}"] += bool(target_ranks and min(target_ranks) <= k)
        counters["a5_eligible"] += 1
        register.append({"question_id": qid, "question": g2[qid],
                         "ticker": source["ticker"], "accession": target,
                         "form": source["form"], "report_date": source["report_date"],
                         "old_a4_filter": old["fiscal_filter"],
                         "target_payload_periods": old["target_payload_fiscal_periods"],
                         "old_a4_outcome": old["frozen_a4_outcome"],
                         "parsed_plan": asdict(plan), "a5_filter": asdict(new_filter),
                         "a5_status": row["status"], "a5_attempts": row["attempts"],
                         "a5_top5_candidate_ids": [h["chunk_id"] for h in row["hits"][:5]],
                         "a5_target_first_rank": min(target_ranks) if target_ranks else None,
                         "cause": "FY_HARD_FILTER_INCOMPATIBLE_WITH_TARGET_METADATA" if
                                  not old["target_payload_passes_fiscal_filter"] else
                                  "OTHER_CANDIDATE_OR_RANKING_NOT_ISOLATED"})
    if (counters["old_metadata_excluded"], counters["a5_filter_target_compatible"],
            counters["a5_eligible"]) != (46, 46, 93):
        raise ValueError("C4 frozen 46/93 diagnosis changed")
    comparison = [json.loads(x) for x in
                  (private_dir / "C4R_HOLDOUT_ANSWER_COMPARISON_QUESTION_LEVEL.jsonl")
                  .read_text(encoding="utf-8").splitlines()]
    failures = [r for r in comparison if not r["correct"]]
    lines = ["# C4R complete private wrong/refused answer casebook", "",
             "Source-derived machine reference is unreviewed. ORIGINAL_CHUNK_ONLY abstains when column context is flattened.", ""]
    for r in failures:
        lines.extend([f"## {r['query_id']} / {r['method']} / {r['track']}", "",
                      f"Question: {r['query_original']}",
                      f"Reference: {r['gold_value']} {r['gold_unit']} for {r['gold_period']} "
                      f"at {r['gold_locator']} (SHA {r['gold_source_sha']}).",
                      f"Output: {r['final_answer_literal'] or '<ABSTAIN>'}; status {r['answer_status']}; "
                      f"error {r['error_code']}.",
                      f"Original candidates: {[(x['rank'], x['chunk_id'], x['accession']) for x in r['candidate_ids_and_ranks'][:5]]}",
                      f"Cause: {'wrong filing absent from Top-5' if not r['hit_at_5'] else 'original chunk has no verified column binding' if r['track']=='ORIGINAL_CHUNK_ONLY' else 'cell/period/unit ambiguity'}.",
                      "Code: `app/research_retrieval/financial_answer_v8.py` and `app/research_retrieval/faith_r_a5.py`.", ""])
    private_register.write_text(json.dumps(register, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    casebook.write_text("\n".join(lines) + "\n", encoding="utf-8")
    public = {"schema": "c4r_g2_post_exposure_diagnostic_summary/v1",
              "frozen_g2_questions": 94, "eligible_proxy": 93,
              "old_a4_metadata_mismatch": 46,
              "a5_filter_target_compatible_in_old_mismatches": 46,
              "a5_status_counts": dict(Counter(r["status"] for r in a5.values())),
              "a5_target_filing_hit_at_1": counters["a5_target_hit_at_1"],
              "a5_target_filing_hit_at_5": counters["a5_target_hit_at_5"],
              "a5_target_filing_hit_at_10": counters["a5_target_hit_at_10"],
              "a5_target_filing_hit_at_20": counters["a5_target_hit_at_20"],
              "old_a4_hit_rows": 67,
              "old_a4_unknown_zero_vs_omitted": 26,
              "old_stage2_author_target_hit_at_5": 90,
              "strict_label": "POST_EXPOSURE_REGRESSION_DIAGNOSTIC_NOT_INDEPENDENT",
              "private_register_sha256": sha(private_register),
              "private_casebook_sha256": sha(casebook),
              "private_g2_run_sha256": sha(private_dir / "C4R_G2_POST_EXPOSURE_A5_BASE.jsonl"),
              "holdout_failure_records_all_methods_tracks": len(failures)}
    public_stats.write_text(json.dumps(public, indent=2) + "\n", encoding="utf-8")
    return public


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("private_dir", "c4_dir", "source_manifest", "public_dir"):
        p.add_argument("--" + name.replace("_", "-"), type=Path, required=True)
    print(json.dumps(create(**vars(p.parse_args())), indent=2))
