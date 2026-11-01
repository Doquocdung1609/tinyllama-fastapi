"""Reproducible, label-blind rerank of the supplied P7L development Top-10."""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.research_retrieval.faith_r import parse_query, rank_recorded_top10


DRIVE = ROOT / "tmp/topic3_v5/handoff-f2fdd13c/drive/reproduction_v1/04_failure_analysis"
RAW = DRIVE / "p7l_live_ab_corrected_metadata/p7l_full_raw_top10.jsonl"
F10 = DRIVE / "f10_one_run_closeout_audit/f10_current_900_rank_checkpoint.csv"
P7L = DRIVE / "p7l_live_ab_corrected_metadata/p7l_full_results.csv"
P7G = DRIVE / "p7g_sec_fiscal_audit/p7g_fiscal_metadata_audit.csv"
OUT = ROOT / "docs/topic3_v5/replay_results.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    if not all(p.is_file() for p in (RAW, F10, P7L, P7G)):
        raise SystemExit("Handoff missing; run topic3_v5_extract_handoff.py first")
    raw = [json.loads(line) for line in RAW.read_text(encoding="utf-8").splitlines()]
    labels = {}
    with F10.open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            key = (row["case"], row["method"], row["chunk_id"])
            value = row["final_review_label"]
            if key in labels and labels[key] != value:
                raise ValueError(f"Conflicting F10 labels: {key}")
            labels[key] = value
    historical = list(csv.DictReader(P7L.open(encoding="utf-8-sig", newline="")))
    fiscal_sources = {r["accession"]: r for r in csv.DictReader(P7G.open(encoding="utf-8-sig", newline=""))}
    case_accessions = {r["case"]: r["target_accession"] for r in historical}
    historical_counts = {}
    for variant in ("A_ORIGINAL", "B_CORRECTED"):
        rows = [r for r in historical if r["variant"] == variant]
        historical_counts[variant] = {f"target_h{k}": sum(int(r[f"target_h{k}"]) for r in rows) for k in (1, 3, 10)} | {"runs": len(rows)}

    cases = []
    for record in raw:
        if record["method"] != "bm25_dense" or record["variant"] != "B_CORRECTED":
            continue
        original = record["results"]
        slots = parse_query(record["question"])
        ranked = rank_recorded_top10(original, slots)
        old_ids = [h["chunk_id"] for h in original]
        new_ids = [h.chunk_id for h in ranked]
        if sorted(old_ids) != sorted(new_ids):
            raise AssertionError("Candidate pool changed")
        case = record["case"]
        def summarize(ids: list[str]) -> dict:
            ls = [labels.get((case, "bm25_dense", cid), "UNJUDGED") for cid in ids]
            return {
                "ids": ids, "labels": ls,
                "known_positive_hit": {str(k): int("YES" in ls[:k]) for k in (1, 3, 10)},
                "possible_positive_hit": {str(k): int(any(v in ("YES", "UNJUDGED") for v in ls[:k])) for k in (1, 3, 10)},
            }
        accession = case_accessions[case]
        source = fiscal_sources.get(accession)
        if source is None:
            raise ValueError(f"P7G source missing: {accession}")
        cases.append({"case": case, "question": record["question"], "slots": slots.__dict__,
                      "source": {k: source[k] for k in ("accession", "source_url", "sec_form", "sec_report_date", "sec_filing_date", "corpus_label", "audit_status")},
                      "A1_recorded": summarize(old_ids), "A4_reranked": summarize(new_ids),
                      "verification_status": "UNVERIFIED",
                      "candidate_features": [c.__dict__ for c in ranked]})
    if len(cases) != 15:
        raise AssertionError(f"Expected 15 development cases, got {len(cases)}")
    aggregate = {}
    for name in ("A1_recorded", "A4_reranked"):
        aggregate[name] = {
            "known_positive_hit": {str(k): sum(c[name]["known_positive_hit"][str(k)] for c in cases) for k in (1, 3, 10)},
            "possible_positive_hit": {str(k): sum(c[name]["possible_positive_hit"][str(k)] for c in cases) for k in (1, 3, 10)},
            "top1_labels": dict(Counter(c[name]["labels"][0] for c in cases)),
        }
    result = {"protocol": "exposed_development_replay_no_blinding", "case_count": len(cases),
              "inputs_sha256": {p.name: sha(p) for p in (RAW, F10, P7L, P7G)},
              "historical_target_filing_hits": historical_counts,
              "aggregate": aggregate, "cases": cases}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"historical": historical_counts, "aggregate": aggregate}, indent=2))


if __name__ == "__main__":
    main()
