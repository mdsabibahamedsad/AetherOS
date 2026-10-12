"""
AetherOS Enterprise Foundation
==============================

Enterprise-grade capabilities for production deployments:

- **Organization Management**: orgs, workspaces, teams, projects
- **Identity & Access**: users, roles, groups, service accounts, API tokens
- **RBAC**: configurable permissions across all domains
- **Policy Engine**: declarative, auditable policy enforcement
- **Approval Workflows**: multi-step approval chains
- **Audit Logging**: tamper-evident, exportable audit trails
- **Secret Management**: pluggable external secret manager integration
- **Compliance**: retention policies, data export, audit reports
- **Operations**: deployment profiles, backup/restore, health checks
- **High Availability**: redundant services, automatic failover
- **Licensing**: license management and enforcement
- **Governance**: organizational governance framework

Architecture
------------
enterprise/
    __init__.py         Package version, public API exports
    organization.py     Organization, workspace, team management
    users.py            User, group, service account management
    invitations.py      Invitation and membership management
    rbac.py             Role-based access control
    policy_engine.py    Declarative policy engine
    approvals.py        Multi-step approval workflows
    audit.py            Tamper-evident audit logging
    secrets.py          Pluggable secret manager integration
    compliance.py       Compliance and governance support
    licensing.py        License management and enforcement
    deployment_profiles.py  Deployment configuration profiles
    backup.py           Backup orchestration
    recovery.py         Recovery orchestration
    high_availability.py   High availability support
    observability.py    Enterprise metrics and events
    governance.py       Governance framework

Usage::

    from enterprise import Organization, Workspace, RBACManager
    from enterprise import PolicyEngine, AuditLogger, ApprovalWorkflow

    org = Organization.create("Acme Corp")
    workspace = org.create_workspace("prod")
    rbac = RBACManager(org)
    rbac.assign_role(user_id="alice", role="admin")
"""

from __future__ import annotations

import logging
from typing import Final

logger = logging.getLogger(__name__)

__version__: Final[str] = "1.0.0"

from enterprise.organization import (
    Organization,
    OrganizationStatus,
    OrganizationMember,
    OrganizationRole,
    OrganizationStore,
)
from enterprise.workspace import (
    Workspace,
    WorkspaceStatus,
    WorkspaceSettings,
)
from enterprise.teams import (
    Team,
    TeamMember,
    TeamRole,
)
from enterprise.users import (
    User,
    UserStatus,
    Group,
    ServiceAccount,
    APIToken,
)
from enterprise.invitations import (
    Invitation,
    InvitationStatus,
    InvitationManager,
)
from enterprise.rbac import (
    Role,
    RoleBinding,
    Permission,
    RBACManager,
    BUILTIN_ROLES,
)
from enterprise.policy_engine import (
    Policy,
    PolicyRule,
    PolicyEngine,
    PolicyDecision,
    PolicyEvaluation,
)
from enterprise.audit import (
    AuditEvent,
    AuditLog,
    AuditLogEntry,
    AuditExporter,
)
from enterprise.approvals import (
    ApprovalRequest,
    ApprovalStep,
    ApprovalWorkflow,
    ApprovalManager,
    ApprovalStatus,
)
from enterprise.secrets import (
    SecretReference,
    SecretManager,
    SecretProvider,
    SecretRotationHook,
)
from enterprise.compliance import (
    ComplianceControl,
    RetentionPolicy,
    ComplianceReport,
    ComplianceManager,
)
from enterprise.licensing import (
    License,
    LicenseFeature,
    LicenseManager,
    LicenseError,
)
from enterprise.deployment_profiles import (
    DeploymentProfile,
    ProfileConfig,
    ProfileManager,
)
from enterprise.backup import (
    BackupJob,
    BackupResult,
    BackupManager,
    BackupSchedule,
)
from enterprise.recovery import (
    RecoveryPlan,
    RecoveryStep,
    RecoveryManager,
    RecoveryResult,
)
from enterprise.high_availability import (
    HANode,
    HACluster,
    FailoverStrategy,
    HealthCheck,
)
from enterprise.observability import (
    EnterpriseMetric,
    MetricType,
    ObservabilityHub,
)
from enterprise.governance import (
    GovernancePolicy,
    GovernanceFramework,
    ComplianceRequirement,
)

__all__ = [
    "__version__",
    # Organization
    "Organization", "OrganizationStatus", "OrganizationMember",
    "OrganizationRole", "OrganizationStore",
    # Workspace
    "Workspace", "WorkspaceStatus", "WorkspaceSettings",
    # Teams
    "Team", "TeamMember", "TeamRole",
    # Users
    "User", "UserStatus", "Group", "ServiceAccount", "APIToken",
    # Invitations
    "Invitation", "InvitationStatus", "InvitationManager",
    # RBAC
    "Role", "RoleBinding", "Permission", "RBACManager", "BUILTIN_ROLES",
    # Policy Engine
    "Policy", "PolicyRule", "PolicyEngine", "PolicyDecision", "PolicyEvaluation",
    # Audit
    "AuditEvent", "AuditLog", "AuditLogEntry", "AuditExporter",
    # Approvals
    "ApprovalRequest", "ApprovalStep", "ApprovalWorkflow",
    "ApprovalManager", "ApprovalStatus",
    # Secrets
    "SecretReference", "SecretManager", "SecretProvider", "SecretRotationHook",
    # Compliance
    "ComplianceControl", "RetentionPolicy", "ComplianceReport", "ComplianceManager",
    # Licensing
    "License", "LicenseFeature", "LicenseManager", "LicenseError",
    # Deployment Profiles
    "DeploymentProfile", "ProfileConfig", "ProfileManager",
    # Backup
    "BackupJob", "BackupResult", "BackupManager", "BackupSchedule",
    # Recovery
    "RecoveryPlan", "RecoveryStep", "RecoveryManager", "RecoveryResult",
    # High Availability
    "HANode", "HACluster", "FailoverStrategy", "HealthCheck",
    # Observability
    "EnterpriseMetric", "MetricType", "ObservabilityHub",
    # Governance
    "GovernancePolicy", "GovernanceFramework", "ComplianceRequirement",
]
