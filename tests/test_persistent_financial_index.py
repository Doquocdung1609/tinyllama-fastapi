from collections import Counter
from contextlib import closing
import json
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.financial_index.lexical import financial_tokens
from app.financial_index.service import FinancialIndex
from app.financial_ingestion.pipeline import FinancialCorpusPipeline
from app.financial_ingestion.registry import FinancialRegistry
from test_financial_ingestion import FixtureClient, filing


class FakeVectors:
    def __init__(self):
        self.calls = 0
        self.digest = "fixture-digest"
        self.bad_dimension = False

    def identity(self):
        return {"model": "fixture", "digest": self.digest, "dimension": 3, "input_policy": "fixture"}

    def embed(self, texts):
        self.calls += len(texts)
        return [[1., float(text.lower().count("revenue") + 1), float(text.lower().count("cash") + 1)]
                if not self.bad_dimension else [1., 2.] for text in texts]


def source(tmp_path, *, amendment=False):
    root = tmp_path / "corpus"
    pipeline = FinancialCorpusPipeline(root=root, registry=FinancialRegistry(root / "registry.sqlite3"), client=FixtureClient())
    original = filing()
    pipeline.ingest_one("fixture", original)
    if amendment:
        pipeline.ingest_one("fixture", filing("0000123456-24-000002", "10-K/A", "amendment.htm"))
    manifest = pipeline.create_manifest("fixture")
    return [{"root": str(root), "dataset_id": "fixture", "manifest_hash": manifest.manifest_hash,
             "allow_partial": True}], pipeline


def built(tmp_path, *, amendment=False):
    specs, pipeline = source(tmp_path, amendment=amendment)
    provider = FakeVectors()
    engine = FinancialIndex(tmp_path / "index", provider=provider)
    generation = engine.plan("test", specs)
    stats = engine.build("test", generation, batch_size=2)
    return engine, provider, generation, stats, specs, pipeline


def test_financial_aliases_preserve_sign_percent_period_and_display_distinctions():
    assert "num:+1250" in financial_tokens("1,250")
    assert "num:+1250" in financial_tokens("1250")
    assert "num:-300" in financial_tokens("(300)")
    assert "num:-300" in financial_tokens("-300")
    assert "pct:+12.5" in financial_tokens("12.5%")
    assert "pct:+12.5" not in financial_tokens("12.5")
    assert "fy:2025" in financial_tokens("FY2025")
    assert "quarter:q3" in financial_tokens("Q3 2025")
    assert "form:10-k/a" in financial_tokens("10-K/A")
    assert "acc:0000123456-24-000001" in financial_tokens("0000123456-24-000001")


def test_restart_stable_results_idempotent_build_and_no_query_retokenization(tmp_path, monkeypatch):
    engine, provider, generation, stats, specs, _ = built(tmp_path)
    first = engine.search("test", "Revenue", "bm25")
    assert first["results"] and all(row["provenance_status"] == "VERIFIED" for row in first["results"])
    calls = provider.calls
    assert engine.build("test", generation)["idempotent_reuse"] is True
    assert provider.calls == calls
    engine.close()
    restarted = FinancialIndex(tmp_path / "index", provider=provider)
    seen = []
    from app.financial_index import lexical
    original = lexical.financial_tokens
    monkeypatch.setattr(lexical, "financial_tokens", lambda text: seen.append(text) or original(text))
    second = restarted.search("test", "Revenue", "bm25")
    assert seen == ["Revenue"]
    assert [row["chunk_id"] for row in first["results"]] == [row["chunk_id"] for row in second["results"]]
    assert provider.calls == calls
    assert restarted.search("test", "Revenue", "dense")["results"]
    restarted.close()


def test_exact_bm25_formula_and_metadata_filter_parity(tmp_path, monkeypatch):
    engine, _, gen, _, _, _ = built(tmp_path, amendment=True)
    from app.services import financial_search_service as legacy
    monkeypatch.setattr(legacy, "tokenize", financial_tokens)
    records = list(engine.lexical.records(gen))
    chunks = [item["chunk"] for item in records if item["chunk"]["metadata"]["form_type"] == "10-K/A"]
    expected = legacy.bm25_rank("Revenue 2023", chunks, 20)
    actual = engine.search("test", "Revenue 2023", "bm25", top_k=20, filters={"form_type": "10-K/A"})["results"]
    assert [item["chunk_id"] for item in actual] == [item["chunk_id"] for item in expected]
    assert [item["bm25_score"] for item in actual] == pytest.approx([item["bm25_score"] for item in expected])
    assert all(item["metadata"]["form_type"] == "10-K/A" for item in actual)
    assert engine.search("test", "Revenue", "hybrid", filters={"ticker": "OTHER"})["results"] == []
    engine.close()


def test_partial_build_preserves_active_and_can_resume_incrementally(tmp_path):
    engine, provider, first, _, specs, pipeline = built(tmp_path)
    pipeline.ingest_one("fixture", filing("0000123456-24-000002", "10-K/A", "amendment.htm"))
    manifest = pipeline.create_manifest("fixture")
    newer = [{**specs[0], "manifest_hash": manifest.manifest_hash}]
    second = engine.plan("test", newer)
    with pytest.raises(RuntimeError, match="CONTROLLED_BUILD_INTERRUPTION"):
        engine.build("test", second, batch_size=1, fail_after_batches=1)
    assert engine.lexical.generation("test")["generation"] == first
    assert engine.lexical.generation("test", second)["state"] == "FAILED"
    before = provider.calls
    engine.close()
    engine = FinancialIndex(tmp_path / "index", provider=provider)
    stats = engine.build("test", second, batch_size=2)
    assert stats["new_posting_documents"] > 0
    assert provider.calls - before < stats["upserted_chunks"]
    assert engine.lexical.generation("test")["generation"] == second
    engine.activate("test", first)
    assert engine.lexical.generation("test")["generation"] == first
    assert engine.search("test", "Revenue", "hybrid", generation=second)["results"]
    engine.close()


def test_new_python_process_reads_persistent_lexical_results(tmp_path):
    import subprocess
    import sys
    engine, _, _, _, _, _ = built(tmp_path)
    expected = engine.search("test", "Revenue", "bm25")["results"]
    engine.close()
    completed = subprocess.run([sys.executable, "scripts/financial_index.py", "--index-root", str(tmp_path / "index"),
        "search", "--dataset", "test", "--query", "Revenue", "--mode", "bm25"], capture_output=True, text=True, check=True)
    actual = json.loads(completed.stdout)["results"]
    assert [item["chunk_id"] for item in actual] == [item["chunk_id"] for item in expected]


def test_incremental_derived_revision_reuses_embeddings_and_keeps_old_generation(tmp_path):
    from test_financial_ingestion import MutableFixtureClient, FIXTURE
    engine, provider, first, _, specs, pipeline = built(tmp_path)
    old_hash = specs[0]["manifest_hash"]
    pipeline.client = MutableFixtureClient(FIXTURE.read_bytes().replace(b"1,250", b"1,550"))
    pipeline.ingest_one("fixture", filing(), force=True)
    new_manifest = pipeline.create_manifest("fixture")
    second = engine.plan("test", [{**specs[0], "manifest_hash": new_manifest.manifest_hash}])
    stats = engine.build("test", second)
    assert stats["embedded_texts"] == 1
    old = engine.search("test", "Revenue", "bm25", generation=first, expected_manifests=[old_hash])
    new = engine.search("test", "Revenue", "bm25", generation=second)
    assert any("1,250" in row["text"] for row in old["results"])
    assert any("1,550" in row["text"] for row in new["results"])
    assert {row["chunk_id"] for row in old["results"]}.isdisjoint(row["chunk_id"] for row in new["results"])
    engine.close()


def test_rrf_and_all_supported_filters_preserve_provenance(tmp_path):
    engine, _, gen, _, _, _ = built(tmp_path, amendment=True)
    filters = {"cik": "0000123456", "ticker": "exm", "fiscal_year": 2023,
               "fiscal_period": "fy", "filing_ids": [filing().filing_id]}
    result = engine.search("test", "Revenue", "hybrid", top_k=20, candidate_limit=100, filters=filters)
    for row in result["results"]:
        expected = sum(1. / (60 + row[key]) for key in ["bm25_rank", "dense_rank"] if row[key] is not None)
        assert row["rrf_score"] == pytest.approx(expected)
        assert row["filing_id"] == filing().filing_id
        assert row["provenance_status"] == "VERIFIED"
    assert len({row["chunk_id"] for row in result["results"]}) == len(result["results"])
    engine.close()


def test_qdrant_failure_is_explicit_and_failed_generation_never_active(tmp_path, monkeypatch):
    engine, _, _, _, specs, _ = built(tmp_path)
    def unavailable(*args, **kwargs):
        raise ConnectionError("synthetic Qdrant failure")
    monkeypatch.setattr(engine, "validate_dense", unavailable)
    with pytest.raises(RuntimeError, match="synthetic Qdrant failure"):
        engine.search("test", "Revenue", "hybrid")
    degraded = engine.search("test", "Revenue", "hybrid", allow_degraded=True)
    assert degraded["effective_mode"] == "bm25" and degraded["results"]
    new = engine.plan("test", specs, force_rebuild=True)
    with pytest.raises(ConnectionError):
        engine.build("test", new)
    assert engine.lexical.generation("test")["generation"] != new
    engine.close()


def test_dimension_mismatch_never_publishes_and_model_drift_fails_or_explicitly_degrades(tmp_path):
    specs, _ = source(tmp_path)
    provider = FakeVectors()
    provider.bad_dimension = True
    engine = FinancialIndex(tmp_path / "index", provider=provider)
    gen = engine.plan("test", specs)
    with pytest.raises(ValueError, match="EMBEDDING_DIMENSION"):
        engine.build("test", gen)
    with pytest.raises(ValueError, match="DATASET_NOT_INDEXED"):
        engine.search("test", "Revenue", "bm25")
    provider.bad_dimension = False
    engine.build("test", gen)
    provider.digest = "changed"
    with pytest.raises(RuntimeError, match="IDENTITY_MISMATCH"):
        engine.search("test", "Revenue", "hybrid")
    result = engine.search("test", "Revenue", "hybrid", allow_degraded=True)
    assert result["effective_mode"] == "bm25" and result["degraded_reason"]
    engine.close()


def test_snapshot_dense_mismatch_and_duplicate_inputs_are_not_silently_mixed(tmp_path):
    specs, _ = source(tmp_path)
    engine = FinancialIndex(tmp_path / "index", provider=FakeVectors())
    gen = engine.plan("test", specs + specs)
    engine.build("test", gen)
    unique = list(engine.lexical.records(gen))
    assert len(unique) == len({row["chunk"]["chunk_id"] for row in unique})
    with pytest.raises(ValueError, match="REQUESTED_SNAPSHOT_MISMATCH"):
        engine.search("test", "Revenue", expected_manifests=["wrong"])
    record = engine.lexical.generation("test")
    collection = record["metadata"]["collection"]
    points, _ = engine.dense.scroll(collection, limit=1)
    engine.dense.set_payload(collection, payload={"generation": "wrong"}, points=[points[0].id])
    with pytest.raises(RuntimeError, match="MEMBERSHIP_MISMATCH"):
        engine.search("test", "Revenue", "dense")
    assert engine.search("test", "Revenue", "bm25")["results"]
    repaired = engine.plan("test", specs, force_rebuild=True)
    engine.build("test", repaired)
    assert engine.search("test", "Revenue", "hybrid")["results"]
    assert engine.dense.collection_exists(collection)  # no old vector deletion
    engine.close()


def test_source_tampering_is_rejected_and_old_manifest_unmodified(tmp_path):
    engine, _, gen, _, specs, pipeline = built(tmp_path)
    manifest_path = Path(pipeline.registry.manifests("fixture")[0]["path"])
    original = manifest_path.read_bytes()
    row = pipeline.registry.list_filings()[0]
    Path(row["raw_path"]).write_bytes(b"<html>tampered</html>")
    with pytest.raises(ValueError, match="HASH_MISMATCH"):
        engine.search("test", "Revenue", "bm25")
    assert manifest_path.read_bytes() == original
    engine.close()


def test_unknown_or_building_generation_cannot_be_queried_and_api_keeps_scope(tmp_path, monkeypatch):
    engine, _, gen, _, _, _ = built(tmp_path)
    from app.api import financial_index as api
    monkeypatch.setattr(api, "get_index", lambda: engine)
    app = FastAPI()
    app.include_router(api.router)
    with TestClient(app) as client:
        assert client.get("/financial-index/datasets").json()["datasets"][0]["state"] == "READY"
        response = client.post("/financial-index/search", json={"dataset_id": "test", "query": "Revenue", "mode": "bm25"})
        assert response.status_code == 200 and response.json()["generation"] == gen
        assert client.post("/financial-index/search", json={"dataset_id": "other", "query": "Revenue"}).status_code == 409
        assert client.post("/financial-index/search", json={"dataset_id": "test", "query": "  "}).status_code == 422
    engine.close()
