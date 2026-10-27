"""Provisional B/D/F/A development comparison on P11's frozen source labels.

This script never opens validation or held-out raw/parsed files. It does not
certify label completeness, column-level correctness or financial answers.
"""
import argparse
from contextlib import closing
from datetime import date
import json
from math import log2
from pathlib import Path
from statistics import median
from time import perf_counter
from types import SimpleNamespace

import psutil
import requests
from qdrant_client import QdrantClient, models

from app.financial_index.corpus import ProvenanceCache, verified_source
from app.financial_index.lexical import LexicalIndex
from app.financial_index.ownership import LocalQdrantOwnership
from app.financial_index.service import OllamaVectors, valid_vectors
from app.financial_query import resolve_financial_query
from app.financial_query.contracts import CatalogFilingV1, CorpusCatalogV1, IssuerV1
from app.research_retrieval.adapters import candidate
from app.research_retrieval.ranking import fuse, single
from scripts.p11_acquire_official_sec import file_hash
from scripts.p11_build_dev_indexes import (COLLECTION, DATASET, DIGEST, DOCS, MODEL,
                                           URL, frozen_sources)


def percentile(values, p):
    ordered = sorted(values)
    if not ordered:
        return None
    at = (len(ordered) - 1) * p
    lower = int(at)
    upper = min(lower + 1, len(ordered) - 1)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (at - lower)


def catalog_for_refusals(identity, source_rows):
    acquisitions = {r["ticker"]: r for r in json.loads(
        (DOCS / "p11_source_registry.json").read_text(encoding="utf-8"))["records"]}
    issuers, filings = [], []
    for row in source_rows:
        item = acquisitions[row["ticker"]]
        meta = item["metadata"]
        issuers.append(IssuerV1(cik=row["cik"], company_name=meta["company_name"],
                                tickers=[row["ticker"]]))
        filings.append(CatalogFilingV1(filing_id=meta["filing_id"],
            cik=row["cik"], accession=row["accession"], form=meta["form_type"],
            filing_date=date.fromisoformat(meta["filing_date"]),
            report_end=date.fromisoformat(meta["report_date"]),
            extraction_status=row["extraction_status"],
            column_periods_complete=False))
    return CorpusCatalogV1(dataset_id=DATASET, manifest_hash=identity["manifest_hash"],
        generation_id=identity["generation"],
        provenance="Official SEC HTTPS bytes; P11 isolated local SHA256 and canonical reparse; not SEC-signed",
        issuers=issuers, filings=filings)


def evaluate(root):
    root = root.resolve(strict=True)
    freeze = json.loads((DOCS / "p11_development_freeze.json").read_text(encoding="utf-8"))
    for name, expected in freeze["file_sha256"].items():
        if file_hash(DOCS / name) != expected:
            raise ValueError("P11_DEVELOPMENT_FREEZE_CHANGED:" + name)
    policy = json.loads((DOCS / "p11_adaptive_policy_v1.json").read_text(encoding="utf-8"))
    if (policy["candidate_limit_per_channel"] != 40 or policy["rrf_k"] != 60
        or policy["validation_finalist_selected"] or policy["heldout_used"]):
        raise ValueError("P11_ADAPTIVE_POLICY_CHANGED")
    queries = json.loads((DOCS / "p11_query_registry.json").read_text(encoding="utf-8"))["queries"]
    qrels = json.loads((DOCS / "p11_qrels.json").read_text(encoding="utf-8"))["qrels"]
    gold = {r["query_id"]: r["parent_id"] for r in qrels}
    parents, source_rows, manifest_hash, membership, generation = frozen_sources(root)
    folder = root / "index_dev"
    identity = json.loads((folder / "generation_manifest.json").read_text(encoding="utf-8"))
    if (identity["state"] != "READY" or identity["completed_points"] != len(parents)
        or identity["lexical_count"] != len(parents) or identity["generation"] != generation
        or identity["manifest_hash"] != manifest_hash
        or identity["parent_membership_sha256"] != membership
        or identity["model_digest"] != DIGEST):
        raise ValueError("P11_COMPARISON_GENERATION_NOT_READY_OR_COMPATIBLE")
    index = LexicalIndex(folder / "lexical.sqlite3")
    record = index.generation(DATASET, generation)
    if record["state"] != "READY" or record["n"] != len(parents):
        raise ValueError("P11_LEXICAL_GENERATION_NOT_READY")
    by_id = {p["cid"]: p for p in parents}
    by_ticker = {r["ticker"]: r for r in source_rows}
    filing_by_ticker = {r["ticker"]: next(p["chunk"].filing_id for p in parents
                                              if p["chunk"].metadata["ticker"] == r["ticker"])
                        for r in source_rows}
    if len(gold) != len(qrels) or len(gold) != sum(bool(q.get("eligible_parent_ids")) for q in queries):
        raise ValueError("P11_QREL_QUERY_CARDINALITY_MISMATCH")
    for query in queries:
        if not query.get("eligible_parent_ids"):
            continue
        row = by_ticker.get(query["issuer"])
        parent = by_id.get(gold.get(query["query_id"]))
        if (row is None or parent is None or query["partition"] != "development"
            or gold[query["query_id"]] not in query["eligible_parent_ids"]
            or parent["chunk"].metadata["cik"] != query["cik"]
            or parent["chunk"].filing_id != filing_by_ticker[query["issuer"]]
            or query["raw_sha256"] != row["raw_sha256"]
            or query["accession"] != row["accession"]):
            raise ValueError("P11_QREL_SOURCE_SCOPE_MISMATCH")
    scope = SimpleNamespace(generation_id=generation, manifest_hash=manifest_hash)
    cache = ProvenanceCache(max_entries=2, max_bytes=64 * 1024 * 1024)
    with requests.Session() as session:
        tags = session.get(URL + "/api/tags", timeout=5)
        tags.raise_for_status()
        live = next((m for m in tags.json().get("models", []) if m.get("name") == MODEL), None)
        if live is None or live.get("digest") != DIGEST:
            raise ValueError("P11_LIVE_EMBEDDING_CHANGED")
        owner = LocalQdrantOwnership(folder / "qdrant")
        try:
            client = QdrantClient(path=str(folder / "qdrant"))
            try:
                if client.count(COLLECTION, exact=True).count != len(parents):
                    raise ValueError("P11_VECTOR_COUNT_CHANGED")
                results = []
                for query in queries:
                    if query.get("eligible_parent_ids") == []:
                        continue
                    started = perf_counter()
                    ticker = query["issuer"]
                    cik = query["cik"]
                    filing_id = filing_by_ticker[ticker]
                    frozen = next(p["frozen"] for p in parents
                                  if p["chunk"].metadata["ticker"] == ticker)
                    canonical = verified_source(frozen, cache=cache, generation=generation)
                    def authenticated(item, channel, score):
                        cid = item["cid"]
                        if (cid not in canonical or item["chunk"].model_dump(mode="json") !=
                            canonical[cid].model_dump(mode="json")
                            or item["chunk"].metadata["cik"] != cik
                            or item["chunk"].filing_id != filing_id):
                            raise ValueError("P11_RETRIEVED_PARENT_PROVENANCE_MISMATCH")
                        return candidate(item["chunk"], scope, channel, score)
                    b_start = perf_counter()
                    b_hits = index.search(query["question"], record, 40,
                                          {"cik": cik, "filing_ids": [filing_id]})
                    b = [authenticated(by_id[h["chunk_id"]], "B", h["bm25_score"])
                         for h in b_hits]
                    b_ms = (perf_counter() - b_start) * 1000
                    d_start = perf_counter()
                    response = session.post(URL + "/api/embed", json={"model": MODEL,
                        "input": [OllamaVectors.query_prefix + query["question"]],
                        "truncate": True, "keep_alive": "5m"}, timeout=30)
                    response.raise_for_status()
                    vector = response.json()["embeddings"][0]
                    valid_vectors([vector], 1, 768)
                    embed_ms = (perf_counter() - d_start) * 1000
                    search_start = perf_counter()
                    filter_ = models.Filter(must=[
                        models.FieldCondition(key="cik", match=models.MatchValue(value=cik)),
                        models.FieldCondition(key="filing_id", match=models.MatchValue(value=filing_id))])
                    points = client.query_points(COLLECTION, query=vector,
                        query_filter=filter_, limit=40, with_payload=True).points
                    d = []
                    for point in points:
                        cid = point.payload.get("chunk_id")
                        item = by_id.get(cid)
                        if (item is None or point.payload.get("generation") != generation
                            or point.payload.get("manifest_hash") != manifest_hash
                            or point.payload.get("model_digest") != DIGEST
                            or point.payload.get("payload_hash") != item["payload_hash"]
                            or point.payload.get("raw_hash") != item["frozen"]["raw_hash"]):
                            raise ValueError("P11_VECTOR_PAYLOAD_IDENTITY_MISMATCH")
                        d.append(authenticated(item, "D", point.score))
                    dense_search_ms = (perf_counter() - search_start) * 1000
                    b_rank, d_rank = single(b), single(d)
                    f_rank = fuse(b, d, weights=(1, 1), k=60)
                    exact = query["category"] in policy["exact_categories"]
                    if exact and sum(c.score > 0 for c in b) >= 5:
                        a_rank, a_route = b_rank, "B_FIVE_POSITIVE_HEURISTIC"
                    else:
                        weights = (2, 1) if exact else (1, 1)
                        a_rank = fuse(b, d, weights=weights, k=60)
                        a_route = "WEIGHTED_RRF_2_1" if exact else "FIXED_RRF_1_1"
                    # Rehash the authenticated source after ranking to detect
                    # replacement during the query, even on a provenance-cache hit.
                    verified_source(frozen, cache=cache, generation=generation)
                    arms = {}
                    for name, ranks in (("B", b_rank), ("D", d_rank),
                                        ("F", f_rank), ("A", a_rank)):
                        top = [r.candidate.chunk_id for r in ranks[:10]]
                        relevant = gold[query["query_id"]]
                        position = top.index(relevant) + 1 if relevant in top else None
                        arms[name] = {"top10_ids": top,
                            "gold_rank_at_10": position,
                            "recall_at_5": int(position is not None and position <= 5),
                            "recall_at_10": int(position is not None),
                            "mrr_at_5": 1 / position if position and position <= 5 else 0,
                            "ndcg_at_5": 1 / log2(position + 1) if position and position <= 5 else 0,
                            "wrong_issuer_top5": sum(by_id[cid]["chunk"].metadata["cik"] != cik
                                                     for cid in top[:5]),
                            "top5_count": len(top[:5])}
                        if name in {"F", "A"}:
                            arms[name]["top5_contributions"] = [
                                {"chunk_id": hit.candidate.chunk_id,
                                 "b_rank": hit.b_rank, "d_rank": hit.d_rank,
                                 "b_contribution": hit.b_contribution,
                                 "d_contribution": hit.d_contribution}
                                for hit in ranks[:5]]
                    results.append({"query_id": query["query_id"], "issuer": ticker,
                        "category": query["category"], "gold_parent_id": gold[query["query_id"]],
                        "a_route": a_route, "b_candidates": len(b), "d_candidates": len(d),
                        "stage_ms": {"bm25": round(b_ms, 3),
                                     "ollama_embed": round(embed_ms, 3),
                                     "qdrant_search_and_verification": round(dense_search_ms, 3),
                                     "total": round((perf_counter() - started) * 1000, 3)},
                        "arms": arms})
                catalog = catalog_for_refusals(identity, source_rows)
                refusals = []
                for query in queries:
                    if query.get("eligible_parent_ids"):
                        continue
                    resolution = resolve_financial_query(query["question"], {}, catalog)
                    refusals.append({"query_id": query["query_id"],
                                     "expected_class": query["expected_status"],
                                     "observed_status": resolution.status.value,
                                     "eligible_filing_ids": list(resolution.resolved_scope.eligible_filing_ids)
                                     if resolution.resolved_scope else []})
                aggregates = {}
                for arm in ("B", "D", "F", "A"):
                    measures = [q["arms"][arm] for q in results]
                    aggregates[arm] = {key: sum(m[key] for m in measures) / len(measures)
                                       for key in ("recall_at_5", "recall_at_10",
                                                   "mrr_at_5", "ndcg_at_5")}
                    aggregates[arm]["evidence_group_coverage_at_5"] = aggregates[arm]["recall_at_5"]
                    aggregates[arm]["wrong_issuer_rate_at_5"] = (sum(m["wrong_issuer_top5"] for m in measures)
                        / max(1, sum(m["top5_count"] for m in measures)))
                    aggregates[arm]["wrong_period_rate"] = "NOT_MEASURED_COLUMN_LEVEL"
                    aggregates[arm]["source_provenance_validity"] = "ALL_RETURNED_PARENTS_VERIFIED"
                    aggregates[arm]["channel_failures"] = 0
                totals = [q["stage_ms"]["total"] for q in results]
                return {"schema_version": "topic3-p11-provisional-development-comparison/v1",
                    "status": "COMPLETED_PROVISIONAL_UNREVIEWED_LABELS",
                    "dataset": DATASET, "generation": generation,
                    "manifest_hash": manifest_hash,
                    "parent_membership_sha256": membership,
                    "model_digest": DIGEST, "candidate_budget_per_channel": 40,
                    "rrf_k": 60, "top_k": [5, 10],
                    "source_selection_commit": "d04fd4b53c104cbc5208ff33bcf876ae7bcbc03e",
                    "dev_label_freeze_commit": "5377534170523a1872f0bcf17b72d69bfc595859",
                    "human_reviewers": 0, "qrel_exhaustiveness_verified": False,
                    "ranking_quality_claim": "PROVISIONAL_DEVELOPMENT_ONLY",
                    "adaptive_finalist_selected": False,
                    "validation_scored": False, "heldout_opened": False,
                    "query_count": len(results), "refusal_count": len(refusals),
                    "per_query": results, "refusals": refusals,
                    "aggregate": aggregates,
                    "total_wall_ms_p50": median(totals),
                    "total_wall_ms_p95": percentile(totals, .95),
                    "available_ram_bytes_after": psutil.virtual_memory().available,
                    "isolated_index_bytes": sum(p.stat().st_size for p in folder.rglob("*") if p.is_file())}
            finally:
                client.close()
        finally:
            owner.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    value = evaluate(args.root)
    args.output.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": value["status"], "query_count": value["query_count"],
                      "aggregate": value["aggregate"]}))
