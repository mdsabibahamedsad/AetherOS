"""IPC validation: every method rejects malformed input (sections 130-131)."""

import pytest

from aetheros_network.ipc import IPC_METHODS


def test_all_required_methods_present():
    for name in ("agent.network.list", "agent.network.discover",
                 "agent.network.info", "agent.network.verify",
                 "agent.network.trust", "agent.network.block",
                 "agent.network.revoke", "agent.network.connect",
                 "agent.network.disconnect", "agent.network.delegate",
                 "agent.network.tasks", "agent.network.cancel",
                 "agent.network.activity", "agent.network.security"):
        assert name in IPC_METHODS, name


def test_info_rejects_bad_agent_id():
    with pytest.raises(ValueError, match="invalid agent id"):
        IPC_METHODS["agent.network.info"]({"id": "../../etc"})


def test_discover_rejects_non_https():
    with pytest.raises(ValueError, match="https://"):
        IPC_METHODS["agent.network.discover"]({"url": "file:///etc/passwd"})


def test_trust_rejects_unknown_level():
    with pytest.raises(ValueError, match="invalid trust level"):
        IPC_METHODS["agent.network.trust"]({"id": "aetheros:x:1", "level": "mega"})


def test_delegate_rejects_empty_task():
    with pytest.raises(ValueError, match="purpose"):
        IPC_METHODS["agent.network.delegate"]({"id": "aetheros:x:1", "task": ""})


def test_delegate_rejects_bad_scope():
    with pytest.raises(ValueError, match="data_scope"):
        IPC_METHODS["agent.network.delegate"](
            {"id": "aetheros:x:1", "task": "hi", "data_scope": "cosmic"})


def test_cancel_requires_task_id():
    with pytest.raises(ValueError, match="task id required"):
        IPC_METHODS["agent.network.cancel"]({})


def test_activity_rejects_bad_limit():
    with pytest.raises(ValueError, match="integer"):
        IPC_METHODS["agent.network.activity"]({"limit": "many"})


def test_list_and_security_run_against_temp_home(tmp_path, monkeypatch):
    monkeypatch.setenv("AETHEROS_HOME", str(tmp_path))
    out = IPC_METHODS["agent.network.list"]({})
    assert out["agents"] == []
    sec = IPC_METHODS["agent.network.security"]({})
    assert sec["trusted"] == 0 and sec["blocked"] == 0
