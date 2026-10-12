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
