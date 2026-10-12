"""Tests for aetheros_comm.authz — zero-trust authorization and delegation."""

from __future__ import annotations

import pytest

from aetheros_comm.authz import (AuthorizationContext, MessageAuthorizer,
                                 ScopedPermission, capability_matches)
from aetheros_comm.envelope import AgentMessageEnvelope
from aetheros_comm.identity import AgentIdentity, AgentRegistry, AgentStatus
from aetheros_comm.trust import TrustZonePolicy
from aetheros_comm.types import MessageType, TrustZone


def build_authorizer():
    reg = AgentRegistry()
    reg.register(AgentIdentity(agentId="orch", capabilities=[
        "task:request", "delegation:request", "comm:*"], trustZone="ZONE_4"))
    reg.register(AgentIdentity(agentId="worker", capabilities=[
        "task:request", "repository_read"], trustZone="ZONE_1"))
    reg.register(AgentIdentity(agentId="untrusted", capabilities=[
        "comm:*"], trustZone="ZONE_0"))
    policy = TrustZonePolicy()
    return MessageAuthorizer(reg, policy), reg


def make_env(message_type=MessageType.TASK_REQUEST.value, **overrides):
    data = {"senderAgentId": "orch", "receiverAgentId": "worker",
            "missionId": "m1", "taskId": "t1"}
    data.update(overrides)
    return AgentMessageEnvelope(messageType=message_type, **data)


def ctx(chain, perms=None, mission="m1", task="t1"):
    return AuthorizationContext(principal_chain=list(chain),
                                scoped_permissions=list(perms or []),
                                mission_id=mission, task_id=task)


class TestCapabilityMatch:
    def test_exact_match(self):
        assert capability_matches("repository_read", "repository_read")

    def test_wildcard_prefix(self):
        assert capability_matches("comm:*", "comm:warn")
        assert capability_matches("comm:*", "comm:heartbeat")

    def test_wildcard_does_not_cross_namespace(self):
        assert not capability_matches("comm:*", "repository_read")

    def test_global_wildcard(self):
        assert capability_matches("*", "anything")

    def test_no_match(self):
        assert not capability_matches("repository_read", "repository_write")


class TestIdentityChecks:
    def test_unknown_sender_denied(self):
        authorizer, _ = build_authorizer()
        decision = authorizer.authorize(make_env(senderAgentId="ghost"))
        assert not decision.allowed
        assert decision.code == "UNKNOWN_SENDER"

    def test_inactive_sender_denied(self):
        authorizer, reg = build_authorizer()
        reg.update_status("worker", AgentStatus.SUSPENDED)
        decision = authorizer.authorize(make_env(senderAgentId="worker"))
        assert not decision.allowed
        assert decision.code == "SENDER_NOT_ACTIVE"

    def test_unknown_receiver_denied(self):
        authorizer, _ = build_authorizer()
        decision = authorizer.authorize(make_env(receiverAgentId="ghost"))
        assert not decision.allowed
        assert decision.code == "UNKNOWN_RECEIVER"

    def test_inactive_receiver_denied(self):
        authorizer, reg = build_authorizer()
        reg.update_status("worker", AgentStatus.SUSPENDED)
        decision = authorizer.authorize(make_env())
        assert not decision.allowed
        assert decision.code == "RECEIVER_NOT_ACTIVE"


class TestZoneChecks:
    def test_cross_zone_denied_without_allowance(self):
        authorizer, _ = build_authorizer()
        # untrusted (ZONE_0) -> worker (ZONE_1) requires explicit policy.
        decision = authorizer.authorize(make_env(senderAgentId="untrusted"))
        assert not decision.allowed
        assert decision.code == "CROSS_ZONE_DENIED"

    def test_zone4_sender_ok(self):
        authorizer, _ = build_authorizer()
        decision = authorizer.authorize(make_env(senderAgentId="orch"),
                                        context=ctx(["orch"]))
        assert decision.allowed


class TestCapabilityChecks:
    def test_lacking_capability_denied(self):
        authorizer, _ = build_authorizer()
        decision = authorizer.authorize(
            make_env(senderAgentId="worker",
                     message_type=MessageType.TASK_CANCEL.value))
        assert not decision.allowed
        assert decision.code == "CAPABILITY_DENIED"

    def test_scoped_permissions_authoritative(self):
        authorizer, _ = build_authorizer()
        # worker's base caps lack task:cancel, but a scoped grant provides it.
        scoped = ctx(["orch", "worker"],
                     perms=[ScopedPermission("task:cancel", "*", "read")])
        decision = authorizer.authorize(
            make_env(senderAgentId="worker",
                     message_type=MessageType.TASK_CANCEL.value),
            context=scoped)
        assert decision.allowed

    def test_broadcast_only_when_allowed(self):
        authorizer, _ = build_authorizer()
        env = make_env(message_type=MessageType.TASK_REQUEST.value,
                       receiverAgentId="")
        decision = authorizer.authorize(env)
        assert not decision.allowed
        assert decision.code == "BROADCAST_DENIED"

    def test_broadcast_capable_type_ok(self):
        authorizer, _ = build_authorizer()
        env = make_env(message_type=MessageType.WARNING.value,
                       senderAgentId="orch", receiverAgentId="",
                       missionId="", taskId="")
        decision = authorizer.authorize(env, context=ctx(["orch"]))
        assert decision.allowed


class TestMissionOwnership:
    def test_mission_mismatch_denied(self):
        authorizer, _ = build_authorizer()
        context = ctx(["orch"], mission="m2", task="t1")
        decision = authorizer.authorize(make_env(), context=context)
        assert not decision.allowed
        assert decision.code == "MISSION_MISMATCH"

    def test_task_mismatch_denied(self):
        authorizer, _ = build_authorizer()
        context = ctx(["orch"], mission="m1", task="t2")
        decision = authorizer.authorize(make_env(), context=context)
        assert not decision.allowed
        assert decision.code == "TASK_MISMATCH"

    def test_no_context_no_mission_check(self):
        authorizer, _ = build_authorizer()
        # Non-sensitive message type needs no context, and no mission means
        # no mission ownership check.
        env = make_env(message_type=MessageType.WARNING.value,
                       missionId="", taskId="")
        decision = authorizer.authorize(env)
        assert decision.allowed


class TestSensitiveAndContext:
    def test_sensitive_requires_context(self):
        authorizer, _ = build_authorizer()
        # No mission/task on the envelope so the ownership checks pass
        # trivially and the sensitive-type check is the one that fires.
        decision = authorizer.authorize(
            make_env(missionId="", taskId=""), context=None)
        assert not decision.allowed
        assert decision.code == "NO_AUTHORIZATION_CONTEXT"

    def test_forged_chain_denied(self):
        authorizer, _ = build_authorizer()
        # Chain ends at orch, but the wire sender is worker.
        decision = authorizer.authorize(
            make_env(senderAgentId="worker"), context=ctx(["orch", "worker", "orch"]))
        assert not decision.allowed
        assert decision.code == "CHAIN_MISMATCH"

    def test_sensitive_requires_signature(self):
        authorizer, _ = build_authorizer()
        decision = authorizer.authorize(make_env(), context=ctx(["orch"]),
                                        signature_ok=False)
        assert not decision.allowed
        assert decision.code == "BAD_SIGNATURE"

    def test_sensitive_signed_allowed(self):
        authorizer, _ = build_authorizer()
        decision = authorizer.authorize(make_env(), context=ctx(["orch"]),
                                        signature_ok=True)
        assert decision.allowed


class TestReplayAndPropagation:
    def test_replay_denied(self):
        authorizer, _ = build_authorizer()
        decision = authorizer.authorize(make_env(), context=ctx(["orch"]),
                                        replay_ok=False)
        assert not decision.allowed
        assert decision.code == "REPLAY_REJECTED"

    def test_propagate_never_widens_mode(self):
        parent = AuthorizationContext(
            principal_chain=["user", "orch"],
            scoped_permissions=[ScopedPermission("repository_write", "*", "read")])
        child = parent.propagate("worker", granted_capabilities=["repository_write"])
        assert child.max_mode("repository_write") == "read"

    def test_propagate_filters_to_granted_caps(self):
        parent = AuthorizationContext(
            principal_chain=["user", "orch"],
            scoped_permissions=[ScopedPermission("repository_read", "*", "read"),
                                ScopedPermission("repository_write", "*", "read")])
        child = parent.propagate("worker", granted_capabilities=["repository_read"])
        assert child.grants("repository_read")
        assert not child.grants("repository_write")

    def test_propagate_grows_chain(self):
        parent = AuthorizationContext(principal_chain=["user", "orch"])
        child = parent.propagate("worker")
        assert child.principal_chain == ["user", "orch", "worker"]
        assert child.delegation_depth == 1

    def test_propagate_child_cannot_inherit_unheld(self):
        parent = AuthorizationContext(
            principal_chain=["user", "orch"],
            scoped_permissions=[ScopedPermission("repository_read", "*", "read")])
        child = parent.propagate("worker", granted_capabilities=["repository_write"])
        assert child.max_mode("repository_write") == ""


class TestContextRoundtrip:
    def test_to_from_dict(self):
        context = AuthorizationContext(
            principal_chain=["user", "orch", "worker"],
            scoped_permissions=[ScopedPermission("read", "repo/*", "write")],
            mission_id="m1", task_id="t1", user="alice")
        restored = AuthorizationContext.from_dict(context.to_dict())
        assert restored.principal_chain == context.principal_chain
        assert restored.scoped_permissions[0].capability == "read"
        assert restored.scoped_permissions[0].mode == "write"
        assert restored.user == "alice"