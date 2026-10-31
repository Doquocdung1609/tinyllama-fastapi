"""Embed frozen provisional queries with one genuine author model per process."""

from __future__ import annotations

import argparse
import hashlib
import json
import threading
import time
from pathlib import Path

import psutil
from hybrid_search.embeddings.bm25 import BM25EmbeddingGenerator
from hybrid_search.embeddings.dense import DenseEmbeddingGenerator
from hybrid_search.embeddings.sparse import SpladeEmbeddingGenerator


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "docs/topic3/01_REPRODUCTION"
WORK = ROOT / "tmp/topic3/replication"
MODELS = {
    "bm25": (BM25EmbeddingGenerator, "Qdrant/bm25"),
    "dense": (DenseEmbeddingGenerator, "BAAI/bge-small-en-v1.5"),
    "splade": (SpladeEmbeddingGenerator, "prithivida/Splade_PP_en_v1"),
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("arm", choices=sorted(MODELS))
    arm = parser.parse_args().arm
    qrels = DATA / "PROVISIONAL_SOURCE_QRELS.jsonl"
    queries = [json.loads(line) for line in qrels.read_text(encoding="utf-8").splitlines()]
    output = WORK / f"{arm}_query_vectors.jsonl"
    manifest = WORK / f"{arm}_query_manifest.json"
    if output.exists() or manifest.exists():
        raise SystemExit("EXISTING_QUERY_CHECKPOINT_REFUSED")
    available = psutil.virtual_memory().available
    threshold = 4 * 1024**3 if arm == "splade" else 1024**3
    if available < threshold:
        raise SystemExit("QUERY_MODEL_LOW_MEMORY_DEFERRED")
    samples = []
    done = threading.Event()
    proc = psutil.Process()

    def monitor() -> None:
        while not done.is_set():
            samples.append((proc.memory_info().rss, psutil.virtual_memory().available))
            done.wait(0.25)

    watch = threading.Thread(target=monitor, daemon=True)
    watch.start()
    start = time.perf_counter()
    error = None
    latencies = []
    try:
        cls, model = MODELS[arm]
        generator = cls(model_name=model, batch_size=1, threads=1)
        with output.open("w", encoding="utf-8", newline="\n") as stream:
            for q in queries:
                t = time.perf_counter()
                vector = generator.embed_query(q["query"])
                elapsed = round((time.perf_counter() - t) * 1000, 2)
                latencies.append(elapsed)
                if arm == "dense":
                    if len(vector) != 384:
                        raise ValueError("DENSE_QUERY_DIMENSION_MISMATCH")
                    record = {"id": q["id"], "vector": vector}
                else:
                    indices, values = vector
                    if len(indices) != len(values):
                        raise ValueError("SPARSE_QUERY_VECTOR_MISMATCH")
                    record = {"id": q["id"], "indices": indices, "values": values}
                stream.write(json.dumps(record, separators=(",", ":")) + "\n")
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        if output.exists():
            output.unlink()
    finally:
        done.set()
        watch.join()
        result = {
            "status": "PASS" if error is None else "FAIL",
            "arm": arm,
            "model": MODELS[arm][1],
            "qrels_sha256": sha(qrels),
            "query_count": len(queries) if error is None else 0,
            "query_vectors_sha256": sha(output) if output.exists() else None,
            "per_query_embed_ms": latencies,
            "total_elapsed_s": round(time.perf_counter() - start, 3),
            "peak_process_rss_mib": round(max(x[0] for x in samples) / 1048576, 2),
            "minimum_available_ram_mib": round(min(x[1] for x in samples) / 1048576, 2),
            "threads": 1,
            "error": error,
        }
        manifest.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(result))
    if error:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
