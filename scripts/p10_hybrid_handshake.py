"""Development-only D1/D3 B-D-F handshake over the isolated P10 vectors."""
import argparse
from contextlib import closing, contextmanager
import json
from pathlib import Path
from time import perf_counter

import requests
from qdrant_client import QdrantClient, models

from app.financial_index.corpus import verified_source
from app.financial_index.ownership import LocalQdrantOwnership, require_supported_embedded_qdrant
from app.financial_index.service import OllamaVectors, valid_vectors
from app.financial_ingestion.schemas import FinancialChunk
from app.research_qa.source_alias import verified_alias_catalog
from app.research_retrieval.adapters import candidate
from app.research_retrieval.contracts import PolicyV1
from app.research_retrieval.service import retrieve_financial_query
from app.research_retrieval.snapshot import FrozenResearchSnapshot
from app.table_evidence.identity import digest

from scripts.p10_build_isolated_vectors import COLLECTION, EXPECTED_DIGEST, MODEL, URL


QUERIES = (
    ("pg_net_sales", "P&G net sales", {}),
    ("hd_total_assets", "HD total assets", {}),
    ("wrong_issuer", "Walmart net sales", {}),
    ("issuer_conflict", "HD total assets", {"cik": "0000080424"}),
    ("explicit_period_uncertain", "P&G net sales for the three months ended September 30, 2026", {}),
)


class IsolatedDenseAdapter:
    def __init__(self, snapshot, client, session, identity):
        self.snapshot = snapshot
        self.client = client
        self.session = session
        self.identity = identity

    @contextmanager
    def pin(self, scope):
        with self.snapshot.pin(scope):
            yield

    def search(self, question, scope, channel, limit, deadline):
        if channel == "B":
            return self.snapshot.search(question, scope, "B", limit, deadline)
        if channel != "D":
            raise ValueError("UNKNOWN_P10_CHANNEL")
        if (scope.generation_id != self.identity["generation"]
            or scope.manifest_hash != self.identity["manifest_hash"]):
            raise ValueError("DENSE_SOURCE_GENERATION_MISMATCH")
        tags = self.session.get(URL + "/api/tags", timeout=5)
        tags.raise_for_status()
        live = next((m for m in tags.json().get("models", []) if m.get("name") == MODEL), None)
        if live is None or live.get("digest") != EXPECTED_DIGEST:
            raise ValueError("DENSE_LIVE_MODEL_CHANGED")
        response = self.session.post(URL + "/api/embed", json={"model": MODEL,
            "input": [OllamaVectors.query_prefix + question], "truncate": True,
            "keep_alive": "5m"}, timeout=min(90, deadline))
        response.raise_for_status()
        vector = response.json()["embeddings"][0]
        valid_vectors([vector], 1, 768)
        query_filter = models.Filter(must=[
            models.FieldCondition(key="cik", match=models.MatchValue(value=scope.cik)),
            models.FieldCondition(key="filing_id", match=models.MatchAny(
                any=list(scope.eligible_filing_ids)))])
        points = self.client.query_points(COLLECTION, query=vector, query_filter=query_filter,
                                          limit=limit, with_payload=True).points
        out = []
        verified = {}
        with closing(self.snapshot.lexical.connect()) as db:
            for point in points:
                payload = point.payload
                cid = payload.get("chunk_id")
                row = db.execute("SELECT d.payload,d.payload_hash,m.source FROM documents d "
                    "JOIN members m ON m.cid=d.cid WHERE d.cid=? AND m.generation=?",
                    (cid, scope.generation_id)).fetchone()
                if row is None:
                    raise ValueError("VECTOR_PARENT_NOT_IN_PINNED_LEXICAL_GENERATION")
                frozen = json.loads(row["source"])
                parent = FinancialChunk.model_validate_json(row["payload"])
                if (payload.get("generation") != scope.generation_id
                    or payload.get("manifest_hash") != scope.manifest_hash
                    or payload.get("model_digest") != EXPECTED_DIGEST
                    or payload.get("payload_hash") != row["payload_hash"]
                    or payload.get("raw_hash") != frozen["raw_hash"]
                    or payload.get("cik") != scope.cik
                    or payload.get("filing_id") not in scope.eligible_filing_ids
                    or parent.filing_id != payload["filing_id"]
                    or digest(parent.model_dump(mode="json")) != row["payload_hash"]):
                    raise ValueError("DENSE_VECTOR_SOURCE_IDENTITY_MISMATCH")
                for key in ("raw_path", "structured_path", "chunks_path"):
                    if not Path(frozen[key]).resolve().is_relative_to(self.snapshot.root):
                        raise ValueError("DENSE_SOURCE_PATH_ESCAPE")
                if frozen["raw_hash"] not in verified:
                    verified[frozen["raw_hash"]] = verified_source(frozen,
                        cache=self.snapshot.cache, generation=scope.generation_id)
                canonical = verified[frozen["raw_hash"]].get(cid)
                if canonical is None or canonical.model_dump(mode="json") != parent.model_dump(mode="json"):
                    raise ValueError("DENSE_PARENT_RECONSTRUCTION_MISMATCH")
                out.append(candidate(parent, scope, "D", point.score))
        return out


def run(root, vector_root):
    root = root.resolve(strict=True)
    vector_root = vector_root.resolve(strict=True)
    if "p7-isolated-review" not in root.name or not vector_root.name.startswith("t3-p10-isolated-vectors-"):
        raise ValueError("ISOLATED_P10_PATHS_REQUIRED")
    snapshot = FrozenResearchSnapshot(root)
    identity = json.loads((vector_root / "generation_manifest.json").read_text(encoding="utf-8"))
    if (identity["state"] != "READY" or identity["completed_points"] != identity["parent_count"]
        or identity["generation"] != snapshot.freeze["generation"]
        or identity["manifest_hash"] != snapshot.freeze["manifest_hash"]
        or identity["model_digest"] != EXPECTED_DIGEST):
        raise ValueError("P10_DENSE_GENERATION_NOT_READY_OR_COMPATIBLE")
    require_supported_embedded_qdrant()
    owner = LocalQdrantOwnership(vector_root / "qdrant")
    try:
        client = QdrantClient(path=str(vector_root / "qdrant"))
        try:
            if client.count(COLLECTION, exact=True).count != identity["parent_count"]:
                raise ValueError("QDRANT_PARENT_COUNT_MISMATCH")
            with requests.Session() as session:
                adapter = IsolatedDenseAdapter(snapshot, client, session, identity)
                catalog = verified_alias_catalog(snapshot)
                rows = []
                for case_id, question, filters in QUERIES:
                    arm_results = {}
                    for arm in ("B", "D", "F"):
                        started = perf_counter()
                        result = retrieve_financial_query(question, filters, catalog,
                            adapter, arm, policy=PolicyV1(top_k=5), evidence_lookup=None)
                        arm_results[arm] = {"status": result.status,
                            "effective_mode": result.effective_mode,
                            "failure_code": result.failure_code,
                            "generation": result.generation,
                            "manifest_hash": result.manifest_hash,
                            "b_candidates": list(result.b_candidates),
                            "d_candidates": list(result.d_candidates),
                            "trace": list(result.trace),
                            "timings_ms": dict(result.timings_ms),
                            "wall_ms": (perf_counter() - started) * 1000,
                            "top": [{"chunk_id": hit.candidate.chunk_id,
                                     "cik": hit.candidate.cik,
                                     "filing_id": hit.candidate.filing_id,
                                     "score": hit.score, "b_rank": hit.b_rank,
                                     "d_rank": hit.d_rank,
                                     "b_contribution": hit.b_contribution,
                                     "d_contribution": hit.d_contribution}
                                    for hit in result.results]}
                    if case_id in {"pg_net_sales", "hd_total_assets"}:
                        if any(arm_results[a]["status"] != "OK" or not arm_results[a]["top"]
                               for a in ("B", "D", "F")):
                            raise AssertionError("VALID_CHANNEL_HANDSHAKE_FAILED:" + case_id)
                        for arm in ("B", "D", "F"):
                            if any(hit["cik"] != arm_results[arm]["top"][0]["cik"]
                                   for hit in arm_results[arm]["top"]):
                                raise AssertionError("CROSS_ISSUER_CANDIDATE")
                    else:
                        if any(arm_results[a]["top"] for a in ("B", "D", "F")):
                            raise AssertionError("UNRESOLVED_SCOPE_RETURNED_CANDIDATE")
                    rows.append({"case_id": case_id, "question": question,
                                 "filters": filters, "arms": arm_results})
                return {"schema_version": "topic3-p10-development-handshake/v1",
                        "purpose": "functional_development_only_not_heldout_quality",
                        "generation": identity["generation"],
                        "manifest_hash": identity["manifest_hash"],
                        "membership_hash": identity["membership_hash"],
                        "model_digest": identity["model_digest"],
                        "candidate_budget_per_channel": 40, "rrf_k": 60,
                        "queries": rows}
        finally:
            client.close()
    finally:
        owner.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--vector-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.root, args.vector_root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({row["case_id"]: {arm: row["arms"][arm]["status"]
        for arm in ("B", "D", "F")} for row in result["queries"]}))
