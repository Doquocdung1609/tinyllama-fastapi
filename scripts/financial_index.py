"""Explicit, bounded persistent financial indexing/search CLI; no model downloads."""
import argparse
import json
from pathlib import Path
import sys
from time import perf_counter
import psutil

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import get_settings
from app.financial_index.service import FinancialIndex


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--index-root", type=Path, default=get_settings().financial_index_path)
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build")
    build.add_argument("--dataset", required=True)
    build.add_argument("--sources", type=Path, required=True, help="JSON array of explicit source manifest descriptors")
    build.add_argument("--force-rebuild", action="store_true")
    build.add_argument("--batch-size", type=int, default=8)
    query = sub.add_parser("search")
    query.add_argument("--dataset", required=True)
    query.add_argument("--query", required=True)
    query.add_argument("--mode", choices=["bm25", "dense", "hybrid"], default="hybrid")
    sub.add_parser("status")
    args = parser.parse_args()
    started = perf_counter()
    engine = FinancialIndex(args.index_root)
    try:
        if args.command == "build":
            generation = engine.plan(args.dataset, json.loads(args.sources.read_text("utf-8")), force_rebuild=args.force_rebuild)
            print(json.dumps({"generation": generation, "state": "BUILDING"}), flush=True)
            result = engine.build(args.dataset, generation, batch_size=args.batch_size)
        elif args.command == "search":
            result = engine.search(args.dataset, args.query, args.mode)
        else:
            result = engine.describe()
        if isinstance(result, dict):
            memory = psutil.Process().memory_info()
            result["process_peak_rss_mb"] = getattr(memory, "peak_wset", memory.rss) / 2**20
            result["process_elapsed_ms"] = (perf_counter() - started) * 1000
        print(json.dumps(result, ensure_ascii=True, indent=2), flush=True)
    finally:
        engine.close()


if __name__ == "__main__":
    main()
