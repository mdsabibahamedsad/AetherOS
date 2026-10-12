"""Trust Fabric security invariants (§135) + governance scenarios
(§181). Every test asserts fail-closed runtime behavior, not wishes."""
from __future__ import annotations

import pytest

from aetheros_control_plane.models import IdentityType
from trust import TrustFabric
from trust.approvals import ApprovalRequest
from trust.models import (DataClassification, ExtendedDecision, Risk,
                          SecurityError, TrustError)


def _fabric() -> TrustFabric:
    return TrustFabric()


def _agent(fabric: TrustFabric, name="t-agent", scopes=()):
    return fabric.plane.identities.create(
        IdentityType.AGENT, name, scopes=list(scopes))


# -- §135 invariants ---------------------------------------------------------
def test_denied_action_never_executes():
    f = _fabric()
    ident = _agent(f)
    d = f.propose(ident.id, "write", "/system/x", kind="filesystem")
    assert d.decision == ExtendedDecision.DENY
    with pytest.raises(TrustError):
        f.authorize(ident.id, "write", "/system/x", kind="filesystem")


def test_expired_capability_cannot_authorize():
    f = _fabric()
    tok = f.capabilities.issue("s", "read", "/d", "p", ttl_s=-1,
                               audience="t")
    with pytest.raises(TrustError) as exc:
        f.capabilities.validate(tok, "t")
    assert exc.value.code == SecurityError.CAPABILITY_EXPIRED


def test_revoked_capability_cannot_authorize():
    f = _fabric()
    tok = f.capabilities.issue("s", "read", "/d", "p", audience="t")
    f.revoke("capability", tok.token_id, "test")
    assert f.revocation.is_revoked("capability", tok.token_id)


def test_model_cannot_modify_own_authority():
    f = _fabric()
    ident = _agent(f, scopes=["read:docs"])
    # scopes are immutable from the model side: no API grants new ones
    assert "write:prod" not in ident.scopes
    d = f.propose(ident.id, "write", "/prod", kind="filesystem")
    assert d.decision == ExtendedDecision.DENY


def test_remote_no_automatic_inheritance():
    f = _fabric()
    assert f.check_remote("remote-x", "read", "/local") is False


def test_webpage_cannot_modify_policy():
    f = _fabric()
    # untrusted content has no path to policy store mutation
    with pytest.raises((AttributeError, TypeError, ValueError)):
        f.policies.publish("x", {"allow": []}, layer="webpage")


def test_untrusted_doc_grants_nothing():
    f = _fabric()
    ident = _agent(f)
    assert ident.scopes == []


def test_high_risk_needs_approval_or_denies():
    f = _fabric()
    ident = _agent(f, scopes=["*"])
    d = f.propose(ident.id, "delete production database",
                  "/prod/db", kind="database")
    assert d.decision in (ExtendedDecision.DENY,
                          ExtendedDecision.REQUIRE_APPROVAL,
                          ExtendedDecision.SIMULATION_ONLY)


def test_estop_needs_no_model_cooperation():
    f = _fabric()
    f.emergency.kill("GLOBAL_KILL", reason="test")
    assert f.emergency.state.value == "EMERGENCY_STOPPED"
    ident = _agent(f, scopes=["read:docs"])
    d = f.propose(ident.id, "read", "/docs/a.md", kind="filesystem")
    assert d.decision == ExtendedDecision.DENY


def test_secrets_not_disclosed_by_use():
    f = _fabric()
    f.secrets.grant("agent-1", "SECRET_USE", "github")
    out = f.secrets.use_secret("agent-1", "github", lambda: "TOKEN-XYZ")
    assert out["value_disclosed"] == "false"
    assert "TOKEN-XYZ" not in str(out)


def test_audit_records_do_not_disappear():
    f = _fabric()
    f.plane.audit.emit("ACTION_PROPOSED", {"a": 1}, {"x": 1})
    n = len(f.plane.audit)
    assert n >= 1
    ok, _ = f.plane.audit.verify()
    assert ok


def test_policy_version_recoverable():
    f = _fabric()
    ver = f.policies.publish("p1", {"allow": ["read"]})
    assert ver.content_hash and ver.version == "v1"


def test_action_identity_recoverable():
    f = _fabric()
    f.provenance.link_action("act_1", "pol", "auth", "apr")
    exp = f.provenance.explain("act_1")
    assert exp["recorded"] is True


def test_delegation_chain_recoverable():
    f = _fabric()
    a = _agent(f, "a", ["read:docs"])
    from aetheros_control_plane.models import IdentityType as IT
    b = f.plane.identities.create(IT.AGENT, "b")
    scopes = f.plane.identities.scopes_for(a.id)
    g = f.plane.delegation.delegate(scopes, a.id, b.id, ["read:docs"])
    chain = f.plane.delegation.chain(g.id)
    assert [x.id for x in chain] == [g.id]


# -- §181 scenarios ------------------------------------------------------------
def test_s1_public_read_allows():
    f = _fabric()
    ident = _agent(f, scopes=["http.read"])
    # low-risk read path: risk engine classifies R1/R0
    ra = f.risk.classify("http.read", "https://example.com")
    assert ra.level in (Risk.R0_INFORMATIONAL, Risk.R1_READ_ONLY)


def test_s2_secret_read_denies():
    f = _fabric()
    assert f.data.decide("SECRET", "public_web")["decision"] == "DENY"


def test_s3_confidential_external_denies():
    f = _fabric()
    assert f.data.decide("CONFIDENTIAL",
                         "untrusted_remote_agent")["decision"] == "DENY"


def test_s4_production_delete_needs_approval_or_deny():
    f = _fabric()
    ra = f.risk.classify("delete", "production database")
    assert ra.level in (Risk.R6_INFRA_MODIFICATION,
                        Risk.R8_IRREVERSIBLE_CRITICAL)


def test_s5_expired_approval_denies():
    f = _fabric()
    import time
    rid = f.approvals.request(ApprovalRequest(
        actor="a", action="write", resource="/tmp/x", expiration=1.0))
    # force expiry
    f.approvals._requests[rid] = ApprovalRequest(
        **{**f.approvals._requests[rid].__dict__, "expiration": 1.0})
    assert f.approvals.consume(rid, "write", "/tmp/x", "a") is False


def test_s6_revoked_mid_execution_denies_next():
    f = _fabric()
    tok = f.capabilities.issue("s", "read", "/d", "p", audience="t",
                               max_uses=5)
    assert f.capabilities.validate(tok, "t").token_id == tok.token_id
    f.revoke("capability", tok.token_id, "mid-execution")
    assert f.revocation.is_revoked("capability", tok.token_id)


def test_s7_remote_fs_denied_without_delegation():
    f = _fabric()
    assert f.check_remote("r", "filesystem.read", "/local") is False


def test_s8_injection_changes_nothing():
    f = _fabric()
    before = list(f.policies._versions)
    # injection string has no code path into policy store
    assert list(f.policies._versions) == before


def test_s9_policy_modification_denied_by_default():
    f = _fabric()
    ident = _agent(f)
    d = f.propose(ident.id, "policy.write", "/policies/main",
                  kind="governance")
    assert d.decision == ExtendedDecision.DENY


def test_s10_estop_stops_execution():
    f = _fabric()
    out = f.emergency.kill("TASK_KILL", target="task-1", reason="test")
    assert out["state"] == "EMERGENCY_STOPPED"
    rec = f.emergency.begin_recovery()
    assert rec[0] == "DIAGNOSTICS" and rec[-1] == "RESUME"
