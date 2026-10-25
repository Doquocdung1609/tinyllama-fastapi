"""Controlled stage and provenance-cache benchmark for the frozen issuer corpus."""
from __future__ import annotations

import argparse
from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path
from statistics import mean, median
from time import perf_counter

from app.financial_index.corpus import ProvenanceCache
from app.financial_index.service import FinancialIndex
from app.services.financial_search_service import reciprocal_rank_fusion


FROZEN_QUERY_SHA256 = "c8aedd619f362208fcb097c197f351b117aaa7e2c3bfd758ef97c56df842792a"


def distribution(values: list[float]) -> dict:
    ordered = sorted(values)
    return {"n": len(values), "mean_ms": mean(values), "p50_ms": median(values),
            "p95_ms": ordered[max(0, (95 * len(values) + 99) // 100 - 1)]}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queries", type=Path, required=True)
    parser.add_argument("--index-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    raw = args.queries.read_bytes()
    if sha256(raw).hexdigest() != FROZEN_QUERY_SHA256:
        raise SystemExit("Frozen query definition changed")
    definition = json.loads(raw)
    split = definition["splits"]["held_out"]
    cases = [case for case in definition["cases"] if case["split"] == "held_out"][:6]
    output = {"query_file_sha256": FROZEN_QUERY_SHA256, "cases": [case["id"] for case in cases],
              "generation": split["generation"], "runs": {}}

    for cache_name, cache in (("disabled", ProvenanceCache(0, 0)),
                              ("generation_bound_lru", ProvenanceCache(8, 128 * 1024 * 1024))):
        index = FinancialIndex(args.index_root)
        index.provenance_cache = cache
        stage = {key: [] for key in ("normalization", "metadata_filter", "bm25", "identity",
                                      "embedding", "qdrant", "rrf", "provenance", "serialization", "total")}
        try:
            if cache_name != "disabled":
                for ticker in ("NVDA", "WMT"):
                    warm = next(case for case in definition["cases"]
                                if case["split"] == "held_out" and case["filters"]["ticker"] == ticker)
                    index.search(split["dataset_id"], warm["query"], "bm25", generation=split["generation"],
                                 top_k=5, candidate_limit=40, filters=warm["filters"])
            for case in cases:
                t = perf_counter(); case["query"].strip(); stage["normalization"].append((perf_counter() - t) * 1000)
                record = index.lexical.generation(split["dataset_id"], split["generation"])
                where, params = index.lexical.scope(split["generation"], case["filters"])
                t = perf_counter()
                with closing(index.lexical.connect()) as connection:
                    connection.execute("SELECT COUNT(*) FROM members m JOIN documents d ON d.cid=m.cid WHERE " + where,
                                       params).fetchone()
                stage["metadata_filter"].append((perf_counter() - t) * 1000)
                t = perf_counter(); lexical = index.lexical.search(case["query"], record, 40, case["filters"])
                stage["bm25"].append((perf_counter() - t) * 1000)
                t = perf_counter(); index.provider.identity()
                stage["identity"].append((perf_counter() - t) * 1000)
                t = perf_counter(); index.provider.embed_query(case["query"])
                stage["embedding"].append((perf_counter() - t) * 1000)
                for mode in ("bm25", "dense", "hybrid"):
                    response = index.search(split["dataset_id"], case["query"], mode,
                                            generation=split["generation"], top_k=5,
                                            candidate_limit=40, filters=case["filters"])
                    timing = response["timings_ms"]
                    stage["qdrant"].append(timing["dense"])
                    stage["provenance"].append(timing["provenance"])
                    stage["total"].append(timing["total"])
                    t = perf_counter(); json.dumps(response, ensure_ascii=False); stage["serialization"].append((perf_counter() - t) * 1000)
                dense = [{"chunk_id": f"d{i}", "dense_score": 1 - i / 100} for i in range(40)]
                t = perf_counter()
                for _ in range(1000): reciprocal_rank_fusion(lexical[:40], dense)
                stage["rrf"].append((perf_counter() - t) * 1000 / 1000)
            output["runs"][cache_name] = {key: distribution(values) for key, values in stage.items()}
            output["runs"][cache_name]["cache_diagnostics"] = cache.diagnostics()
            output["runs"][cache_name]["note"] = (
                "Identity and embedding are independently probed immediately before service searches; "
                "service total also includes its own identity lookup and embedding for dense/hybrid.")
        finally:
            index.close()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
