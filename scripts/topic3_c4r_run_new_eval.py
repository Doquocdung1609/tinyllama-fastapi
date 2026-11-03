"""Execute frozen new questions; this process never opens reference answer fields."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import psutil
import sys
import time

from app.research_retrieval.faith_r_a5 import OriginalChunkSidecarA5, execute_a5, plan_query
from app.research_retrieval.financial_answer_v8 import SourceArchiveAnswererV8

AUTHOR = ("bm25", "dense", "sparse", "bm25_dense", "sparse_dense", "rerank")
A5 = ("A5_BASE", "A5_FALLBACK", "A5_SIDECAR")
METHODS = tuple("AUTHOR_" + x.upper() for x in AUTHOR) + A5


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _hit(r) -> dict:
    return {"chunk_id": r.chunk_id, "ticker": r.ticker,
            "document_type": r.document_type, "fiscal_period": r.fiscal_period,
            "filing_date": r.filing_date, "section": r.section, "score": float(r.score),
            "text": r.text, "source_url": r.source_url,
            "accession_number": r.document_id.split("_")[-1]}


def execute(questions_path: Path, lock_path: Path, split: str, index_b: Path,
            source_manifest: Path, author_root: Path, cache: Path,
            output: Path) -> dict:
    if output.exists():
        raise FileExistsError("Run output exists; no overwrite or hidden rerun")
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    if (lock["schema"] != "c4r_new_evaluation_public_lock/v1" or
            lock["facts"] != 16 or split not in {"DEV", "HOLDOUT", "VN_PAIRED"}):
        raise ValueError("New evaluation lock changed")
    questions = json.loads(questions_path.read_text(encoding="utf-8"))
    if questions["source_private_manifest_sha256"] != lock["private_manifest_sha256"]:
        raise ValueError("Questions do not derive from frozen source manifest")
    selected = [q for q in questions["questions"] if q["split"] == split]
    if len(selected) != (4 if split == "DEV" else 12):
        raise ValueError("Unexpected frozen split denominator")
    if psutil.virtual_memory().available < 2 * 1024**3:
        raise RuntimeError("C4R_LOCAL_RAM_BELOW_2_GIB_USE_COLAB_HANDOFF")
    os.environ.setdefault("FASTEMBED_CACHE_PATH", str(cache.resolve()))
    sys.path.insert(0, str(author_root.resolve() / "src"))
    from hybrid_search.retrieval.engine import SearchEngine
    from qdrant_client import QdrantClient
    client = QdrantClient(path=str(index_b))
    process = psutil.Process()
    records = 0
    peak = process.memory_info().rss
    started = time.perf_counter()
    source_lookup = json.loads(source_manifest.read_text(encoding="utf-8"))
    report_dates = {s["accession"]: s["report_date"] for s in source_lookup["sources"]}
    try:
        if client.count("financial_docs", exact=True).count != 8670:
            raise ValueError("Frozen index B point count changed")
        engine = SearchEngine(client=client)
        sidecar = OriginalChunkSidecarA5(client)
        answerer = SourceArchiveAnswererV8(source_manifest)
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("x", encoding="utf-8", newline="\n") as stream:
            for q in selected:
                plan = plan_query(q["question"])
                for method in METHODS:
                    begin = time.perf_counter()
                    try:
                        if method.startswith("AUTHOR_"):
                            author_method = method.removeprefix("AUTHOR_").lower()
                            found = engine.search(q["question"], method=author_method,
                                                  k=20, prefetch_k=50)
                            hits = [_hit(r) for r in found]
                            attempts = [{"method": author_method, "status":
                                         "COMPLETED_WITH_HITS" if hits else "COMPLETED_EMPTY",
                                         "returned": len(hits), "internal_depth":
                                         60 if author_method == "rerank" else 20}]
                            status = "COMPLETED_WITH_HITS" if hits else "COMPLETED_EMPTY"
                            candidate_ids = [h["chunk_id"] for h in hits]
                            scanned = 0
                        else:
                            a5 = execute_a5(engine, q["question"], budget=20,
                                            report_dates=report_dates,
                                            sidecar=sidecar if method == "A5_SIDECAR" else None,
                                            use_fallback=method != "A5_BASE")
                            hits, attempts, status = a5.hits, a5.attempts, a5.status
                            candidate_ids, scanned = a5.candidate_pool_ids, a5.candidate_scanned
                        answers = {track: answerer.answer(q["question"], hits, track).__dict__
                                   for track in ("ORIGINAL_CHUNK_ONLY", "SOURCE_ENRICHED_V1")}
                        error = None
                    except Exception as exc:
                        hits, candidate_ids, scanned = [], [], 0
                        answers = {}
                        status, error = "ERROR", f"{type(exc).__name__}:{exc}"
                        attempts = [{"method": method, "status": "ERROR", "reason": error}]
                    elapsed = round((time.perf_counter() - begin) * 1000, 3)
                    peak = max(peak, process.memory_info().rss)
                    record = {"schema": "c4r_new_eval_raw_method_output/v1", "run_id":
                              "C4R_NEW_V1_" + split, "split": split,
                              "query_id": q["question_id"], "query_original": q["question"],
                              "method": method, "query_plan": plan.__dict__,
                              "status": status, "attempts": attempts,
                              "candidate_ids_and_ranks": [{"rank": i, "chunk_id": h["chunk_id"],
                                  "accession": h["accession_number"], "source_url": h["source_url"]}
                                  for i, h in enumerate(hits, 1)],
                              "candidate_pool_ids": candidate_ids, "scanned_payloads": scanned,
                              "answers": answers, "error": error, "latency_ms": elapsed,
                              "rss_mb": round(process.memory_info().rss / 1e6, 2),
                              "index_id": "B_P7K_8670_UNMODIFIED",
                              "environment_commit": os.environ.get("C4R_COMMIT", "WORKTREE_PRECOMMIT"),
                              "run_timestamp": datetime.now(timezone.utc).isoformat()}
                    stream.write(json.dumps(record, ensure_ascii=False) + "\n")
                    stream.flush()
                    records += 1
                print(f"{split} {q['question_id']} complete {records}/{len(selected)*len(METHODS)}", flush=True)
        answerer.close()
    finally:
        client.close()
    manifest = {"schema": "c4r_new_eval_run_manifest/v1", "split": split,
                "questions": len(selected), "methods": list(METHODS), "rows": records,
                "questions_only_sha256": sha(questions_path), "public_lock_sha256": sha(lock_path),
                "raw_output_sha256": sha(output), "peak_rss_mb": round(peak / 1e6, 2),
                "wall_seconds": round(time.perf_counter() - started, 2),
                "free_ram_after_gib": round(psutil.virtual_memory().available / 1024**3, 3),
                "gold_fields_read_by_this_runner": False}
    output.with_suffix(".manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("questions_path", "lock_path", "index_b", "source_manifest",
                 "author_root", "cache", "output"):
        p.add_argument("--" + name.replace("_", "-"), required=True, type=Path)
    p.add_argument("--split", required=True, choices=("DEV", "HOLDOUT", "VN_PAIRED"))
    print(json.dumps(execute(**vars(p.parse_args())), indent=2))
