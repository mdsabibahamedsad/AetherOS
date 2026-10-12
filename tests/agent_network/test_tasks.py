"""Remote task state machine + persistence (sections 23-27, 34-37, 102-103)."""

import pytest

from aetheros_network.tasks import TaskStore, new_task


def _store(tmp_path):
    return TaskStore(tmp_path / "tasks.sqlite")


def test_full_lifecycle(tmp_path):
    store = _store(tmp_path)
    task = new_task("local", "aetheros:ext:1", "summarize this")
    assert task.status == "discovered"
    assert task.origin_agent and task.owner is not None
    assert task.idempotency_key
    store.save(task)
    for state in ("proposed", "authorized", "submitted", "accepted",
                  "running", "completed"):
        task = store.transition(task.task_id, state)
    assert task.status == "completed"
    assert len(task.events) >= 6


def test_illegal_transition_rejected(tmp_path):
    store = _store(tmp_path)
    task = new_task("local", "a:1", "x")
    store.save(task)
    with pytest.raises(ValueError, match="not allowed"):
        store.transition(task.task_id, "completed")


def test_terminal_states_have_no_outgoing(tmp_path):
    store = _store(tmp_path)
    task = new_task("local", "a:1", "x")
    store.save(task)
    store.transition(task.task_id, "cancelled")
    with pytest.raises(ValueError, match="not allowed"):
        store.transition(task.task_id, "running")


def test_every_task_has_owner_and_origin(tmp_path):
    store = _store(tmp_path)
    task = new_task("local:cli", "a:1", "x", owner="cli")
    store.save(task)
    loaded = store.get(task.task_id)
    assert loaded.origin_agent == "local:cli"
    assert loaded.owner == "cli"


def test_idempotency_lookup(tmp_path):
    store = _store(tmp_path)
    task = new_task("local", "a:1", "x")
    store.save(task)
    found = store.find_by_idempotency(task.idempotency_key)
    assert found is not None and found.task_id == task.task_id


def test_queue_depth_bounded(tmp_path):
    store = TaskStore(tmp_path / "t.sqlite", max_queued=2)
    for i in range(3):
        t = new_task("local", "a:1", f"t{i}")
        store.save(t)
    q = store.queue_depth()
    assert q["queued"] == 3
    assert q["full"] is True


def test_reconcile_adopts_legal_remote_state(tmp_path):
    store = _store(tmp_path)
    task = new_task("local", "a:1", "x")
    store.save(task)
    for s in ("proposed", "authorized", "submitted", "accepted", "running"):
        store.transition(task.task_id, s)
    task = store.reconcile(task.task_id, "completed")
    assert task.status == "completed"


def test_reconcile_never_fabricates_progress(tmp_path):
    store = _store(tmp_path)
    task = new_task("local", "a:1", "x")
    store.save(task)
    task = store.reconcile(task.task_id, "completed")  # illegal jump
    assert task.status == "discovered"


def test_persistence_across_restart(tmp_path):
    path = tmp_path / "t.sqlite"
    s1 = TaskStore(path)
    task = new_task("local", "a:1", "survive restart")
    s1.save(task)
    s2 = TaskStore(path)
    loaded = s2.get(task.task_id)
    assert loaded is not None and loaded.purpose == "survive restart"
