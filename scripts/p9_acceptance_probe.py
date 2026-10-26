"""Frozen engineering acceptance cases on an explicitly supplied research clone.

This is a development-source technical check, not an independent held-out study.
"""
import argparse
import json
from pathlib import Path
from math import ceil
from statistics import median
from time import perf_counter

import psutil

from app.research_qa.backend import ResearchBackend


CASES = (
    ("pg_sales_exact", "What were P&G's net sales for the three months ended September 30, 2026?", {}, "SUPPORTED", ("23276000000",)),
    ("pg_sales_compare", "Compare P&G's net sales for the three months ended September 30, 2025 and the three months ended September 30, 2026.", {}, "SUPPORTED", ("22386000000", "23276000000")),
    ("pg_assets_exact", "What were P&G's total assets as of September 30, 2026?", {}, "SUPPORTED", ("133132000000",)),
    ("pg_assets_compare", "Compare P&G total assets as of June 30, 2026 and as of September 30, 2026.", {}, "SUPPORTED", ("126521000000", "133132000000")),
    ("hd_assets_exact", "What were HD total assets as of August 2, 2026?", {}, "SUPPORTED", ("109384000000",)),
    ("hd_assets_compare", "Compare HD total assets as of February 1, 2026 and as of August 2, 2026.", {}, "SUPPORTED", ("105095000000", "109384000000")),
    ("cost_revenue_duration", "What were COST net sales for the 12 weeks ended May 10, 2026?", {}, "ABSTAIN", ()),
    ("hd_revenue_context", "What were HD net sales for the quarter ended August 2, 2026?", {}, "ABSTAIN", ()),
    ("eps_basic", "What was P&G basic earnings per share for the three months ended September 30, 2026?", {}, "ABSTAIN", ()),
    ("operating_cash_flow", "What was P&G operating cash flow for the three months ended September 30, 2026?", {}, "ABSTAIN", ()),
    ("segment", "What were P&G Beauty segment net sales for the three months ended September 30, 2026?", {}, "ABSTAIN", ()),
    ("fair_value", "What was HD total assets fair value as of August 2, 2026?", {}, "ABSTAIN", ()),
    ("wrong_issuer", "What were Walmart total assets as of August 2, 2026?", {}, "ABSTAIN", ()),
    ("wrong_period", "What were HD total assets as of August 2, 2024?", {}, "ABSTAIN", ()),
    ("conflicting_cik", "What were HD total assets as of August 2, 2026?", {"cik": "0000080424"}, "ABSTAIN", ()),
    ("wrong_unit", "What were HD total assets in thousands as of August 2, 2026?", {}, "ABSTAIN", ()),
    ("dense_unavailable", "What were HD total assets as of August 2, 2026?", {}, "ABSTAIN", ()),
    ("ollama_unavailable", "What were HD total assets as of August 2, 2026?", {}, "ABSTAIN", ()),
)


def percentile(values, fraction):
    ordered = sorted(values)
    return ordered[max(0, min(len(ordered) - 1, ceil(len(ordered) * fraction) - 1))]


def run(root):
    root = root.resolve(strict=True)
    if "p7-isolated-review" not in root.name or not (root / "ownership.json").is_file():
        raise ValueError("EXPLICIT_ISOLATED_RESEARCH_CLONE_REQUIRED")
    process = psutil.Process()
    start = perf_counter()
    backend = ResearchBackend(root)
    startup_ms = (perf_counter() - start) * 1000
    rows = []
    peak_rss = process.memory_info().rss
    for case_id, question, filters, expected, values in CASES:
        arm = "D" if case_id == "dense_unavailable" else "B"
        use_llm = case_id == "ollama_unavailable"
        started = perf_counter()
        try:
            response = backend.query(question, filters, arm, "EXTRACT", 5, use_llm, "automatic_real")
            answer = response.get("answer", {})
            actual = answer.get("status")
            actual_values = tuple(answer.get("result_values", ()))
            cells = answer.get("source_cells", ())
            passed = (actual == "SUPPORTED" and actual_values == values and bool(cells)) if expected == "SUPPORTED" else (actual != "SUPPORTED" and not actual_values)
            row = {"case_id": case_id, "question": question, "filters": filters, "arm": arm,
                   "use_llm": use_llm,
                   "expected": expected, "actual": actual, "result_values": actual_values,
                   "pass": passed, "failure_code": response.get("failure_code"),
                   "trace": response.get("trace", ()), "generation": response.get("generation"),
                   "manifest_hash": response.get("manifest_hash"),
                   "source_cells": cells, "citations": response.get("evidence", ()),
                   "formula": answer.get("formula"), "unit": answer.get("result_unit"),
                   "timings_ms": response.get("timings_ms", {})}
        except (ValueError, RuntimeError) as exc:
            row = {"case_id": case_id, "question": question, "filters": filters,
                   "arm": arm, "use_llm": use_llm, "expected": expected, "actual": "REJECTED_EXCEPTION",
                   "result_values": (), "pass": expected == "ABSTAIN", "error": str(exc)[:200]}
        anchor = next(iter(row.get("source_cells", ())), None)
        rank_token = next((x for x in row.get("trace", ())
                           if x.startswith("SELECTED_ORIGINAL_BM25_RANK_")), None)
        row.update({"issuer_cik": anchor["cik"] if anchor else None,
                    "accession": anchor["accession"] if anchor else None,
                    "source_sha256": anchor["raw_sha256"] if anchor else None,
                    "parent_id": anchor["parent_id"] if anchor else None,
                    "source_locator": anchor["structural_path"] if anchor else None,
                    "original_bm25_rank": int(rank_token.rsplit("_", 1)[-1]) if rank_token else None,
                    "candidate_budget": 64})
        row["wall_ms"] = (perf_counter() - started) * 1000
        peak_rss = max(peak_rss, process.memory_info().rss)
        rows.append(row)
    # Bounded repeated-query probe, disjoint from ranking evaluation.
    repeated = []
    for _ in range(5):
        started = perf_counter()
        response = backend.query(CASES[4][1], {}, "B", "EXTRACT", 5, False, "automatic_real")
        if response["answer"]["status"] != "SUPPORTED":
            raise AssertionError("REPEATED_CONTROL_FAILED")
        repeated.append({"wall_ms": (perf_counter() - started) * 1000,
                         "timings_ms": response.get("timings_ms", {})})
        peak_rss = max(peak_rss, process.memory_info().rss)
    return {"schema_version": "topic3-p9-technical-acceptance/v1",
            "purpose": "engineering_development_sources_not_scientific_heldout",
            "root_label": root.name, "startup_ms": startup_ms,
            "manifest_hash": backend.adapter.freeze["manifest_hash"],
            "generation": backend.adapter.freeze["generation"],
            "candidate_budget": 64, "cases": rows, "repeated_query": repeated,
            "wall_p50_ms": median(x["wall_ms"] for x in rows),
            "wall_p95_ms": percentile([x["wall_ms"] for x in rows], .95),
            "peak_python_rss_bytes": peak_rss,
            "all_pass": all(x["pass"] for x in rows)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"total": len(result["cases"]), "passed": sum(x["pass"] for x in result["cases"]),
                      "all_pass": result["all_pass"], "p50_ms": result["wall_p50_ms"],
                      "p95_ms": result["wall_p95_ms"]}))
    if not result["all_pass"]:
        raise SystemExit(1)
