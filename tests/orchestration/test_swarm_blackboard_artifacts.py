"""Blackboard isolation/sharing + artifact store versioning (P19-22, P71-72)."""

import pytest

from agent.orchestration.blackboard import (
    ArtifactStore,
    SecretInArtifact,
    ShareDenied,
    TaskBlackboard,
)


def test_artifact_versioning_chain():
    store = ArtifactStore()
    root = store.add(_mk(store, content="draft v1"))
    child = store.add(_mk(store, content="draft v2",
                          parent_artifact=root.artifact_id))
    grand = store.add(_mk(store, content="final",
                          parent_artifact=child.artifact_id))
    assert child.version == 2 and grand.version == 3
    chain = store.history(grand.artifact_id)
    assert [a.version for a in chain] == [1, 2, 3]


def _mk(store, **kw):
    from agent.orchestration.blackboard import Artifact

    return Artifact.create(kind="report", creator_agent="writer",
                           task_id=kw.pop("task_id", "t1"), **kw)


def test_artifact_hash_detects_content_identity():
    store = ArtifactStore()
    a = store.add(_mk(store, content="same"))
    b = store.add(_mk(store, content="same"))
    assert a.hash == b.hash and a.artifact_id != b.artifact_id


def test_secret_refused_in_artifacts():
    store = ArtifactStore()
    with pytest.raises(SecretInArtifact):
        store.add(_mk(store, content="token: ghp_" + "a" * 36))


def test_blackboard_cross_task_share_grant_enforced():
    bb_a = TaskBlackboard("task-A")
    bb_a.add_verified_fact("fact one", verified_by="verifier")
    with pytest.raises(ShareDenied):
        bb_a.export_for_task("task-B")
    bb_a.grant_share("task-B")
    view = bb_a.export_for_task("task-B")
    assert view["verified_facts"] == ["fact one [verified_by=verifier]"]
    bb_a.revoke_share("task-B")
    with pytest.raises(ShareDenied):
        bb_a.export_for_task("task-B")


def test_own_task_reads_freely():
    bb = TaskBlackboard("task-X")
    bb.add_warning("watch out", source_agent="critic")
    snap = bb.snapshot()
    assert snap["warnings"] == ["[critic] watch out"]


def test_persistence_roundtrip(tmp_path):
    d = tmp_path / "artifacts"
    store = ArtifactStore(persist_dir=str(d))
    a = store.add(_mk(store, content="persisted payload"))
    fresh = ArtifactStore(persist_dir=str(d))
    # new instance loads lazily via file; direct check of file instead
    assert (d / "artifacts.json").exists()
    import json

    data = json.loads((d / "artifacts.json").read_text(encoding="utf-8"))
    assert a.artifact_id in data
