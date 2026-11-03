"""Create private/public SHA manifests without committing sealed C4 rows."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path


def sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def publish(private_dir: Path, public_dir: Path) -> dict:
    private_out = private_dir / "C4_RUN_MANIFEST.json"
    public_out = public_dir / "C4_PRIVATE_ARTIFACTS_MANIFEST.json"
    if private_out.exists() or public_out.exists():
        raise FileExistsError("C4 immutable manifest already exists")
    required = [
        "C4_JUDGED_ELIGIBILITY.json", "C4_PER_QUERY_ARM_RESULTS.jsonl",
        "C4_RUN_SUMMARY.json", "C4_FAILURE_DIAGNOSIS_PRIVATE.json",
        "C4_PR35_PRODUCT_SMOKE.json", "C4_DEMO_WIN_CASE.txt",
        "C4_DEMO_LOSS_CASE.txt",
    ]
    files = {name: {"sha256": sha(private_dir / name),
                    "bytes": (private_dir / name).stat().st_size}
             for name in required}
    screenshots = sorted((private_dir / "screenshots").glob("*.png"))
    if len(screenshots) != 6:
        raise ValueError("Six actual React screenshots required")
    for path in screenshots:
        files[f"screenshots/{path.name}"] = {
            "sha256": sha(path), "bytes": path.stat().st_size}
    public_inputs = {
        path.name: sha(path) for path in
        (public_dir / "C4_ELIGIBILITY_LOCK_V1.json",
         public_dir / "C4_OBJECTIVE_PROXY_SCORECARD_V1.json",
         public_dir / "C4_QREL_COVERAGE_AT_K_V1.json",
         public_dir / "C4_FAILURE_DIAGNOSIS_V1.json")
    }
    private = {
        "schema": "c4_run_manifest/v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "mode": "SCORE_EXISTING_REAL_G3U_V2_POOL_NO_NEW_G2_QUERIES",
        "research_pr": 36,
        "product_pr": 35,
        "product_commit": "b5c6e1b43e7526bcebd8289fc85b580f4a4c1eef",
        "runtime": {
            "question_count": 94,
            "proxy_eligible": 93,
            "ranked_hit_rows": 31760,
            "observed_arm_runs": 1588,
            "unlogged_zero_or_omitted_runs": 104,
            "original_chunks": 8670,
            "index_A_sha256": "1e8e3c6393e7e59786575ed0228254079639016c7b986d1e9702fa5a3ce32540",
            "index_B_sha256": "fef99bfa5cde1ec358f460efacd3db4ca540673213491c569d64e313070df663",
            "peak_process_rss_mib": 1491.64,
            "gpu_vram": "NOT_MEASURED_CPU_ONNX_PATH",
            "cold_warm": "MIXED_NOT_SEPARATELY_LOGGED",
            "product_pdf_ready": 2,
            "product_sec": "UNAVAILABLE",
        },
        "private_location": str(private_dir.resolve()),
        "private_files": files,
        "public_input_sha256": public_inputs,
        "final_original_chunk_benchmark": "NOT_RUN",
        "human_gold_claim": False,
    }
    private_out.write_text(json.dumps(private, indent=2) + "\n", encoding="utf-8")
    public = {
        "schema": "c4_private_artifacts_manifest/v1",
        "private_location": "OWNER_MACHINE_DOWNLOADS_OUTSIDE_GIT",
        "run_manifest_sha256": sha(private_out),
        "files": files,
        "public_input_sha256": public_inputs,
        "original_private_bytes_in_git": False,
    }
    public_out.write_text(json.dumps(public, indent=2) + "\n", encoding="utf-8")
    return public


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--private-dir", type=Path, required=True)
    p.add_argument("--public-dir", type=Path, required=True)
    r = publish(**vars(p.parse_args()))
    print(json.dumps({"private_files":len(r["files"]),
                      "run_manifest_sha256":r["run_manifest_sha256"]}, indent=2))
