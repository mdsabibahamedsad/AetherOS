"""
Tests for the Aetheros Enterprise Foundation package.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from enterprise.organization import (
    Organization, OrganizationMember, OrganizationRole,
    OrganizationSettings, OrganizationStatus, OrganizationStore,
)
from enterprise.workspace import Workspace, WorkspaceStatus, WorkspaceSettings, WorkspaceStore
from enterprise.teams import Team, TeamMember, TeamRole
from enterprise.users import User, UserStatus, Group, ServiceAccount, APIToken
from enterprise.invitations import Invitation, InvitationStatus, InvitationManager
from enterprise.rbac import (
    RBACManager, Role, Permission, RoleBinding,
    BUILTIN_ROLES,
    PERM_ADMIN_USERS, PERM_ENGINEERING_READ,
    PERM_MEMORY_READ, PERM_CLUSTER_READ,
)
from enterprise.policy_engine import (
    Policy, PolicyRule, PolicyEngine, PolicyDecision, PolicyEvaluation,
)
from enterprise.audit import AuditLog, AuditEvent, AuditExporter
from enterprise.approvals import (
    ApprovalRequest, ApprovalStep, ApprovalStatus,
    ApprovalWorkflow, ApprovalManager,
)
from enterprise.secrets import SecretReference, SecretProviderType, SecretManager
from enterprise.compliance import (
    ComplianceManager, ComplianceControl, ComplianceControlType,
    RetentionPolicy, ComplianceReport,
)
from enterprise.licensing import License, LicenseFeature, LicenseManager
from enterprise.backup import BackupJob, BackupManager, BackupResult, BackupStatus
from enterprise.recovery import RecoveryManager, RecoveryPlan, RecoveryStep
from enterprise.high_availability import HACluster, HANode, NodeStatus, FailoverStrategy
from enterprise.observability import ObservabilityHub, MetricType, EnterpriseMetric
from enterprise.governance import GovernanceFramework, GovernancePolicy, ComplianceRequirement


# ===========================================================================
# Organization Tests
# ===========================================================================

class TestOrganization:
    def test_create(self):
        org = Organization(name="test-org")
        assert org.name == "test-org"
        assert org.status == OrganizationStatus.PENDING
        assert len(org.members) == 0

    def test_activate(self):
        org = Organization(name="test")
        org.activate()
        assert org.status == OrganizationStatus.ACTIVE

    def test_suspend(self):
        org = Organization(name="test")
        org.activate()
        org.suspend()
        assert org.status == OrganizationStatus.SUSPENDED

    def test_add_member(self):
        org = Organization(name="test")
        member = org.add_member("user1", "user1@test.com", OrganizationRole.ADMIN)
        assert org.has_member("user1")
        assert member.role == OrganizationRole.ADMIN

    def test_add_duplicate_member(self):
        org = Organization(name="test")
        org.add_member("user1", "user1@test.com")
        with pytest.raises(ValueError):
            org.add_member("user1", "user1@test.com")

    def test_remove_member(self):
        org = Organization(name="test")
        org.add_member("user1", "user1@test.com")
        assert org.remove_member("user1")
        assert not org.has_member("user1")

    def test_to_dict(self):
        org = Organization(name="test-org", display_name="Test Org")
        d = org.to_dict()
        assert d["name"] == "test-org"
        assert d["display_name"] == "Test Org"
        assert d["status"] == "pending"


class TestOrganizationStore:
    def test_create_and_get(self):
        store = OrganizationStore()
        org = Organization(name="test")
        store.create(org)
        assert store.get(org.id) is org

    def test_get_by_name(self):
        store = OrganizationStore()
        org = Organization(name="unique-name")
        store.create(org)
        assert store.get_by_name("unique-name") is org

    def test_list_filtered(self):
        store = OrganizationStore()
        org1 = Organization(name="active")
        org1.activate()
        org2 = Organization(name="suspended")
        store.create(org1)
        store.create(org2)
        active = store.list(status=OrganizationStatus.ACTIVE)
        assert len(active) == 1
        assert active[0].name == "active"

    def test_delete(self):
        store = OrganizationStore()
        org = Organization(name="test")
        store.create(org)
        assert store.delete(org.id)
        assert store.get(org.id) is None


# ===========================================================================
# Workspace Tests
# ===========================================================================

class TestWorkspace:
    def test_create(self):
        ws = Workspace(name="prod", organization_id="org_1")
        assert ws.name == "prod"
        assert ws.status == WorkspaceStatus.ACTIVE

    def test_freeze(self):
        ws = Workspace(name="test", organization_id="org_1")
        ws.freeze()
        assert ws.status == WorkspaceStatus.FROZEN

    def test_archive(self):
        ws = Workspace(name="test", organization_id="org_1")
        ws.archive()
        assert ws.status == WorkspaceStatus.ARCHIVED


# ===========================================================================
# User Tests
# ===========================================================================

class TestUser:
    def test_create(self):
        user = User(username="alice", email="alice@test.com")
        assert user.status == UserStatus.PENDING

    def test_activate(self):
        user = User(username="alice", email="alice@test.com")
        user.activate()
        assert user.status == UserStatus.ACTIVE

    def test_disable(self):
        user = User(username="alice", email="alice@test.com")
        user.disable()
        assert user.status == UserStatus.DISABLED


class TestAPIToken:
    def test_generate_and_verify(self):
        token = APIToken(name="test-token", owner_id="user1")
        plaintext = token.generate()
        assert token.token_hash
        assert token.verify(plaintext)
        assert not token.verify("wrong-token")

    def test_revoke(self):
        token = APIToken(name="test", owner_id="user1")
        plaintext = token.generate()
        token.revoke()
        assert not token.verify(plaintext)

    def test_expiration(self):
        token = APIToken(name="test", owner_id="user1",
                         expires_at=datetime.utcnow() - timedelta(hours=1))
        plaintext = token.generate()
        assert not token.verify(plaintext)


# ===========================================================================
# Invitation Tests
# ===========================================================================

class TestInvitation:
    def test_create(self):
        inv = Invitation(email="user@test.com", organization_id="org_1")
        assert inv.status == InvitationStatus.PENDING
        assert inv.token

    def test_accept(self):
        inv = Invitation(email="user@test.com", organization_id="org_1")
        inv.accept()
        assert inv.status == InvitationStatus.ACCEPTED

    def test_expiry(self):
        inv = Invitation(email="user@test.com", organization_id="org_1",
                         expires_at=datetime.utcnow() - timedelta(hours=1))
        assert inv.is_expired()


class TestInvitationManager:
    def test_create_and_get(self):
        mgr = InvitationManager()
        inv = Invitation(email="u@t.com", organization_id="org_1")
        mgr.create(inv)
        assert mgr.get(inv.id) is inv

    def test_get_by_token(self):
        mgr = InvitationManager()
        inv = Invitation(email="u@t.com", organization_id="org_1", token="abc123")
        mgr.create(inv)
        assert mgr.get_by_token("abc123") is inv


# ===========================================================================
# RBAC Tests
# ===========================================================================

class TestRBAC:
    def test_builtin_roles_exist(self):
        assert "admin" in BUILTIN_ROLES
        assert "developer" in BUILTIN_ROLES
        assert "viewer" in BUILTIN_ROLES

    def test_role_permissions(self):
        admin = BUILTIN_ROLES["admin"]
        assert PERM_ADMIN_USERS in admin.permissions

    def test_assign_role(self):
        rbac = RBACManager()
        binding = rbac.assign_role("user:alice", "admin", "org:acme")
        assert binding.role_name == "admin"

    def test_check_access(self):
        rbac = RBACManager()
        rbac.assign_role("user:alice", "admin", "org:acme")
        assert rbac.check_access("user:alice", PERM_ADMIN_USERS, "org:acme")

    def test_deny_access(self):
        rbac = RBACManager()
        rbac.assign_role("user:alice", "viewer", "global")
        assert not rbac.check_access("user:alice", PERM_ADMIN_USERS)

    def test_custom_role(self):
        rbac = RBACManager()
        custom = Role(name="custom-reader", description="Custom", permissions={PERM_CLUSTER_READ})
        rbac.register_role(custom)
        rbac.assign_role("user:bob", "custom-reader", "global")
        assert rbac.check_access("user:bob", PERM_CLUSTER_READ)
        assert not rbac.check_access("user:bob", PERM_ENGINEERING_READ)

    def test_unassign_role(self):
        rbac = RBACManager()
        rbac.assign_role("user:alice", "admin", "org:acme")
        assert rbac.unassign_role("user:alice", "admin", "org:acme")
        assert not rbac.check_access("user:alice", PERM_ADMIN_USERS, "org:acme")


# ===========================================================================
# Policy Engine Tests
# ===========================================================================

class TestPolicyEngine:
    def test_allow_rule(self):
        engine = PolicyEngine()
        policy = Policy(name="plugin_policy")
        policy.add_rule(PolicyRule(
            resource="plugin:*",
            action=PolicyDecision.ALLOW,
            priority=100,
        ))
        engine.register_policy(policy)
        result = engine.evaluate("plugin_policy", "plugin:test")
        assert result.decision == PolicyDecision.ALLOW

    def test_deny_rule(self):
        engine = PolicyEngine()
        policy = Policy(name="network_policy")
        policy.add_rule(PolicyRule(
            resource="network:*",
            action=PolicyDecision.DENY,
            priority=100,
        ))
        engine.register_policy(policy)
        result = engine.evaluate("network_policy", "network:external")
        assert result.decision == PolicyDecision.DENY

    def test_default_deny(self):
        engine = PolicyEngine()
        policy = Policy(name="default")
        engine.register_policy(policy)
        result = engine.evaluate("default", "anything")
        assert result.decision == PolicyDecision.DENY

    def test_conditional_rule(self):
        engine = PolicyEngine()
        policy = Policy(name="test")
        policy.add_rule(PolicyRule(
            resource="file:*",
            action=PolicyDecision.ALLOW,
            conditions={"env": "dev"},
        ))
        engine.register_policy(policy)
        result = engine.evaluate("test", "file:read", {"env": "dev"})
        assert result.decision == PolicyDecision.ALLOW
        result2 = engine.evaluate("test", "file:read", {"env": "prod"})
        assert result2.decision == PolicyDecision.DENY

    def test_priority_order(self):
        engine = PolicyEngine()
        policy = Policy(name="test")
        policy.add_rule(PolicyRule(resource="*", action=PolicyDecision.DENY, priority=200))
        policy.add_rule(PolicyRule(resource="safe:*", action=PolicyDecision.ALLOW, priority=100))
        engine.register_policy(policy)
        result = engine.evaluate("test", "safe:operation")
        assert result.decision == PolicyDecision.ALLOW

    def test_evaluation_log(self):
        engine = PolicyEngine()
        policy = Policy(name="test")
        policy.add_rule(PolicyRule(resource="*", action=PolicyDecision.DENY))
        engine.register_policy(policy)
        engine.evaluate("test", "resource:1")
        engine.evaluate("test", "resource:2")
        assert len(engine.get_evaluation_log()) == 2

    def test_unknown_policy(self):
        engine = PolicyEngine()
        result = engine.evaluate("nonexistent", "something")
        assert result.decision == PolicyDecision.DENY


# ===========================================================================
# Audit Log Tests
# ===========================================================================

class TestAuditLog:
    def test_record_and_query(self):
        log = AuditLog()
        log.record(AuditEvent.USER_LOGIN, "alice", "auth", org_id="org_1")
        entries = log.query()
        assert len(entries) == 1
        assert entries[0].event == AuditEvent.USER_LOGIN

    def test_tamper_evident_chain(self):
        log = AuditLog()
        log.record(AuditEvent.USER_LOGIN, "alice")
        log.record(AuditEvent.USER_LOGOUT, "alice")
        assert log.verify_chain()

    def test_tamper_detection(self):
        log = AuditLog()
        log.record(AuditEvent.USER_LOGIN, "alice")
        log.record(AuditEvent.USER_LOGOUT, "alice")
        # Tamper with an entry
        log._entries[0].details = {"tampered": True}
        assert not log.verify_chain()

    def test_filter_by_event(self):
        log = AuditLog()
        log.record(AuditEvent.USER_LOGIN, "alice")
        log.record(AuditEvent.POLICY_CREATED, "admin")
        results = log.query(event_type=AuditEvent.USER_LOGIN)
        assert len(results) == 1

    def test_entry_hash(self):
        log = AuditLog()
        entry = log.record(AuditEvent.USER_LOGIN, "alice")
        assert entry.entry_hash == entry.compute_hash()


class TestAuditExporter:
    def test_json_export(self):
        log = AuditLog()
        log.record(AuditEvent.USER_LOGIN, "alice")
        exporter = AuditExporter(log)
        exported = exporter.to_json()
        assert '"USER_LOGIN"' in exported or '"auth:login"' in exported


# ===========================================================================
# Approval Workflow Tests
# ===========================================================================

class TestApprovals:
    def test_create_request(self):
        request = ApprovalRequest(title="Test", request_type="general")
        assert request.status == ApprovalStatus.PENDING

    def test_approve_step(self):
        mgr = ApprovalManager()
        request = ApprovalRequest(title="Test")
        step = ApprovalStep(id="step1", name="Review", approver_id="admin")
        request.steps.append(step)
        mgr.submit_request(request)
        assert mgr.approve_step(request.id, "step1", "admin")
        assert request.all_approved

    def test_reject_step(self):
        mgr = ApprovalManager()
        request = ApprovalRequest(title="Test")
        step = ApprovalStep(id="step1", name="Review", approver_id="admin")
        request.steps.append(step)
        mgr.submit_request(request)
        assert mgr.reject_step(request.id, "step1", "admin")
        assert request.is_rejected

    def test_multi_step_workflow(self):
        workflow = ApprovalWorkflow(
            name="multi-step",
            steps=[
                {"name": "Manager", "approver_id": "manager", "order": 0},
                {"name": "Director", "approver_id": "director", "order": 1},
            ],
        )
        request = workflow.create_request("Deploy", request_type="deployment")
        assert len(request.steps) == 2
        assert request.current_step is not None

    def test_approval_workflow_register(self):
        mgr = ApprovalManager()
        wf = ApprovalWorkflow(name="deploy", steps=[{"name": "Admin", "approver_id": "admin"}])
        mgr.register_workflow(wf)
        assert mgr.get_workflow("deploy") is wf


# ===========================================================================
# Secret Management Tests
# ===========================================================================

class TestSecrets:
    def test_secret_reference(self):
        ref = SecretReference(path="db/password", provider=SecretProviderType.ENV)
        assert ref.needs_refresh()

    def test_secret_manager_no_provider(self):
        mgr = SecretManager()
        ref = SecretReference(path="test", provider=SecretProviderType.ENV)
        assert mgr.get_secret(ref) is None


# ===========================================================================
# Compliance Tests
# ===========================================================================

class TestCompliance:
    def test_register_control(self):
        mgr = ComplianceManager()
        control = ComplianceControl(name="audit-logging", control_type=ComplianceControlType.AUDIT)
        mgr.register_control(control)
        assert mgr.get_control("audit-logging") is control

    def test_retention_policy(self):
        mgr = ComplianceManager()
        policy = RetentionPolicy(data_type="sessions", retention_days=90)
        mgr.set_retention_policy(policy)
        assert mgr.get_retention_policy("sessions") is policy

    def test_generate_report(self):
        mgr = ComplianceManager()
        report = mgr.generate_report("policy_compliance")
        assert report.passed
        assert len(report.findings) >= 0


# ===========================================================================
# Licensing Tests
# ===========================================================================

class TestLicensing:
    def test_register_license(self):
        mgr = LicenseManager()
        lic = License(key="test-key", tier="enterprise")
        mgr.register_license(lic)
        assert mgr.get_license("test-key") is lic

    def test_feature_check(self):
        mgr = LicenseManager()
        lic = License(key="k", organization_id="org_1", tier="enterprise")
        lic.features["sso"] = LicenseFeature(name="sso", enabled=True)
        mgr.register_license(lic)
        assert mgr.check_feature("org_1", "sso")

    def test_missing_feature(self):
        mgr = LicenseManager()
        lic = License(key="k", organization_id="org_1", tier="free")
        mgr.register_license(lic)
        assert not mgr.check_feature("org_1", "nonexistent")


# ===========================================================================
# Backup & Recovery Tests
# ===========================================================================

class TestBackup:
    def test_create_job(self):
        import tempfile
        from pathlib import Path
        job = BackupJob(name="test", source_paths=[Path(tempfile.gettempdir())],
                        destination=Path(tempfile.gettempdir()))
        assert job.name == "test"


class TestRecovery:
    def test_create_plan(self):
        import tempfile
        from pathlib import Path
        mgr = RecoveryManager()
        plan = mgr.create_plan("test", Path("/backup/test.tar.gz"), Path(tempfile.gettempdir()))
        assert plan.name == "test"
        assert len(plan.steps) >= 1


# ===========================================================================
# High Availability Tests
# ===========================================================================

class TestHA:
    def test_cluster_create(self):
        cluster = HACluster(name="prod")
        assert cluster.name == "prod"

    def test_add_node(self):
        cluster = HACluster(name="prod")
        node = HANode(id="node1", name="primary", role="active")
        cluster.add_node(node)
        assert cluster.active_node is node

    def test_health_summary(self):
        cluster = HACluster(name="prod")
        cluster.add_node(HANode(id="n1", name="node1", role="active"))
        cluster.add_node(HANode(id="n2", name="node2", role="passive"))
        summary = cluster.health_summary()
        assert summary["total_nodes"] == 2

    def test_failover(self):
        cluster = HACluster(name="prod")
        cluster.add_node(HANode(id="n1", name="primary", role="active"))
        cluster.add_node(HANode(id="n2", name="secondary", role="passive"))
        # Mark primary unhealthy
        cluster.nodes["n1"].status = NodeStatus.UNHEALTHY
        promoted = cluster.perform_failover()
        assert promoted is not None
        assert promoted.role == "active"


# ===========================================================================
# Observability Tests
# ===========================================================================

class TestObservability:
    def test_record_metric(self):
        hub = ObservabilityHub()
        hub.record("test.metric", 42.0)
        results = hub.query(name="test.metric")
        assert len(results) == 1

    def test_increment(self):
        hub = ObservabilityHub()
        hub.increment("request.count")
        results = hub.query(name="request.count")
        assert results[0].value == 1.0

    def test_timing(self):
        hub = ObservabilityHub()
        hub.timing("api.latency", 150.0)
        results = hub.query(name="api.latency")
        assert results[0].metric_type == MetricType.TIMING
        assert results[0].unit == "ms"


# ===========================================================================
# Governance Tests
# ===========================================================================

class TestGovernance:
    def test_framework_create(self):
        fw = GovernanceFramework()
        assert fw.get_compliance_score() == 1.0  # No requirements = fully compliant

    def test_add_requirement(self):
        fw = GovernanceFramework()
        req = ComplianceRequirement(name="encryption-at-rest", framework="SOC2")
        fw.add_requirement(req)
        assert fw.get_requirement("encryption-at-rest") is req

    def test_compliance_check(self):
        fw = GovernanceFramework()
        req = ComplianceRequirement(name="audit-logging", framework="SOC2")
        fw.add_requirement(req)
        results = fw.run_compliance_check()
        assert results["total"] == 1

    def test_audit_trail(self):
        fw = GovernanceFramework()
        fw.log_action("policy.updated", "admin", {"policy": "test"})
        assert len(fw.get_audit_trail()) == 1


# ===========================================================================
# Team Tests
# ===========================================================================

class TestTeam:
    def test_create(self):
        team = Team(name="eng", organization_id="org_1")
        assert team.name == "eng"

    def test_add_member(self):
        team = Team(name="eng", organization_id="org_1")
        member = team.add_member("user1")
        assert "user1" in team.members
        assert member.role == TeamRole.MEMBER

    def test_remove_member(self):
        team = Team(name="eng", organization_id="org_1")
        team.add_member("user1")
        assert team.remove_member("user1")
        assert "user1" not in team.members


# ===========================================================================
# RBAC Extra Tests
# ===========================================================================

class TestRBACPermissions:
    def test_check_any_access(self):
        rbac = RBACManager()
        rbac.assign_role("viewer", "viewer", "global")
        assert rbac.check_any_access("viewer", [PERM_CLUSTER_READ, PERM_ADMIN_USERS])
        assert not rbac.check_any_access("viewer", [PERM_ADMIN_USERS])

    def test_get_subject_permissions(self):
        rbac = RBACManager()
        rbac.assign_role("alice", "viewer", "global")
        perms = rbac.get_subject_permissions("alice", "global")
        assert len(perms) > 0

    def test_has_role(self):
        rbac = RBACManager()
        rbac.assign_role("alice", "admin", "org:acme")
        assert rbac.has_role("alice", "admin", "org:acme")

    def test_get_role(self):
        rbac = RBACManager()
        role = rbac.get_role("admin")
        assert role is not None
        assert role.name == "admin"
