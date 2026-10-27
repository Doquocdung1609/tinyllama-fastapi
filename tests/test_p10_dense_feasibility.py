"""Small offline guards for opt-in P10 research artifacts."""
import json
from types import SimpleNamespace

import pytest

from scripts import p10_hybrid_handshake as handshake
from scripts.p10_build_isolated_vectors import point_id


def test_parent_point_identity_is_stable_and_distinct():
    assert point_id("parent-a") == point_id("parent-a")
    assert point_id("parent-a") != point_id("parent-b")


@pytest.mark.parametrize("change", [
    {"state": "BUILDING"},
    {"completed_points": 1},
    {"generation": "wrong"},
    {"manifest_hash": "wrong"},
    {"model_digest": "wrong"},
])
def test_development_handshake_refuses_incomplete_or_mixed_generation(
    tmp_path, monkeypatch, change
):
    root = tmp_path / "p7-isolated-review-test"
    vector_root = tmp_path / "t3-p10-isolated-vectors-test"
    root.mkdir()
    vector_root.mkdir()
    identity = {
        "state": "READY", "completed_points": 2, "parent_count": 2,
        "generation": "generation-1", "manifest_hash": "manifest-1",
        "model_digest": handshake.EXPECTED_DIGEST,
    }
    identity.update(change)
    (vector_root / "generation_manifest.json").write_text(json.dumps(identity))
    monkeypatch.setattr(handshake, "FrozenResearchSnapshot", lambda _: SimpleNamespace(
        freeze={"generation": "generation-1", "manifest_hash": "manifest-1"}
    ))
    with pytest.raises(ValueError, match="P10_DENSE_GENERATION_NOT_READY_OR_COMPATIBLE"):
        handshake.run(root, vector_root)
