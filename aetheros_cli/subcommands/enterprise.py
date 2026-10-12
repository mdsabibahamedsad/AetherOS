"""
``aetheros enterprise`` subcommand parser.
"""

from __future__ import annotations

from typing import Callable


def build_enterprise_parser(subparsers, *, cmd_enterprise: Callable) -> None:
    """Attach the enterprise subcommand."""
    parser = subparsers.add_parser(
        "enterprise",
        aliases=["ent"],
        help="Enterprise management — organizations, RBAC, policies, audit",
        description="AetherOS Enterprise Foundation management tools.",
    )
    ent_subparsers = parser.add_subparsers(dest="enterprise_action")

    # enterprise org
    org_parser = ent_subparsers.add_parser("org", help="Manage organizations")
    org_sub = org_parser.add_subparsers(dest="org_action")
    org_create = org_sub.add_parser("create", help="Create an organization")
    org_create.add_argument("name", help="Organization name")
    org_create.add_argument("--display-name", help="Display name")
    org_create.add_argument("--description", help="Description")

    org_list = org_sub.add_parser("list", aliases=["ls"], help="List organizations")
    org_list.add_argument("--status", help="Filter by status")

    org_show = org_sub.add_parser("show", help="Show organization details")
    org_show.add_argument("id", help="Organization ID")
    org_show.add_argument("--json", action="store_true", help="JSON output")

    org_parser.add_argument("--json", action="store_true", help="JSON output")

    # enterprise workspace
    ws_parser = ent_subparsers.add_parser("workspace", aliases=["ws"], help="Manage workspaces")
    ws_sub = ws_parser.add_subparsers(dest="ws_action")
    ws_create = ws_sub.add_parser("create", help="Create a workspace")
    ws_create.add_argument("name", help="Workspace name")
    ws_create.add_argument("--org", required=True, help="Organization ID")
    ws_create.add_argument("--display-name", help="Display name")

    ws_list = ws_sub.add_parser("list", aliases=["ls"], help="List workspaces")
    ws_list.add_argument("--org", help="Filter by organization")

    # enterprise user
    usr_parser = ent_subparsers.add_parser("user", help="Manage users")
    usr_sub = usr_parser.add_subparsers(dest="user_action")
    usr_create = usr_sub.add_parser("create", help="Create a user")
    usr_create.add_argument("username", help="Username")
    usr_create.add_argument("--email", required=True, help="Email")
    usr_create.add_argument("--display-name", help="Display name")
    usr_create.add_argument("--role", help="Initial role")

    usr_list = usr_sub.add_parser("list", aliases=["ls"], help="List users")
    usr_list.add_argument("--org", help="Filter by organization")

    # enterprise rbac
    rbac_parser = ent_subparsers.add_parser("rbac", help="Manage roles and permissions")
    rbac_sub = rbac_parser.add_subparsers(dest="rbac_action")
    rbac_roles = rbac_sub.add_parser("roles", help="List roles")
    rbac_roles.add_argument("--json", action="store_true", help="JSON output")
    rbac_assign = rbac_sub.add_parser("assign", help="Assign a role to a user")
    rbac_assign.add_argument("user", help="User ID")
    rbac_assign.add_argument("role", help="Role name")
    rbac_assign.add_argument("--scope", default="global", help="Scope")
    rbac_assign.add_argument("--subject-type", default="user", choices=["user", "group", "service_account"])
    rbac_check = rbac_sub.add_parser("check", help="Check if user has permission")
    rbac_check.add_argument("user", help="User ID")
    rbac_check.add_argument("permission", help="Permission name")

    # enterprise policy
    policy_parser = ent_subparsers.add_parser("policy", help="Manage policies")
    policy_sub = policy_parser.add_subparsers(dest="policy_action")
    policy_list = policy_sub.add_parser("list", aliases=["ls"], help="List policies")
    policy_show = policy_sub.add_parser("show", help="Show policy details")
    policy_show.add_argument("name", help="Policy name")
    policy_eval = policy_sub.add_parser("evaluate", help="Evaluate a policy")
    policy_eval.add_argument("policy", help="Policy name")
    policy_eval.add_argument("resource", help="Resource to evaluate")

    # enterprise audit
    audit_parser = ent_subparsers.add_parser("audit", help="Manage audit logs")
    audit_sub = audit_parser.add_subparsers(dest="audit_action")
    audit_log = audit_sub.add_parser("log", help="View audit log")
    audit_log.add_argument("--limit", type=int, default=50, help="Max entries")
    audit_log.add_argument("--event", help="Filter by event type")
    audit_log.add_argument("--actor", help="Filter by actor")
    audit_log.add_argument("--json", action="store_true", help="JSON output")
    audit_verify = audit_sub.add_parser("verify", help="Verify audit chain integrity")

    # enterprise backup
    backup_parser = ent_subparsers.add_parser("backup", help="Manage backups")
    backup_sub = backup_parser.add_subparsers(dest="backup_action")
    backup_run = backup_sub.add_parser("run", help="Run a backup")
    backup_run.add_argument("--name", default="default", help="Backup job name")
    backup_run.add_argument("--source", help="Source path")
    backup_run.add_argument("--dest", help="Destination path")
    backup_list = backup_sub.add_parser("list", aliases=["ls"], help="List backups")

    # enterprise recovery
    recovery_parser = ent_subparsers.add_parser("recovery", help="Manage recovery")
    recovery_parser_alias = ent_subparsers.add_parser("restore", help="Manage recovery")
    recovery_sub = recovery_parser.add_subparsers(dest="recovery_action")
    recovery_sub_alias = recovery_parser_alias.add_subparsers(dest="recovery_action")
    recovery_plan = recovery_sub.add_parser("plan", help="Create a recovery plan")
    recovery_plan_alias = recovery_sub_alias.add_parser("plan", help="Create a recovery plan")
    recovery_plan.add_argument("--name", required=True, help="Plan name")
    recovery_plan.add_argument("--backup", required=True, help="Backup path")
    recovery_plan.add_argument("--target", required=True, help="Target path")
    recovery_exec = recovery_sub.add_parser("execute", help="Execute a recovery plan")
    recovery_exec.add_argument("plan_id", help="Plan ID")

    # enterprise ha
    ha_parser = ent_subparsers.add_parser("ha", help="Manage high availability")
    ha_sub = ha_parser.add_subparsers(dest="ha_action")
    ha_status = ha_sub.add_parser("status", help="Show HA cluster status")
    ha_health = ha_sub.add_parser("health", help="Run health checks")

    # enterprise compliance
    comp_parser = ent_subparsers.add_parser("compliance", help="Manage compliance")
    comp_sub = comp_parser.add_subparsers(dest="compliance_action")
    comp_report = comp_sub.add_parser("report", help="Generate compliance report")
    comp_report.add_argument("--type", default="general", help="Report type")
    comp_controls = comp_sub.add_parser("controls", help="List compliance controls")

    # enterprise governance
    gov_parser = ent_subparsers.add_parser("governance", help="Manage governance")
    gov_sub = gov_parser.add_subparsers(dest="governance_action")
    gov_check = gov_sub.add_parser("check", help="Run compliance check")
    gov_score = gov_sub.add_parser("score", help="Show compliance score")
    gov_policies = gov_sub.add_parser("policies", help="List governance policies")

    # enterprise status
    ent_subparsers.add_parser("status", aliases=["st"], help="Show enterprise status")

    parser.set_defaults(func=cmd_enterprise)
