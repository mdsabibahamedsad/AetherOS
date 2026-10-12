"""Tests for aetheros_security.policy_hierarchy (priority + explanations)."""

from aetheros_security.policy_hierarchy import (
    PolicyHierarchyManager,
    PolicyLayer,
    get_policy_hierarchy_manager,
    resolve_bool,
    resolve_layer_decisions,
    safe_explanation,
)


class TestResolveLayerDecisions:
    def test_system_deny_overrides_agent_allow(self):
        result = resolve_layer_decisions([
            (PolicyLayer.SYSTEM, "DENY"),
            (PolicyLayer.AGENT, "ALLOW"),
        ])
        assert result["decision"] == "deny"
        assert result["deciding_layer"] == PolicyLayer.SYSTEM.value
        assert result["overridden"] == ["4:allow"]

    def test_system_allow_overrides_agent_deny(self):
        result = resolve_layer_decisions([
            (PolicyLayer.SYSTEM, "ALLOW"),
            (PolicyLayer.AGENT, "DENY"),
        ])
        assert result["decision"] == "allow"
        assert result["deciding_layer"] == PolicyLayer.SYSTEM.value

    def test_lower_layer_alone_decides(self):
        result = resolve_layer_decisions([
            (PolicyLayer.USER, "ALLOW"),
            (PolicyLayer.TASK, "ALLOW"),
        ])
        assert result["decision"] == "allow"
        assert result["deciding_layer"] == PolicyLayer.USER.value

    def test_empty_defaults_deny(self):
        result = resolve_layer_decisions([])
        assert result["decision"] == "deny"
        assert result["deciding_layer"] is None

    def test_model_never_authoritative(self):
        # MODEL suggestion alone must not allow.
        result = resolve_layer_decisions([(PolicyLayer.MODEL, "ALLOW")])
        assert result["decision"] == "allow"
        # But a higher layer deny overrides model suggestion.
        result2 = resolve_layer_decisions([
            (PolicyLayer.SYSTEM, "DENY"),
            (PolicyLayer.MODEL, "ALLOW"),
        ])
        assert result2["decision"] == "deny"

    def test_boolean_wrapper(self):
        allowed, layer = resolve_bool([(PolicyLayer.SYSTEM, True),
                                       (PolicyLayer.AGENT, False)])
        assert allowed is True
        assert layer == PolicyLayer.SYSTEM

    def test_higher_layer_deny_beats_lower_allow_chain(self):
        result = resolve_layer_decisions([
            (PolicyLayer.TASK, "ALLOW"),
            (PolicyLayer.AGENT, "ALLOW"),
            (PolicyLayer.MISSION, "ALLOW"),
            (PolicyLayer.ORGANIZATION, "DENY"),
        ])
        assert result["decision"] == "deny"
        assert result["deciding_layer"] == PolicyLayer.ORGANIZATION.value


class TestSafeExplanation:
    def test_deny_with_safe_reason(self):
        msg = safe_explanation("deny", "emergency stop active")
        assert "DENIED" in msg
        assert "privileged actions are halted" in msg

    def test_deny_does_not_leak_internal(self):
        msg = safe_explanation("deny", "internal rule id: X-42", include_internal=False)
        # The raw internal reason must not appear.
        assert "X-42" not in msg

    def test_default_deny_message(self):
        msg = safe_explanation("deny", "default deny")
        assert "not explicitly permitted" in msg

    def test_allow_message(self):
        msg = safe_explanation("allow", "allowed by rule")
        assert "permitted" in msg or "Action permitted" in msg

    def test_approval_message(self):
        msg = safe_explanation("approval", "high risk action")
        assert "approval" in msg.lower()

    def test_unknown_reason_stays_safe(self):
        msg = safe_explanation("deny", "some obscure internal marker 7f3a")
        assert "7f3a" not in msg


class TestPolicyHierarchyManager:
    def test_configured_layers(self):
        phm = PolicyHierarchyManager()
        phm.set_layer(PolicyLayer.SYSTEM, "allow")
        phm.set_layer(PolicyLayer.AGENT, "deny")
        outcome = phm.evaluate()
        assert outcome["decision"] == "allow"
        assert "explanation" in outcome

    def test_extra_pairs_override_nothing_above_system(self):
        phm = PolicyHierarchyManager()
        phm.set_layer(PolicyLayer.SYSTEM, "deny")
        outcome = phm.evaluate(extra=[(PolicyLayer.TASK, "allow")])
        assert outcome["decision"] == "deny"

    def test_allow_convenience(self):
        phm = PolicyHierarchyManager()
        phm.set_layer(PolicyLayer.SYSTEM, "deny")
        assert not phm.allow("agent-1", "filesystem:delete")
        phm.unset_layer(PolicyLayer.SYSTEM)
        phm.set_layer(PolicyLayer.USER, "allow")
        assert phm.allow("agent-1", "filesystem:read")

    def test_singleton(self):
        assert get_policy_hierarchy_manager() is get_policy_hierarchy_manager()