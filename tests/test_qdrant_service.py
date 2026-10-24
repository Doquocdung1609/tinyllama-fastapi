from concurrent.futures import ThreadPoolExecutor
import sys
import time
from types import SimpleNamespace

from app.services import qdrant_service


def test_concurrent_first_access_constructs_one_local_client(monkeypatch, tmp_path):
    calls = []

    class FakeClient:
        def __init__(self, **kwargs):
            calls.append(kwargs)
            time.sleep(0.05)

    monkeypatch.setattr(qdrant_service, "_client", None)
    monkeypatch.setattr(qdrant_service.get_settings(), "qdrant_url", "")
    monkeypatch.setattr(qdrant_service.get_settings(), "qdrant_path", tmp_path)
    monkeypatch.setitem(sys.modules, "qdrant_client", SimpleNamespace(QdrantClient=FakeClient))

    with ThreadPoolExecutor(max_workers=8) as pool:
        clients = list(pool.map(lambda _: qdrant_service.get_client(), range(8)))

    assert len(calls) == 1
    assert all(client is clients[0] for client in clients)


def test_search_builds_document_and_metadata_prefilter(monkeypatch):
    captured = {}

    class FakeClient:
        def collection_exists(self, name):
            return True

        def query_points(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(points=[])

    monkeypatch.setattr(qdrant_service, "get_client", lambda: FakeClient())
    qdrant_service.search([.1, .2], 10, ["doc-a", "doc-b"],
                           {"ticker": "ABC", "fiscal_year": 2024})

    conditions = captured["query_filter"].must
    assert {condition.key for condition in conditions} == {
        "document_id", "metadata.ticker", "metadata.fiscal_year"}
    values = {condition.key: condition.match.value for condition in conditions
              if condition.key.startswith("metadata.")}
    assert values == {"metadata.ticker": "ABC", "metadata.fiscal_year": 2024}


def test_search_supports_multiple_exact_metadata_spellings(monkeypatch):
    captured = {}

    class FakeClient:
        def collection_exists(self, name):
            return True

        def query_points(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(points=[])

    monkeypatch.setattr(qdrant_service, "get_client", lambda: FakeClient())
    qdrant_service.search([.1], 5, ["doc-a"], {"form_type": ["10-K", "10-k"]})
    condition = next(item for item in captured["query_filter"].must
                     if item.key == "metadata.form_type")
    assert condition.match.any == ["10-K", "10-k"]
