"""Package immutable local P9 measurements; GitHub CI is reported separately."""
import json
import platform
from pathlib import Path
import shutil
from statistics import median

import psutil


ROOT = Path("docs/topic3/milestone_d/recovery/p9")


def read(name):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def save(name, value):
    (ROOT / name).write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def run():
    acceptance, live = read("p9_acceptance_matrix.json"), read("p9_live_results.json")
    browser, tamper = read("p9_browser_results.json"), read("p9_tamper_results.json")
    http_tamper, semantic = read("p9_http_tamper_results.json"), read("p9_semantic_results.json")
    concurrency = read("p9_concurrency_results.json")
    passed = sum(x["pass"] for x in acceptance["cases"])
    positive = [x for x in acceptance["cases"] if x["expected"] == "SUPPORTED"]
    negative = [x for x in acceptance["cases"] if x["expected"] == "ABSTAIN"]
    repeated = acceptance["repeated_query"]
    disk = shutil.disk_usage(Path.cwd().anchor)
    resources = {"schema_version": "topic3-p9-resources/v1", "os": platform.platform(),
                 "python": platform.python_version(), "local_total_ram_bytes": psutil.virtual_memory().total,
                 "local_available_ram_bytes_at_packaging": psutil.virtual_memory().available,
                 "disk_free_bytes_at_packaging": disk.free,
                 "research_clone_peak_python_rss_bytes": acceptance["peak_python_rss_bytes"],
                 "backend_initialization_ms": acceptance["startup_ms"],
                 "api_cold_start_ms": live["api_startup_ms"],
                 "streamlit_cold_start_ms": live["streamlit_startup_ms"],
                 "api_restart_ms": live["api_restart_ms"],
                 "positive_development_wall_ms": [x["wall_ms"] for x in positive],
                 "warm_repeated_hd_wall_ms": [x["wall_ms"] for x in repeated],
                 "warm_repeated_hd_p50_ms": median(x["wall_ms"] for x in repeated),
                 "warm_repeated_hd_p95_nearest_ms": max(x["wall_ms"] for x in repeated),
                 "warm_stage_median_ms": {key: median(x["timings_ms"][key] for x in repeated)
                                          for key in repeated[0]["timings_ms"]},
                 "measurement_limit": "Five repeated HD queries; mixed positive-case timings are not a stable latency distribution."}
    tests = {"schema_version": "topic3-p9-tests/v1", "candidate_commit": "aa78c1a5f5bdee0d1ac578c799e6cddca2d04045",
             "candidate_tree": "d1d69269d4de4c97db9f429ba74031b8e43967f9",
             "python": platform.python_version(),
             "compileall": "PASS", "focused": {"passed": 20},
             "full": {"passed": 575, "skipped": 3, "warnings": 1, "seconds": 33.48},
             "non_integration": {"passed": 575, "deselected": 3, "warnings": 1, "seconds": 108.25},
             "technical_cases": {"total": len(acceptance["cases"]), "passed": passed,
                                  "positive": len(positive), "negative": len(negative)},
             "tamper_cases_refused": len(tamper["cases"]),
             "http_tamper": http_tamper["tampered_raw"],
             "semantic_percentage_points": next(x for x in semantic["cases"] if x["case_id"] == "percentage_points"),
             "http_invalid_generation": live["invalid_generation_http"],
             "parallel_publication_reads": concurrency["queries_during_publication"],
             "mixed_generation_claims": concurrency["mixed_generation_claims"],
             "browser": browser, "github_final_head_ci": "CHECK_AFTER_DRAFT_PR_PUSH",
             "environment_note": "System Python lacked portalocker; configured repository venv used without code changes."}
    manifest = {"schema_version": "topic3-p9-execution/v1",
                "authorization": "TOPIC3_P9_RELEASE_CANDIDATE_AND_SCIENTIFIC_READINESS_AUTHORIZED",
                "accepted_target": "32c4a4834c5f8a0b34ac28c42f960c862dd8077d",
                "p8_base": "468ddf6ca3f40edbd342b444a088cadc801b40c4",
                "local_candidate": tests["candidate_commit"], "candidate_tree": tests["candidate_tree"],
                "source_clone": acceptance["root_label"],
                "manifest_hash": acceptance["manifest_hash"], "generation": acceptance["generation"],
                "candidate_budget": acceptance["candidate_budget"],
                "historical_heldout_used": False, "new_sec_download": False,
                "owner_source_or_qdrant_mutated": False, "production_default_changed": False,
                "merge_authorized": False, "final_pr_head": "SET_BY_GIT_COMMIT_AND_PR_METADATA"}
    gates = {"schema_version": "topic3-p9-gates/v1", "checkpoint": "local technical RC before final-head CI",
             "stack_ancestry": "VERIFIED", "candidate_tree": "VERIFIED",
             "source_authenticated_positive_controls": "VERIFIED_6_OF_6_DEVELOPMENT",
             "safety_negative_controls": "VERIFIED_WITH_LIMITATIONS",
             "full_regression": "VERIFIED_575_PASS_3_SKIP",
             "live_http": "VERIFIED", "live_ui": "VERIFIED_WITH_LIMITATIONS",
             "source_tamper": "VERIFIED_12_OF_12_CLONE",
             "concurrent_pinned_reads": "VERIFIED_12_READS_ZERO_MIXED_GENERATIONS",
             "historical_artifacts": "VERIFIED_TRACKED_BLOBS",
             "final_head_ci": "PENDING_PR", "draft_pr": "PENDING_PR",
             "dense_compatible_execution": "BLOCKED", "new_human_labels": "NOT_AVAILABLE",
             "scientific_heldout": "NOT_RUN"}
    save("p9_resource_measurements.json", resources)
    save("p9_test_results.json", tests)
    save("p9_execution_manifest.json", manifest)
    save("p9_gate_ledger.json", gates)
    return {"technical_cases_passed": passed, "tamper_cases": len(tamper["cases"])}


if __name__ == "__main__":
    print(json.dumps(run()))
