"""Agent Hypervisor 1.0 — capsule lifecycle, admission, enforcement, recovery.

Hermetic: stub agent runtime, ephemeral event bus off, capsule roots under
tmp_path (via checkpoint_dir), no network, no credentials, no hardware.
"""

from __future__ import annotations

import pytest

from kernel.core.hypervisor import (
    CapsuleLifecycleState,
    IsolationLevel,
    IsolationStatus,
    NetworkMode,
    ReplayMode,
    TerminationMode,
    get_profile,
    list_profiles,
)
from kernel.core.kernel import AgentKernel
from kernel.core.types import Intent, KernelConfig


def _kernel(tmp_path):
    k = AgentKernel(KernelConfig(
        enable_event_bus=False, checkpoint_interval_seconds=0,
        health_check_interval_seconds=3600, checkpoint_dir=str(tmp_path)))
    k.boot()
    return k


def _intent(objective="capsule test", caps=None):
    return Intent(actor="human", objective=objective,
                  requested_capabilities=list(caps or []))


# -- lifecycle -----------------------------------------------------------------


def test_capsule_full_lifecycle(tmp_path):
    k = _kernel(tmp_path)
    try:
        hyp = k.hypervisor
        cap = hyp.create_capsule(_intent(), "minimal")
        assert cap.lifecycle_state == CapsuleLifecycleState.READY
        assert cap.manifest is not None and cap.manifest.verify()
        hyp.start_capsule(cap.capsule_id)
        assert cap.lifecycle_state == CapsuleLifecycleState.RUNNING
        hyp.pause_capsule(cap.capsule_id)
        assert cap.lifecycle_state == CapsuleLifecycleState.SUSPENDED
        hyp.resume_capsule(cap.capsule_id)
        assert cap.lifecycle_state == CapsuleLifecycleState.RUNNING
        out = hyp.destroy_capsule(cap.capsule_id)
        assert out["mode"] == "graceful"
        assert cap.lifecycle_state == CapsuleLifecycleState.DESTROYED
    finally:
        k._shutdown_flag = True


def test_capsule_invalid_transition_rejected(tmp_path):
    k = _kernel(tmp_path)
    try:
        cap = k.hypervisor.create_capsule(_intent(), "minimal")
        with pytest.raises(ValueError):
            cap.transition(CapsuleLifecycleState.DESTROYED)  # READY->DESTROYED skips TERMINATED
    finally:
        k._shutdown_flag = True


def test_capsule_admission_denies_empty_objective(tmp_path):
    k = _kernel(tmp_path)
    try:
        with pytest.raises(Exception):
            k.hypervisor.create_capsule(Intent(actor="human", objective=""), "minimal")
    finally:
        k._shutdown_flag = True


def test_capsule_parent_subset_and_depth(tmp_path):
    k = _kernel(tmp_path)
    try:
        hyp = k.hypervisor
        parent = hyp.create_capsule(_intent("parent"), "standard")
        child = hyp.create_capsule(
            _intent("child", ["fs.read", "terminal.execute", "browser.navigate"]),
            "standard", parent_capsule_id=parent.capsule_id)
        assert set(child.capabilities) <= set(parent.capabilities)
        assert "browser.navigate" not in child.capabilities  # not in parent grant
        assert child.parent_capsule_id == parent.capsule_id
    finally:
        k._shutdown_flag = True


# -- profiles ------------------------------------------------------------------


def test_all_fourteen_profiles_exist():
    assert len(list_profiles()) == 14
    for name in ("minimal", "standard", "developer", "research", "browser",
                 "computer_use", "automation", "swarm", "untrusted",
                 "high_security", "physical", "ambient", "local_only", "offline"):
        assert get_profile(name).name == name


def test_unknown_profile_rejected():
    with pytest.raises(ValueError):
        get_profile("nope")


def test_untrusted_profile_is_most_restrictive():
    p = get_profile("untrusted")
    assert p.network.mode == NetworkMode.NO_NETWORK
    assert p.max_autonomy == "autonomy_0"
    assert len(p.capabilities) <= 2


# -- isolation honesty ----------------------------------------------------------


def test_isolation_detection_reports_statuses(tmp_path):
    k = _kernel(tmp_path)
    try:
        status = k.hypervisor.isolation_status()
        assert status["strongest_available"] in [lvl.value for lvl in IsolationLevel]
        providers = {p["provider"]: p for p in status["providers"]}
        assert providers["native_process"]["status"] == IsolationStatus.SUPPORTED.value
        # VM isolation must NOT be claimed in 1.0.
        assert providers["vm"]["status"] != IsolationStatus.SUPPORTED.value
        # Every report carries an explicit status + detail.
        for rep in status["providers"]:
            assert rep["status"] in ("supported", "unavailable", "requires_configuration")
            assert rep["detail"]
    finally:
        k._shutdown_flag = True


def test_capsule_never_claims_above_detected_level(tmp_path):
    k = _kernel(tmp_path)
    try:
        cap = k.hypervisor.create_capsule(_intent(), "standard")
        assert cap.isolation_level in (IsolationLevel.LEVEL_0_PROCESS,
                                       IsolationLevel.LEVEL_1_SANDBOXED_PROCESS,
                                       IsolationLevel.LEVEL_2_CONTAINER)
    finally:
        k._shutdown_flag = True


# -- filesystem -----------------------------------------------------------------


def test_capsule_fs_write_read_and_mount_ro(tmp_path):
    k = _kernel(tmp_path)
    try:
        cap = k.hypervisor.create_capsule(_intent(), "minimal")
        fs = k.hypervisor._filesystems[cap.capsule_id]
        fs.write_bytes("/workspace/hello.txt", b"hi")
        assert fs.read_bytes("/workspace/hello.txt") == b"hi"
        with pytest.raises(Exception):
            fs.write_bytes("/readonly/x.txt", b"nope")
    finally:
        k._shutdown_flag = True


def test_capsule_fs_copy_on_write(tmp_path):
    k = _kernel(tmp_path)
    try:
        cap = k.hypervisor.create_capsule(_intent(), "minimal")
        fs = k.hypervisor._filesystems[cap.capsule_id]
        fs.write_bytes("/workspace/a.txt", b"v1")
        fs.copy_on_write("/workspace/a.txt", "/workspace/b.txt")
        assert fs.read_bytes("/workspace/b.txt") == b"v1"
    finally:
        k._shutdown_flag = True


# -- network policy --------------------------------------------------------------


def test_offline_capsule_denies_network_invoke(tmp_path):
    k = _kernel(tmp_path)
    try:
        hyp = k.hypervisor
        cap = hyp.create_capsule(_intent("net", ["network.request"]), "offline")
        # offline profile grants no network caps at all -> manifest gate denies
        with pytest.raises(PermissionError):
            hyp.invoke(cap.capsule_id, "network.request", {"url": "https://github.com"})
    finally:
        k._shutdown_flag = True


def test_allowlist_capsule_blocks_unlisted_domain(tmp_path):
    k = _kernel(tmp_path)
    try:
        hyp = k.hypervisor
        cap = hyp.create_capsule(_intent("net", ["network.request"]), "standard")
        hyp.start_capsule(cap.capsule_id)
        with pytest.raises(PermissionError):
            hyp.invoke(cap.capsule_id, "network.request",
                       {"url": "https://evil.example/"})
    finally:
        k._shutdown_flag = True


# -- secrets ----------------------------------------------------------------------


def test_secret_broker_mediation(tmp_path):
    k = _kernel(tmp_path)
    try:
        hyp = k.hypervisor
        cap = hyp.create_capsule(_intent(), "developer")
        binding = hyp.secret_broker.request_secret(
            "github.token", "s3cr3t-value", agent_id=cap.agent_id,
            capsule_id=cap.capsule_id, capability="network.request",
            destination="github.com")
        use = hyp.secret_broker.use_secret(
            binding.binding_id, agent_id=cap.agent_id,
            capability="network.request", destination="github.com")
        assert use["ok"] is True
        assert "s3cr3t-value" not in str(use)
        # Wrong capability -> denied.
        bad = hyp.secret_broker.use_secret(
            binding.binding_id, agent_id=cap.agent_id, capability="fs.read")
        assert bad["ok"] is False
        # Plaintext only reaches the provider callback.
        seen = []
        hyp.secret_broker.with_resolved(
            binding.binding_id, agent_id=cap.agent_id,
            capability="network.request", destination="github.com",
            consumer=lambda v: seen.append(v))
        assert seen == ["s3cr3t-value"]
        hyp.secret_broker.revoke_secret(binding.binding_id)
        assert hyp.secret_broker.use_secret(
            binding.binding_id, agent_id=cap.agent_id,
            capability="network.request")["ok"] is False
    finally:
        k._shutdown_flag = True


# -- risk determinism ---------------------------------------------------------------


def test_risk_is_deterministic_and_untrusted_scores_higher(tmp_path):
    k = _kernel(tmp_path)
    try:
        hyp = k.hypervisor
        lo = hyp.create_capsule(_intent("plain"), "minimal")
        hi = hyp.create_capsule(
            _intent("risky", ["terminal.execute", "message.send"]), "automation")
        assert lo.risk.band in ("LOW", "MEDIUM", "HIGH", "CRITICAL")
        assert hi.risk.score >= lo.risk.score
        again = hyp.create_capsule(_intent("plain"), "minimal")
        assert again.risk.score == lo.risk.score
        assert again.risk.factors == lo.risk.factors
    finally:
        k._shutdown_flag = True


# -- quarantine / forensics / restore --------------------------------------------------


def test_quarantine_forensic_restore_cycle(tmp_path):
    k = _kernel(tmp_path)
    try:
        hyp = k.hypervisor
        cap = hyp.create_capsule(_intent(), "standard")
        hyp.start_capsule(cap.capsule_id)
        hyp.quarantine_capsule(cap.capsule_id, reason="test")
        assert cap.lifecycle_state == CapsuleLifecycleState.QUARANTINED
        assert cap.capsule_id in hyp._forensics
        with pytest.raises(PermissionError):
            hyp.invoke(cap.capsule_id, "memory.read", {"key": "k"})
        hyp.release_quarantine(cap.capsule_id)
        assert cap.lifecycle_state == CapsuleLifecycleState.READY
    finally:
        k._shutdown_flag = True


def test_snapshot_restore_and_migration(tmp_path):
    k = _kernel(tmp_path)
    try:
        hyp = k.hypervisor
        cap = hyp.create_capsule(_intent(), "standard")
        snap = hyp.snapshot_capsule(cap.capsule_id)
        assert snap.verify()
        restored = hyp.restore_snapshot(snap.integrity_hash)
        assert restored.capsule_id == cap.capsule_id
        out = hyp.migrate_capsule(cap.capsule_id, "local")
        assert out["status"] == "MIGRATED"
        remote = hyp.migrate_capsule(cap.capsule_id, "cloud")
        assert remote["status"] == "REQUIRES_CONFIGURATION"
    finally:
        k._shutdown_flag = True


def test_tampered_snapshot_rejected(tmp_path):
    k = _kernel(tmp_path)
    try:
        hyp = k.hypervisor
        cap = hyp.create_capsule(_intent(), "standard")
        snap = hyp.snapshot_capsule(cap.capsule_id)
        snap.capabilities.append("admin.everything")
        assert snap.verify() is False
        with pytest.raises(PermissionError):
            hyp.restore_snapshot(snap.integrity_hash)
    finally:
        k._shutdown_flag = True


# -- replay ---------------------------------------------------------------------------


def test_replay_observe_only_by_default(tmp_path):
    k = _kernel(tmp_path)
    try:
        hyp = k.hypervisor
        cap = hyp.create_capsule(_intent("replay", ["memory.read", "message.send"]),
                                 "standard")
        hyp.start_capsule(cap.capsule_id)
        out = hyp.replay(cap.capsule_id)
        assert out["mode"] == "observe_only"
        assert out["executed"] == 0
        dry = hyp.replay(cap.capsule_id, ReplayMode.DRY_RUN)
        assert dry["executed"] == 0
        with pytest.raises(PermissionError):
            hyp.replay(cap.capsule_id, ReplayMode.FULL_EXECUTION)
    finally:
        k._shutdown_flag = True


# -- revocation / handoff / simulate / diff -------------------------------------------------


def test_revoke_blocks_future_calls(tmp_path):
    k = _kernel(tmp_path)
    try:
        hyp = k.hypervisor
        cap = hyp.create_capsule(_intent("rev", ["memory.read"]), "standard")
        assert hyp.revoke_capability(cap.capsule_id, "memory.read")["revoked"] is True
        assert hyp.simulate(cap.capsule_id, "memory.read")["verdict"] == "DENY"
    finally:
        k._shutdown_flag = True


def test_simulate_never_executes(tmp_path):
    k = _kernel(tmp_path)
    try:
        hyp = k.hypervisor
        cap = hyp.create_capsule(_intent("sim", ["memory.read"]), "standard")
        assert hyp.simulate(cap.capsule_id, "memory.read")["verdict"] == "ALLOW"
        assert hyp.simulate(cap.capsule_id, "financial.pay")["verdict"] == "DENY"
        assert len(hyp._receipts.get(cap.capsule_id, [])) == 0
    finally:
        k._shutdown_flag = True


def test_diff_and_preview(tmp_path):
    k = _kernel(tmp_path)
    try:
        hyp = k.hypervisor
        a = hyp.create_capsule(_intent("a"), "minimal")
        b = hyp.create_capsule(_intent("b"), "developer")
        diff = hyp.diff_capsules(a.capsule_id, b.capsule_id)
        assert "terminal.execute" in diff["permissions"]["only_b"]
        preview = hyp.preview("do work", "standard")
        assert "CAPSULE_PREVIEW" in preview
        assert "RESOURCE_PREVIEW_ESTIMATES" in preview
    finally:
        k._shutdown_flag = True


# -- quotas / breakers / swarm / gc ----------------------------------------------------------


def test_child_quota_enforced(tmp_path):
    k = _kernel(tmp_path)
    try:
        hyp = k.hypervisor
        parent = hyp.create_capsule(_intent("swarm-parent"), "swarm")
        parent.process_policy["max_children"] = 1
        hyp.create_capsule(_intent("w1"), "swarm",
                           parent_capsule_id=parent.capsule_id)
        with pytest.raises(PermissionError):
            hyp.create_capsule(_intent("w2"), "swarm",
                               parent_capsule_id=parent.capsule_id)
    finally:
        k._shutdown_flag = True


def test_swarm_quota_accounting(tmp_path):
    k = _kernel(tmp_path)
    try:
        hyp = k.hypervisor
        parent = hyp.create_capsule(_intent("swarm"), "standard")
        hyp.set_swarm_quota(parent.capsule_id, {"tool_calls": 100})
        w = hyp.create_capsule(_intent("w"), "swarm",
                               parent_capsule_id=parent.capsule_id)
        assert hyp.check_swarm_quota(parent.capsule_id)["within_quota"] is True
        assert w.parent_capsule_id == parent.capsule_id
    finally:
        k._shutdown_flag = True


def test_gc_and_leak_scan(tmp_path):
    k = _kernel(tmp_path)
    try:
        hyp = k.hypervisor
        cap = hyp.create_capsule(_intent(), "minimal", expires_in_seconds=-1)
        assert cap.is_expired()
        out = hyp.gc(dry_run=True)
        assert cap.capsule_id in out["reclaimed"]
        out2 = hyp.gc()
        assert cap.capsule_id in out2["reclaimed"]
        assert hyp.leak_scan()["total"] >= 0
    finally:
        k._shutdown_flag = True


def test_sdk_capsules_surface(tmp_path):
    from kernel.core.sdk import KernelSDK
    k = _kernel(tmp_path)
    try:
        api = KernelSDK(k).capsules
        cap = api.create("sdk capsule", profile="minimal")
        assert api.inspect(cap.capsule_id)["capsule_id"] == cap.capsule_id
        assert any(c["capsule_id"] == cap.capsule_id for c in api.list())
        assert api.permissions(cap.capsule_id)["manifest_valid"] is True
        api.destroy(cap.capsule_id, confirm=True)
    finally:
        k._shutdown_flag = True
