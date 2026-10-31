"""Sequential author-model embeddings for the locked 121-chunk SEC corpus.

Use the isolated author virtualenv. Invoke once per arm to release each model
before loading the next. Outputs are checkpoints, never substituted vectors.
"""

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
OUT = ROOT / "tmp/topic3/replication"
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
    args = parser.parse_args()
    manifest = json.loads((DATA / "CORPUS_MANIFEST.json").read_text(encoding="utf-8"))
    chunks_path = DATA / "author_chunks.jsonl"
    if sha(chunks_path) != manifest["chunks_sha256"]:
        raise SystemExit("CORPUS_HASH_CHANGED")
    chunks = [json.loads(line) for line in chunks_path.read_text(encoding="utf-8").splitlines()]
    if len(chunks) != manifest["chunk_count"]:
        raise SystemExit("CHUNK_COUNT_CHANGED")
    if psutil.virtual_memory().available < 1024 * 1024**2:
        raise SystemExit("INSUFFICIENT_RAM_FOR_AUTHOR_MODEL")
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{args.arm}_vectors.jsonl"
    report = OUT / f"{args.arm}_embed_manifest.json"
    if path.exists() or report.exists():
        raise SystemExit("EXISTING_EMBED_CHECKPOINT_REFUSED")
    samples = []
    done = threading.Event()
    proc = psutil.Process()

    def monitor() -> None:
        while not done.is_set():
            samples.append((proc.memory_info().rss, psutil.virtual_memory().available))
            done.wait(0.25)

    watch = threading.Thread(target=monitor, daemon=True)
    watch.start()
    started = time.perf_counter()
    error = None
    try:
        cls, name = MODELS[args.arm]
        generator = cls(model_name=name, batch_size=16, threads=4)
        vectors = generator.embed_texts([chunk["text"] for chunk in chunks])
        if len(vectors) != len(chunks):
            raise ValueError("EMBED_COUNT_MISMATCH")
        with path.open("w", encoding="utf-8", newline="\n") as stream:
            for chunk, vector in zip(chunks, vectors, strict=True):
                if args.arm == "dense":
                    if len(vector) != 384:
                        raise ValueError("DENSE_DIMENSION_MISMATCH")
                    row = {"chunk_id": chunk["chunk_id"], "dense": vector}
                else:
                    indices, values = vector
                    if len(indices) != len(values):
                        raise ValueError("SPARSE_VECTOR_MISMATCH")
                    row = {"chunk_id": chunk["chunk_id"], "indices": indices, "values": values}
                stream.write(json.dumps(row, separators=(",", ":")) + "\n")
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        if path.exists():
            path.unlink()
    finally:
        done.set()
        watch.join()
        result = {
            "status": "PASS" if error is None else "FAIL",
            "arm": args.arm,
            "model": MODELS[args.arm][1],
            "author_commit": manifest["author_commit"],
            "corpus_sha256": manifest["chunks_sha256"],
            "count": len(chunks) if error is None else 0,
            "vectors_sha256": sha(path) if path.exists() else None,
            "elapsed_s": round(time.perf_counter() - started, 3),
            "peak_process_rss_mib": round(max(x[0] for x in samples) / 1048576, 2),
            "minimum_available_ram_mib": round(min(x[1] for x in samples) / 1048576, 2),
            "batch_size": 16,
            "threads": 4,
            "error": error,
        }
        report.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(result))
    if error:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
