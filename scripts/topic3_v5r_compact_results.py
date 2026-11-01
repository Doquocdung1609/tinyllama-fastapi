"""Publish ranked source IDs without copying the frozen SEC corpus into Git."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIVE = ROOT / "tmp/topic3_v5r/live"
OUT = ROOT / "docs/topic3_v5/recovery_live"


def main():
    lines = []
    for dataset in ("p5", "p7l"):
        for index in ("A", "B"):
            path = LIVE / f"{dataset}_{index}.jsonl"
            for raw in path.read_text(encoding="utf-8").splitlines():
                row = json.loads(raw)
                lines.append(json.dumps({
                    "dataset": dataset, "index": index, "case": row["id"],
                    "method": row["method"], "target_accession": row.get("target_accession"),
                    "elapsed_ms": row["elapsed_ms"],
                    "top10": [{"rank": hit["rank"], "chunk_id": hit["chunk_id"],
                               "score": hit["score"], "source_url": hit.get("source_url"),
                               "text_sha256": hashlib.sha256(hit["text"].encode()).hexdigest()}
                              for hit in row["results"]],
                }, ensure_ascii=False, separators=(",", ":")))
    assert len(lines) == 480
    path = OUT / "author_live_top10_compact.jsonl"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"runs": len(lines), "path": str(path),
                      "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}))


if __name__ == "__main__":
    main()
