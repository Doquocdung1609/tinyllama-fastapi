"""Explain the two P7L A rank mismatches using immutable saved rows."""

import hashlib
import json
import zipfile
from pathlib import Path

from topic3_v5r_restore import REPO, SOURCE

LIVE = REPO / "tmp/topic3_v5r/live/p7l_A.jsonl"
OUT = REPO / "docs/topic3_v6/V6_P7L_DISCREPANCY_DATA.json"


def main():
    live = {(r["id"], r["method"]): r for r in map(json.loads, LIVE.read_text(encoding="utf-8").splitlines())}
    with zipfile.ZipFile(SOURCE) as archive:
        historical = {(r["case"], r["method"], r["variant"][0]): r
                      for r in map(json.loads, archive.read("audit/p7l_full_raw_top10.jsonl").splitlines())}
    differences = []
    for (case, method), current in live.items():
        old = historical[case, method, "A"]
        ids = [r["chunk_id"] for r in current["results"]]
        old_ids = [r["chunk_id"] for r in old["results"]]
        if ids == old_ids:
            continue
        shared = set(ids) & set(old_ids)
        old_scores = {r["chunk_id"]: r["score"] for r in old["results"]}
        new_scores = {r["chunk_id"]: r["score"] for r in current["results"]}
        differences.append({"case": case, "method": method, "same_top1": ids[0] == old_ids[0],
                            "same_top10_set": set(ids) == set(old_ids),
                            "old_ids": old_ids, "new_ids": ids,
                            "moved": [{"chunk_id": cid, "old_rank": old_ids.index(cid) + 1,
                                       "new_rank": ids.index(cid) + 1,
                                       "old_score": old_scores[cid], "new_score": new_scores[cid],
                                       "score_delta": new_scores[cid] - old_scores[cid]}
                                      for cid in old_ids if cid in shared and old_ids.index(cid) != ids.index(cid)]})
    if len(differences) != 2:
        raise ValueError(f"Unexpected P7L A mismatch count: {len(differences)}")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"status": "SAVED_RANK_DIFFERENCES_EXPLAINED_TO_OBSERVABLE_LEVEL",
                               "live_sha256": hashlib.sha256(LIVE.read_bytes()).hexdigest(),
                               "mismatches": differences,
                               "root_cause": "UNRESOLVED: dense score drift is observed; old query vector and exact P3C snapshot unavailable"},
                              indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"mismatches": [(r["case"], r["method"], r["same_top10_set"]) for r in differences]}))


if __name__ == "__main__":
    main()
