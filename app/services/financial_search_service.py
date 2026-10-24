"""Auditable BM25, dense, RRF and optional local Cross-Encoder for financial documents.

Retrieval only. Never send benchmark answer keys or oracle labels to this service.
"""
from __future__ import annotations
from collections import Counter
from functools import lru_cache
from hashlib import sha256
import json
from math import log
import os
from pathlib import Path
import re
from time import perf_counter
from typing import Any
import unicodedata

from app.services import qdrant_service, rag_service
from app.config import get_settings
from app.services.embedding_service import get_embedding_provider


def _numeric_tokens(value: str) -> list[str]:
    """Return locale-tolerant aliases without guessing a financial value."""
    aliases = []
    if "," in value and "." in value:
        canonical = (value.replace(",", "") if value.rfind(".") > value.rfind(",")
                     else value.replace(".", "").replace(",", "."))
    elif "," in value:
        parts = value.split(",")
        canonical = ("".join(parts) if len(parts) > 1 and
                     all(len(part) == 3 for part in parts[1:])
                     else value.replace(",", "."))
    elif "." in value:
        parts = value.split(".")
        canonical = ("".join(parts) if len(parts) > 2 and
                     all(len(part) == 3 for part in parts[1:]) else value)
        # A single three-digit dot is ambiguous (decimal vs thousands), so
        # retain both representations instead of silently changing the value.
        if len(parts) == 2 and len(parts[1]) == 3:
            aliases.append("".join(parts))
    else:
        canonical = value
    return list(dict.fromkeys([canonical, *aliases]))


def tokenize(text: str) -> list[str]:
    normalized = unicodedata.normalize("NFKC", text).casefold()
    tokens = []
    for value in re.findall(r"(?u)\d+(?:[.,]\d+)*|[^\W\d_]+|_+", normalized):
        tokens.extend(_numeric_tokens(value) if value[0].isdigit() else [value])
    return tokens


def bm25_rank(query: str, chunks: list[dict], top_n: int, k1: float = 1.5,
              b: float = .75) -> list[dict]:
    """Okapi BM25, positive IDF. Unmatched queries return zero hits, not arbitrary rows."""
    terms = set(tokenize(query))
    if not terms or not chunks:
        return []
    docs = [Counter(tokenize(str(chunk.get("text") or ""))) for chunk in chunks]
    n = len(docs)
    df = Counter(term for doc in docs for term in doc if term in terms)
    lengths = [sum(doc.values()) for doc in docs]
    avg_len = max(1., sum(lengths) / n)
    idf = {term: log(1. + (n - df[term] + .5) / (df[term] + .5))
           for term in terms if df[term]}
    matches = []
    for i, doc in enumerate(docs):
        document_length_normalizer = k1 * (1. - b + b * lengths[i] / avg_len)
        score = sum(idf[t] * (doc[t] * (k1 + 1.) /
                    (doc[t] + document_length_normalizer)) for t in idf if doc[t])
        if score > 0:
            matches.append({"chunk_id": chunks[i]["chunk_id"], "bm25_score": score})
    matches.sort(key=lambda row: (-row["bm25_score"], row["chunk_id"]))
    for rank, item in enumerate(matches[:top_n], 1):
        item["bm25_rank"] = rank
    return matches[:top_n]


def reciprocal_rank_fusion(bm25_hits: list[dict], dense_hits: list[dict],
                           k: int = 60) -> list[dict]:
    """Combine positions, not incomparable raw BM25 and cosine similarities."""
    if k < 1:
        raise ValueError("RRF k must be positive")
    merged = {}
    for channel, hits in (("bm25", bm25_hits), ("dense", dense_hits)):
        seen = set()
        for rank, hit in enumerate(hits, 1):
            cid = hit["chunk_id"]
            if cid in seen:
                continue
            seen.add(cid)
            row = merged.setdefault(cid, {"chunk_id": cid, "bm25_score": None,
                                          "dense_score": None, "bm25_rank": None,
                                          "dense_rank": None, "rrf_score": 0.})
            row[channel + "_rank"] = rank
            row[channel + "_score"] = hit[channel + "_score"]
            row["rrf_score"] += 1. / (k + rank)
    return sorted(merged.values(), key=lambda row: (-row["rrf_score"], row["chunk_id"]))


def _metadata(chunk: dict) -> dict:
    return chunk.get("metadata") if isinstance(chunk.get("metadata"), dict) else {}


def _matches_metadata(chunk: dict, filters: dict[str, Any]) -> bool:
    metadata = _metadata(chunk)
    for key, expected in filters.items():
        if expected is None or expected == "":
            continue
        value = metadata.get(key, chunk.get(key))
        if value is None or str(value).casefold() != str(expected).casefold():
            return False
    return True


def _dense_prefilter_values(chunks: list[dict], filters: dict[str, Any]) -> dict[str, Any]:
    """Map case-insensitive API filters back to exact values stored in Qdrant."""
    result = {}
    for key, expected in filters.items():
        values = []
        for chunk in chunks:
            value = _metadata(chunk).get(key, chunk.get(key))
            if value is not None and str(value).casefold() == str(expected).casefold() \
                    and value not in values:
                values.append(value)
        if values:
            result[key] = values[0] if len(values) == 1 else values
    return result


def corpus_snapshot(chunks: list[dict]) -> str:
    """Hash retrieval-visible content so benchmark methods can prove corpus parity."""
    digest = sha256()
    for chunk in sorted(chunks, key=lambda item: item["chunk_id"]):
        record = {
            "chunk_id": chunk["chunk_id"],
            "document_id": chunk.get("document_id"),
            "text": chunk.get("text", ""),
            "metadata": _metadata(chunk),
        }
        digest.update(json.dumps(record, ensure_ascii=False, sort_keys=True,
                                 separators=(",", ":")).encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()


@lru_cache(maxsize=1)
def _cross_encoder():
    model_path = os.getenv("FINANCIAL_RERANKER_PATH", "").strip()
    if not model_path or not Path(model_path).is_dir():
        raise RuntimeError("Cross-Encoder unavailable: set FINANCIAL_RERANKER_PATH to an existing local model directory")
    try:
        from sentence_transformers import CrossEncoder
    except ImportError as exc:
        raise RuntimeError("Install optional sentence-transformers to use Cross-Encoder") from exc
    # Inexpensive CPU inference on the 4GB-VRAM development machine.
    return CrossEncoder(model_path, device="cpu", max_length=512, local_files_only=True)


def cross_encoder_rerank(query: str, hits: list[dict], encoder=None) -> list[dict]:
    if not hits:
        return []
    model = encoder if encoder is not None else _cross_encoder()
    scores = model.predict([(query, hit.get("text", "")) for hit in hits],
                           batch_size=8, show_progress_bar=False)
    if len(scores) != len(hits):
        raise RuntimeError("Cross-Encoder returned unexpected score count")
    rescored = [{**hit, "rerank_score": float(score)}
                for hit, score in zip(hits, scores)]
    return sorted(rescored, key=lambda row: (-row["rerank_score"], row["chunk_id"]))


def _present(hit: dict, rank: int) -> dict:
    return {"rank": rank, "chunk_id": hit["chunk_id"],
            "document_id": hit.get("document_id"), "filename": hit.get("filename"),
            "page": hit.get("page"), "source_id": hit.get("source_id"),
            "modality": hit.get("modality"), "bbox": hit.get("bbox"),
            "text": hit.get("text", ""), "metadata": _metadata(hit),
            "bm25_score": hit.get("bm25_score"), "bm25_rank": hit.get("bm25_rank"),
            "dense_score": hit.get("dense_score"), "dense_rank": hit.get("dense_rank"),
            "rrf_score": hit.get("rrf_score"), "rerank_score": hit.get("rerank_score")}


def search(question: str, document_ids: list[str], method: str = "hybrid",
           top_k: int = 5, candidate_limit: int = 40,
           filters: dict[str, Any] | None = None) -> dict:
    """Explicit document scope only. Never accepts labels or ground-truth answers."""
    if method not in {"bm25", "dense", "hybrid", "hybrid_rerank"}:
        raise ValueError("Unknown method")
    question = question.strip()
    if not question:
        raise ValueError("Query must contain non-whitespace text")
    if not document_ids:
        raise ValueError("Explicit document_ids are required; no global search")
    if not 1 <= top_k <= candidate_limit <= 100:
        raise ValueError("Require 1 <= top_k <= candidate_limit <= 100")
    started = perf_counter()
    reranker_load_started = perf_counter()
    encoder = _cross_encoder() if method == "hybrid_rerank" else None
    reranker_load_ms = round((perf_counter() - reranker_load_started) * 1000, 2)
    corpus_started = perf_counter()
    if any(not isinstance(document_id, str) or not document_id.strip()
           for document_id in document_ids):
        raise ValueError("Every document_id must contain non-whitespace text")
    scope = sorted({document_id.strip() for document_id in document_ids})
    corpus = [chunk for chunk in rag_service.chunks_for(scope)
              if chunk.get("chunk_id") and chunk.get("document_id") in scope]
    if not corpus:
        raise ValueError("No indexed chunks found in the selected document scope")
    requested_filters = filters or {}
    unavailable_fields = sorted(
        key for key, expected in requested_filters.items()
        if expected is not None and not any(
            _metadata(chunk).get(key, chunk.get(key)) is not None for chunk in corpus))
    if unavailable_fields:
        raise ValueError("Metadata unavailable for selected document scope: " +
                         ",".join(unavailable_fields))
    eligible = [chunk for chunk in corpus if _matches_metadata(chunk, requested_filters)]
    by_id = {chunk["chunk_id"]: chunk for chunk in eligible}
    snapshot = corpus_snapshot(eligible)
    corpus_prepare_ms = round((perf_counter() - corpus_started) * 1000, 2)
    lex_started = perf_counter()
    lexical = bm25_rank(question, eligible, candidate_limit) if method != "dense" else []
    lexical_ms = round((perf_counter() - lex_started) * 1000, 2)
    dense = []
    embedding_ms = 0.
    dense_ms = 0.
    if method != "bm25" and eligible:
        embed_started = perf_counter()
        vector = get_embedding_provider().embed([question])[0]
        embedding_ms = round((perf_counter() - embed_started) * 1000, 2)
        dense_started = perf_counter()
        # Qdrant performs both document scoping and metadata prefiltering.  The
        # local ID guard remains a fail-closed consistency check.
        points = qdrant_service.search(vector, min(candidate_limit * 4, 400), scope,
                                        _dense_prefilter_values(eligible, requested_filters) or None)
        for point in points:
            cid = (point.payload or {}).get("chunk_id")
            if cid in by_id:
                dense.append({"chunk_id": cid, "dense_score": float(point.score)})
                if len(dense) >= candidate_limit:
                    break
        dense_ms = round((perf_counter() - dense_started) * 1000, 2)
    fuse_started = perf_counter()
    if method == "bm25":
        ranks = [{**h, "dense_score": None, "dense_rank": None, "rrf_score": None}
                 for h in lexical]
    elif method == "dense":
        ranks = [{**h, "bm25_score": None, "bm25_rank": None,
                  "dense_rank": index + 1, "rrf_score": None}
                 for index, h in enumerate(dense)]
    else:
        ranks = reciprocal_rank_fusion(lexical, dense)
    fusion_ms = round((perf_counter() - fuse_started) * 1000, 2)
    candidates = [{**by_id[h["chunk_id"]], **h} for h in ranks]
    rerank_started = perf_counter()
    if method == "hybrid_rerank":
        candidates = cross_encoder_rerank(question, candidates[:candidate_limit], encoder)
    rerank_ms = round((perf_counter() - rerank_started) * 1000, 2)
    settings = get_settings()
    return {"method": method, "query": question, "scope_document_ids": scope,
            "filters": filters or {}, "corpus_size": len(corpus),
            "eligible_chunks": len(eligible), "candidate_count": len(candidates),
            "corpus_snapshot_sha256": snapshot,
            "results": [_present(hit, rank) for rank, hit in enumerate(candidates[:top_k], 1)],
            "timings_ms": {"corpus_prepare": corpus_prepare_ms,
                           "lexical": lexical_ms, "embedding": embedding_ms,
                           "dense": dense_ms, "fusion": fusion_ms,
                           "reranker_load": reranker_load_ms,
                           "cross_encoder": rerank_ms,
                           "total": round((perf_counter() - started) * 1000, 2)},
            "provenance": {
                "lexical": {"algorithm": "okapi_bm25", "k1": 1.5, "b": .75,
                            "persistent": False, "build": "per_request"},
                "dense": {"collection": settings.qdrant_collection,
                          "embedding_provider": settings.embedding_provider,
                          "embedding_model": settings.embedding_model,
                          "metadata_prefilter": True},
                "fusion": {"algorithm": "rrf", "k": 60} if method.startswith("hybrid") else None,
                "reranker": {"enabled": method == "hybrid_rerank",
                             "path": os.getenv("FINANCIAL_RERANKER_PATH", "") or None,
                             "device": "cpu" if method == "hybrid_rerank" else None},
            },
            "caveats": (["Lexical BM25 is rebuilt per request; persistent lexical indexing is not implemented."]
                        if method != "dense" else [])}
