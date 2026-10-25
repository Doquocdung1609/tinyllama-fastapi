from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import subprocess
import sys
import time
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
import requests

from app.financial_index.corpus import ProvenanceCache, verified_source
from app.financial_index.ownership import LocalQdrantOwnership
from app.financial_index.service import FinancialIndex, OllamaVectors
from app.path_safety import ensure_path_capacity
from test_persistent_financial_index import FakeVectors, built


class ApiEngine:
    def __init__(self):
        self.activations = []
        self.builds = []

    def describe(self):
        return []

    def search(self, dataset, query, mode, **kwargs):
        return {"dataset_id": dataset, "mode": mode, "results": []}

    def plan(self, dataset, _sources, force_rebuild=False):
        return "a" * 64

    def build(self, dataset, generation):
        self.builds.append((dataset, generation))

    def activate(self, dataset, generation):
        self.activations.append((dataset, generation))

    def retention_inventory(self):
        return {"generations": []}


def api_settings(**updates):
    values = {
        "financial_index_admin_token": "correct-secret",
        "financial_index_allow_local_mutations": False,
        "financial_index_max_request_bytes": 16384,
        "financial_index_max_pending_builds": 2,
        "financial_index_force_rebuild_cooldown_seconds": 60,
        "financial_corpus_dir": Path("unused"),
    }
    values.update(updates)
    return SimpleNamespace(**values)


@pytest.fixture
def secured_api(monkeypatch):
    from app.api import financial_index as api
    engine = ApiEngine()
    monkeypatch.setattr(api, "get_index", lambda: engine)
    monkeypatch.setattr(api, "get_settings", lambda: api_settings())
    monkeypatch.setattr(api, "_pending_builds", 0)
    api._last_forced_build.clear()
    app = FastAPI()
    app.include_router(api.router)
    return TestClient(app), engine, api


def test_mutations_default_deny_invalid_valid_and_read_compatibility(secured_api, monkeypatch):
    client, engine, api = secured_api
    payload = {"dataset_id": "test", "generation": "b" * 64}
    monkeypatch.setattr(api, "get_settings", lambda: api_settings(financial_index_admin_token=""))
    assert client.post("/financial-index/activate", json=payload).status_code == 503

    monkeypatch.setattr(api, "get_settings", lambda: api_settings())
    invalid = client.post("/financial-index/activate", json=payload,
                          headers={"Authorization": "Bearer wrong-secret"})
    assert invalid.status_code == 401
    assert "wrong-secret" not in invalid.text
    valid = client.post("/financial-index/activate", json=payload,
                        headers={"Authorization": "Bearer correct-secret"})
    assert valid.status_code == 200
    assert engine.activations == [("test", "b" * 64)]
    read = client.post("/financial-index/search", json={
        "dataset_id": "test", "query": "Revenue", "mode": "bm25"})
    assert read.status_code == 200


def test_mutation_body_validation_queue_and_force_rebuild_cooldown(secured_api, monkeypatch):
    client, engine, api = secured_api
    headers = {"Authorization": "Bearer correct-secret"}
    oversized = client.post("/financial-index/activate", content=b"{}",
                            headers={**headers, "Content-Length": "20000"})
    assert oversized.status_code == 413
    assert client.post("/financial-index/activate", json={
        "dataset_id": "bad/path", "generation": "b" * 64}, headers=headers).status_code == 422
    assert client.post("/financial-index/search", json={
        "dataset_id": "test", "query": "Revenue", "ticker": "../BAD"}).status_code == 422
    assert client.post("/financial-index/search", json={
        "dataset_id": "test", "query": "Revenue",
        "filing_ids": ["not-a-filing"]}).status_code == 422

    monkeypatch.setattr(api, "_pending_builds", 2)
    build = {"dataset_id": "test", "source_dataset_id": "source",
             "manifest_hash": "c" * 64}
    assert client.post("/financial-index/build", json=build, headers=headers).status_code == 429
    monkeypatch.setattr(api, "_pending_builds", 0)
    first = client.post("/financial-index/build", json={**build, "force_rebuild": True}, headers=headers)
    assert first.status_code == 202
    second = client.post("/financial-index/build", json={**build, "force_rebuild": True}, headers=headers)
    assert second.status_code == 429
    assert engine.builds == [("test", "a" * 64)]


def test_loopback_override_is_explicit(secured_api, monkeypatch):
    client, engine, api = secured_api
    monkeypatch.setattr(api, "get_settings", lambda: api_settings(
        financial_index_admin_token="", financial_index_allow_local_mutations=True))
    response = client.post("/financial-index/activate", json={
        "dataset_id": "test", "generation": "d" * 64})
    assert response.status_code == 200
    assert engine.activations


def test_embedded_qdrant_has_cross_process_owner_and_recovers_after_termination(tmp_path):
    root = tmp_path / "owned"
    code = (
        "from pathlib import Path\n"
        "from app.financial_index.ownership import LocalQdrantOwnership\n"
        "lock=LocalQdrantOwnership(Path(__import__('sys').argv[1]))\n"
        "print('READY', flush=True)\n"
        "input()\n"
    )
    process = subprocess.Popen([sys.executable, "-c", code, str(root)], cwd=Path(__file__).parents[1],
                               stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               text=True)
    try:
        assert process.stdout.readline().strip() == "READY"
        with pytest.raises(RuntimeError, match="LOCAL_QDRANT_ALREADY_OWNED"):
            LocalQdrantOwnership(root)
    finally:
        process.terminate()
        process.wait(timeout=10)
        process.stdout.close()
        process.stderr.close()
        process.stdin.close()
    recovered = None
    for _ in range(20):
        try:
            recovered = LocalQdrantOwnership(root)
            break
        except RuntimeError:
            time.sleep(.05)
    assert recovered is not None
    recovered.close()
    assert (root / ".qdrant-owner.lock").exists()  # stale file is not used as ownership proof


def test_server_mode_is_not_blocked_by_local_owner_lock(tmp_path):
    first = FinancialIndex(tmp_path / "server", provider=FakeVectors(), qdrant_url="http://127.0.0.1:6333")
    second = FinancialIndex(tmp_path / "server", provider=FakeVectors(), qdrant_url="http://127.0.0.1:6333")
    first.close()
    second.close()


def test_provenance_cache_hits_and_tampering_never_bypasses_hashes(tmp_path):
    engine, _, _, _, _, pipeline = built(tmp_path)
    first = engine.search("test", "Revenue", "bm25")
    second = engine.search("test", "Revenue", "bm25")
    assert first["provenance_cache"]["misses"] == 1
    assert second["provenance_cache"]["hits"] >= 1
    row = pipeline.registry.list_filings()[0]
    for field in ("raw_path", "structured_path", "chunks_path"):
        path = Path(row[field])
        original = path.read_bytes()
        path.write_bytes(original + b"tamper")
        with pytest.raises(ValueError, match="HASH_MISMATCH"):
            engine.search("test", "Revenue", "bm25")
        path.write_bytes(original)
        assert engine.search("test", "Revenue", "bm25")["results"]
    assert engine.provenance_cache.diagnostics()["invalidations"] >= 1
    engine.close()


def test_provenance_cache_generation_version_eviction_and_single_flight(tmp_path, monkeypatch):
    engine, _, generation, _, _, _ = built(tmp_path, amendment=True)
    sources = {}
    for item in engine.lexical.records(generation):
        sources.setdefault(item["source"]["structured_path"], item["source"])
    frozen = list(sources.values())
    assert len(frozen) == 2
    cache = ProvenanceCache(max_entries=1, max_bytes=64 * 1024 * 1024)
    verified_source(frozen[0], cache=cache, generation="g1")
    verified_source(frozen[1], cache=cache, generation="g1")
    assert cache.diagnostics()["evictions"] == 1
    verified_source(frozen[0], cache=cache, generation="g2")
    assert cache.diagnostics()["misses"] == 3

    from app.financial_index import corpus
    fresh = ProvenanceCache(max_entries=4, max_bytes=64 * 1024 * 1024)
    calls = 0
    original_parse = corpus.parse_sec_html

    def counted(*args, **kwargs):
        nonlocal calls
        calls += 1
        time.sleep(.05)
        return original_parse(*args, **kwargs)

    monkeypatch.setattr(corpus, "parse_sec_html", counted)
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: verified_source(
            frozen[0], cache=fresh, generation="concurrent"), range(4)))
    assert calls == 1
    assert all(results[0].keys() == result.keys() for result in results)
    assert fresh.diagnostics()["waits"] >= 1
    engine.close()


def test_provenance_toctou_change_is_detected_and_recovery_is_possible(tmp_path, monkeypatch):
    engine, _, generation, _, _, _ = built(tmp_path)
    frozen = next(engine.lexical.records(generation))["source"]
    raw_path = Path(frozen["raw_path"])
    original = raw_path.read_bytes()
    from app.financial_index import corpus
    original_reader = corpus._verified_bytes
    changed = False

    def racing(path, expected):
        nonlocal changed
        data = original_reader(path, expected)
        if Path(path) == raw_path and not changed:
            changed = True
            raw_path.write_bytes(original + b"race")
        return data

    monkeypatch.setattr(corpus, "_verified_bytes", racing)
    cache = ProvenanceCache()
    with pytest.raises(ValueError, match="SOURCE_CHANGED_DURING_VERIFICATION"):
        verified_source(frozen, cache=cache, generation=generation)
    raw_path.write_bytes(original)
    monkeypatch.setattr(corpus, "_verified_bytes", original_reader)
    assert verified_source(frozen, cache=cache, generation=generation)
    engine.close()


def test_retention_protects_active_pin_evaluation_and_rollback_and_recovers_cleanup(tmp_path, monkeypatch):
    from app.config import get_settings
    settings = get_settings()
    monkeypatch.setattr(settings, "financial_index_retained_ready", 1)
    monkeypatch.setattr(settings, "financial_index_rollback_generations", 1)
    engine, _, first, _, specs, pipeline = built(tmp_path)
    generations = [first]
    for _ in range(3):
        generation = engine.plan("test", specs, force_rebuild=True)
        engine.build("test", generation)
        generations.append(generation)
    inventory = {item["generation"]: item for item in engine.retention_inventory()["generations"]}
    assert not inventory[generations[-1]]["cleanup_eligible"]
    assert "active" in inventory[generations[-1]]["protected_reasons"]
    assert "required_rollback" in inventory[generations[-2]]["protected_reasons"]
    assert inventory[generations[0]]["cleanup_eligible"]

    engine.protect_generation("test", generations[0], "pin", "owner")
    assert not {item["generation"]: item for item in engine.retention_inventory()["generations"]}[
        generations[0]]["cleanup_eligible"]
    engine.unprotect_generation("test", generations[0], "pin", "owner")
    engine.protect_generation("test", generations[0], "evaluation", "frozen-eval-v1")
    with pytest.raises(ValueError, match="PROTECTED"):
        engine.cleanup_generations([generations[0]], apply=True)
    engine.unprotect_generation("test", generations[0], "evaluation", "frozen-eval-v1")

    raw = Path(pipeline.registry.list_filings()[0]["raw_path"])
    raw_hash = raw.read_bytes()
    collection = inventory[generations[0]]["collection"]
    with pytest.raises(RuntimeError, match="CONTROLLED_CLEANUP_INTERRUPTION"):
        engine.cleanup_generations([generations[0]], apply=True, fail_after_dense=True)
    assert engine.lexical.generation("test", generations[0])
    assert not engine.dense.collection_exists(collection)
    result = engine.cleanup_generations([generations[0]], apply=True)
    assert result["deleted"] == [generations[0]]
    with pytest.raises(ValueError, match="NOT_FOUND"):
        engine.lexical.generation("test", generations[0])
    assert raw.read_bytes() == raw_hash
    assert engine.retention_inventory()["recent_cleanup_audit"][0]["state"] == "COMPLETE"
    engine.close()


def test_ollama_identity_is_complete_and_connection_failures_do_not_fallback(monkeypatch):
    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {"models": [{"name": "nomic-embed-text:latest", "digest": "digest",
                                "details": {"embedding_length": 768}}]}

    class Session:
        def get(self, *_args, **_kwargs):
            return Response()

        def post(self, *_args, **_kwargs):
            raise requests.Timeout("timeout")

        def close(self):
            pass

    provider = OllamaVectors(session=Session())
    identity = provider.identity()
    assert identity["model"] == "nomic-embed-text:latest"
    assert identity["digest"] == "digest" and identity["dimension"] == 768
    assert identity["document_prefix"] == "search_document: "
    assert identity["query_prefix"] == "search_query: "
    assert identity["normalization_policy"]
    with pytest.raises(requests.Timeout):
        provider.embed_query("Revenue")


def test_windows_path_preflight_is_actionable():
    ensure_path_capacity(Path("C:/short"), Path("ok/file.json"), platform="nt")
    with pytest.raises(ValueError, match="WINDOWS_PATH_CAPACITY_EXCEEDED"):
        ensure_path_capacity(Path("C:/") / ("x" * 300), Path("nested/file.json"), platform="nt")
