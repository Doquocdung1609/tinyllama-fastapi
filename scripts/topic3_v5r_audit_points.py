"""Audit all restored Qdrant points and compare immutable A/B content."""

from __future__ import annotations

import hashlib
import json
import math
import zipfile
from collections import Counter
from pathlib import Path

from qdrant_client import QdrantClient

from topic3_v5r_restore import REPO, SOURCE, WORK


OUT = REPO / "docs/topic3_v5/recovery_live"
SIGNATURES = REPO / "tmp/topic3_v5r/signatures"
COLLECTION = "financial_docs"


def sha(obj: object) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def frozen() -> dict:
    with zipfile.ZipFile(SOURCE) as z:
        return {row["chunk_id"]: row for row in (json.loads(line) for line in z.read("corpus/chunks_frozen.jsonl").splitlines())}


def scan(arm: str, reference: dict) -> dict:
    SIGNATURES.mkdir(parents=True, exist_ok=True)
    counts = Counter()
    errors = []
    seen_ids = set()
    seen_chunks = set()
    client = QdrantClient(path=str(WORK / arm))
    try:
        info = client.get_collection(COLLECTION)
        if info.config.params.vectors["dense"].size != 384 or info.config.params.vectors["dense"].distance.value != "Cosine":
            errors.append("DENSE_SCHEMA")
        for name in ("bm25", "sparse"):
            if info.config.params.sparse_vectors[name].modifier.value != "idf":
                errors.append(f"SPARSE_IDF_SCHEMA:{name}")
        with (SIGNATURES / f"{arm}.jsonl").open("w", encoding="utf-8") as out:
            offset = None
            while True:
                batch, offset = client.scroll(COLLECTION, offset=offset, limit=64, with_payload=True, with_vectors=True)
                for point in batch:
                    counts["points"] += 1
                    cid = point.payload.get("chunk_id")
                    if point.id in seen_ids or cid in seen_chunks:
                        errors.append(f"DUPLICATE:{point.id}:{cid}")
                    seen_ids.add(point.id)
                    seen_chunks.add(cid)
                    original = reference.get(cid)
                    if original is None:
                        errors.append(f"UNKNOWN_CHUNK:{cid}")
                    vector = point.vector or {}
                    dense = vector.get("dense")
                    if not isinstance(dense, list) or len(dense) != 384 or not all(math.isfinite(x) for x in dense):
                        errors.append(f"BAD_DENSE:{cid}")
                    hashes = {"dense": sha(dense)}
                    for name in ("bm25", "sparse"):
                        sparse = vector.get(name)
                        if sparse is None or not sparse.indices or len(sparse.indices) != len(sparse.values) or len(set(sparse.indices)) != len(sparse.indices) or not all(math.isfinite(x) for x in sparse.values):
                            errors.append(f"BAD_{name.upper()}:{cid}")
                        else:
                            counts[f"{name}_nonempty"] += 1
                        hashes[name] = sha({"indices": sparse.indices, "values": sparse.values}) if sparse else None
                    payload = point.payload
                    if original:
                        for key in ("chunk_id", "document_id", "company", "ticker", "cik", "document_type", "filing_date", "section", "sector", "geography", "text", "text_hash", "chunk_index", "source_url", "accession_number"):
                            if payload.get(key) != original.get(key):
                                errors.append(f"CORPUS_PAYLOAD:{cid}:{key}")
                        if arm == "A" and payload.get("fiscal_period") != original.get("fiscal_period"):
                            errors.append(f"CORPUS_FISCAL:{cid}")
                    if payload.get("accession_number") not in cid:
                        errors.append(f"ACCESSION_ID:{cid}")
                    if hashlib.sha256(payload.get("text", "").encode()).hexdigest() != payload.get("text_hash"):
                        errors.append(f"TEXT_HASH:{cid}")
                    row = {"point_id": point.id, "chunk_id": cid, "accession": payload.get("accession_number"),
                           "payload_sha256": sha(payload), "text_sha256": sha(payload.get("text")),
                           "fiscal_period": payload.get("fiscal_period"), "vectors_sha256": hashes,
                           "payload": payload}
                    out.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
                if offset is None:
                    break
        missing = set(reference) - seen_chunks
        if missing:
            errors.append(f"MISSING_CHUNKS:{len(missing)}")
        return {"arm": arm, "points": counts["points"], "bm25_nonempty": counts["bm25_nonempty"],
                "sparse_nonempty": counts["sparse_nonempty"], "unique_point_ids": len(seen_ids),
                "unique_chunk_ids": len(seen_chunks), "errors_count": len(errors), "errors_sample": errors[:30],
                "signature_path": str(SIGNATURES / f"{arm}.jsonl")}
    finally:
        client.close()


def compare() -> dict:
    def rows(arm: str) -> dict:
        return {r["point_id"]: r for r in (json.loads(line) for line in (SIGNATURES / f"{arm}.jsonl").read_text(encoding="utf-8").splitlines())}
    a, b = rows("A"), rows("B")
    changed = Counter()
    accessions = Counter()
    with (OUT / "point_diff.jsonl").open("w", encoding="utf-8") as out:
        for pid in sorted(set(a) | set(b)):
            left, right = a.get(pid), b.get(pid)
            if not left or not right:
                changed["point_set"] += 1
                continue
            keys = sorted(k for k in set(left["payload"]) | set(right["payload"]) if left["payload"].get(k) != right["payload"].get(k))
            vector_equal = {name: left["vectors_sha256"][name] == right["vectors_sha256"][name] for name in ("dense", "bm25", "sparse")}
            if keys:
                accessions[left["accession"]] += 1
                for key in keys:
                    changed[f"payload:{key}"] += 1
            for name, equal in vector_equal.items():
                if not equal:
                    changed[f"vector:{name}"] += 1
            if left["chunk_id"] != right["chunk_id"]:
                changed["chunk_id"] += 1
            out.write(json.dumps({"point_id": pid, "chunk_id": left["chunk_id"], "accession": left["accession"],
                                  "changed_payload_keys": keys, "vector_equal": vector_equal,
                                  "a_fiscal": left["fiscal_period"], "b_fiscal": right["fiscal_period"]}, separators=(",", ":")) + "\n")
    return {"point_sets_equal": set(a) == set(b), "changed_counts": dict(changed),
            "changed_accessions": dict(accessions), "point_diff_sha256": hashlib.sha256((OUT / "point_diff.jsonl").read_bytes()).hexdigest()}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    reference = frozen()
    result = {"frozen_chunks": len(reference), "arms": {}}
    for arm in ("A", "B"):
        result["arms"][arm] = scan(arm, reference)
        print(arm, result["arms"][arm], flush=True)
    result["comparison"] = compare()
    (OUT / "full_point_audit.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result["comparison"], indent=2))


if __name__ == "__main__":
    main()
