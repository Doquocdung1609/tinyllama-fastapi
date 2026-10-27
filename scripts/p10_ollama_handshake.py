"""Bounded read-only live embedding identity probe; never pulls a model."""
import argparse
from hashlib import sha256
import json
import math
from pathlib import Path
import struct
from time import perf_counter

import psutil
import requests

from app.financial_index.service import OllamaVectors, valid_vectors


MODEL = "nomic-embed-text:latest"
EXPECTED_DIGEST = "0a109f422b47e3a30ba2b10eca18548e944e8a23073ee3f3e947efcf3c45e59f"
URL = "http://127.0.0.1:11434"


def embed(session, text):
    started = perf_counter()
    response = session.post(URL + "/api/embed", json={"model": MODEL, "input": [text],
        "truncate": True, "keep_alive": "5m"}, timeout=90)
    response.raise_for_status()
    vector = response.json()["embeddings"][0]
    valid_vectors([vector], 1, 768)
    return vector, (perf_counter() - started) * 1000


def fingerprint(vector):
    return sha256(b"".join(struct.pack("<d", float(value)) for value in vector)).hexdigest()


def run():
    memory_before = psutil.virtual_memory().available
    with requests.Session() as session:
        response = session.get(URL + "/api/tags", timeout=5)
        response.raise_for_status()
        model = next((item for item in response.json().get("models", [])
                      if item.get("name") == MODEL), None)
        if model is None or model.get("digest") != EXPECTED_DIGEST:
            raise ValueError("ACCEPTED_EMBEDDING_DIGEST_MISMATCH")
        query = OllamaVectors.query_prefix + "P&G total assets as of September 30, 2026"
        document = OllamaVectors.document_prefix + "TOTAL ASSETS 133,132 (Amounts in millions)"
        first, first_ms = embed(session, query)
        second, second_ms = embed(session, query)
        doc, document_ms = embed(session, document)
    memory_after = psutil.virtual_memory().available
    norm = lambda values: math.sqrt(sum(float(value) ** 2 for value in values))
    return {"schema_version": "topic3-p10-live-embedding/v1", "endpoint": URL,
            "model": MODEL, "digest": model["digest"], "expected_digest": EXPECTED_DIGEST,
            "dimension": len(first), "all_finite": all(math.isfinite(float(v)) for v in first + second + doc),
            "query_prefix": OllamaVectors.query_prefix,
            "document_prefix": OllamaVectors.document_prefix,
            "document_truncation_content_characters": 6000,
            "normalization_policy": "unicode-preserved;whitespace-preserved",
            "distance_policy": "COSINE", "query_norm": norm(first), "document_norm": norm(doc),
            "query_repeat_max_abs_delta": max(abs(a - b) for a, b in zip(first, second)),
            "query_vector_sha256_first": fingerprint(first),
            "query_vector_sha256_repeat": fingerprint(second),
            "latency_ms": {"first_query": first_ms, "repeat_query": second_ms,
                           "first_document": document_ms},
            "available_ram_bytes_before": memory_before,
            "available_ram_bytes_after": memory_after,
            "vector_values_recorded": False, "model_downloaded": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: result[key] for key in ("model", "digest", "dimension", "all_finite",
                     "query_repeat_max_abs_delta", "latency_ms")}))
