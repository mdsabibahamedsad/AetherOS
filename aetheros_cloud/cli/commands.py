"""CLI commands for Aether Cloud — workspace, team, sync, cloud, remote.

Usage::

    aetheros workspace create|list|show|delete|switch <args>
    aetheros team create|list|add|remove <args>
    aetheros sync status|push|pull|conflicts|resolve <args>
    aetheros cloud status|connect|disconnect|config <args>
    aetheros remote add|list|connect|exec|deploy <args>
    aetheros project create|list|clone|archive <args>
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any, Dict, List, Optional

from aetheros_cloud.workspace.manager import WorkspaceManager
from aetheros_cloud.team.manager import TeamManager
from aetheros_cloud.sync.engine import SyncEngine
from aetheros_cloud.remote.manager import RemoteManager
from aetheros_cloud.storage.base import StorageManager
from aetheros_cloud.audit.logger import AuditLogger
from aetheros_cloud.notifications.dispatcher import NotificationDispatcher
from aetheros_cloud.knowledge.share import KnowledgeManager
from aetheros_cloud.collaboration.presence import PresenceManager
from aetheros_cloud.config import CloudConfigManager
from aetheros_cloud.models import (
    WorkspaceType, RemoteProvider, SharePermission, CloudMode,
)

logger = logging.getLogger(__name__)


class CloudCLI:
    """Aggregates all cloud CLI commands.

    Designed to be called from the existing aetheros CLI dispatcher.
    """

    def __init__(self):
        self._config = CloudConfigManager()
        self._audit = AuditLogger()
        self._ws_mgr = WorkspaceManager(audit=self._audit)
        self._team_mgr = TeamManager(audit=self._audit)
        self._sync = SyncEngine()
        self._remote = RemoteManager(audit=self._audit)
        self._storage = StorageManager()
        self._notifications = NotificationDispatcher()
        self._knowledge = KnowledgeManager()
        self._presence = PresenceManager()

    # ── Top-level dispatch ──────────────────────────────────────────

    def dispatch(self, args: List[str]) -> str:
        if not args:
            return self._help()
        cmd = args[0]
        sub = args[1:] if len(args) > 1 else []
        handlers = {
            "workspace": self._workspace_cmd,
            "team": self._team_cmd,
            "sync": self._sync_cmd,
            "cloud": self._cloud_cmd,
            "remote": self._remote_cmd,
            "project": self._project_cmd,
            "share": self._share_cmd,
            "audit": self._audit_cmd,
        }
        handler = handlers.get(cmd)
        if handler is None:
            return f"Unknown cloud command: {cmd}\n{self._help()}"
        return handler(sub)

    @staticmethod
    def _help() -> str:
        return (
            "Aether Cloud Commands:\n"
            "  workspace create|list|show|delete|switch <args>  — Manage workspaces\n"
            "  team create|list|add|remove <args>               — Manage teams\n"
            "  sync status|push|pull|conflicts|resolve <args>    — Sync across devices\n"
            "  cloud status|connect|disconnect|config <args>     — Cloud connection\n"
            "  remote add|list|connect|exec|deploy <args>        — Remote execution\n"
            "  project create|list|clone|archive <args>          — Manage projects\n"
            "  share create|list|revoke|resolve <args>           — Share knowledge\n"
            "  audit query|export|status <args>                  — Audit logs\n"
        )

    # ── Workspace commands ─────────────────────────────────────────

    def _workspace_cmd(self, args: List[str]) -> str:
        if not args:
            return "Usage: aetheros workspace <create|list|show|delete|switch> [args...]"
        sub = args[0]
        rest = args[1:]

        if sub == "create":
            name = rest[0] if rest else "New Workspace"
            ws = self._ws_mgr.create_workspace(name=name)
            return f"Workspace created:\n  ID:   {ws.id}\n  Name: {ws.name}\n  Type: {ws.type.value}"

        elif sub == "list":
            workspaces = self._ws_mgr.list_workspaces()
            if not workspaces:
                return "No workspaces found."
            lines = [f"Workspaces ({len(workspaces)}):"]
            for w in workspaces:
                active = " [active]" if w.id == self._ws_mgr._active_workspace_id else ""
                lines.append(f"  [{w.id[:8]}] {w.name} ({w.type.value}){active}")
            return "\n".join(lines)

        elif sub == "show":
            ws_id = rest[0] if rest else (self._ws_mgr._active_workspace_id or "")
            ws = self._ws_mgr.get_workspace(ws_id)
            if ws is None:
                return f"Workspace not found: {ws_id}"
            lines = [
                f"Workspace: {ws.name}",
                f"  ID:     {ws.id}",
                f"  Type:   {ws.type.value}",
                f"  Status: {ws.status.value}",
                f"  Owner:  {ws.owner_id}",
                f"  Members: {len(ws.members)}",
                f"  Created: {ws.created_at}",
            ]
            if ws.members:
                lines.append("  Members:")
                for m in ws.members:
                    lines.append(f"    [{m.role.value}] {m.display_name} ({m.user_id})")
            return "\n".join(lines)

        elif sub == "delete":
            ws_id = rest[0] if rest else ""
            if self._ws_mgr.delete_workspace(ws_id):
                return f"Workspace {ws_id} deleted."
            return f"Workspace not found: {ws_id}"

        elif sub == "switch":
            ws_id = rest[0] if rest else ""
            if self._ws_mgr.set_active_workspace(ws_id):
                ws = self._ws_mgr.get_workspace(ws_id)
                return f"Switched to workspace: {ws.name if ws else ws_id}"
            return f"Workspace not found: {ws_id}"

        return f"Unknown workspace subcommand: {sub}"

    # ── Team commands ───────────────────────────────────────────────

    def _team_cmd(self, args: List[str]) -> str:
        if not args:
            return "Usage: aetheros team <create|list|add|remove|delete> [args...]"
        sub = args[0]
        rest = args[1:]

        if sub == "create":
            name = rest[0] if rest else "New Team"
            ws_id = rest[1] if len(rest) > 1 else self._config.get("workspace_id", "")
            team = self._team_mgr.create_team(name=name, workspace_id=ws_id)
            return f"Team created:\n  ID:   {team.id}\n  Name: {team.name}"

        elif sub == "list":
            ws_id = rest[0] if rest else None
            teams = self._team_mgr.list_teams(ws_id)
            if not teams:
                return "No teams found."
            lines = [f"Teams ({len(teams)}):"]
            for t in teams:
                lines.append(f"  [{t.id[:8]}] {t.name} (members: {len(t.members)})")
            return "\n".join(lines)

        elif sub == "add":
            if len(rest) < 2:
                return "Usage: aetheros team add <team_id> <user_id> [role]"
            team_id, user_id = rest[0], rest[1]
            role_str = rest[2] if len(rest) > 2 else "member"
            from aetheros_cloud.models import TeamRole
            try:
                role = TeamRole(role_str)
            except ValueError:
                return f"Invalid role: {role_str}"
            member = self._team_mgr.add_member(team_id, user_id, role=role)
            if member is None:
                return f"Team not found: {team_id}"
            return f"Added {user_id} to team {team_id} as {role.value}"

        elif sub == "remove":
            if len(rest) < 2:
                return "Usage: aetheros team remove <team_id> <user_id>"
            if self._team_mgr.remove_member(rest[0], rest[1]):
                return f"Removed {rest[1]} from team {rest[0]}"
            return f"Team or member not found"

        elif sub == "delete":
            if not rest:
                return "Usage: aetheros team delete <team_id>"
            if self._team_mgr.delete_team(rest[0]):
                return f"Team {rest[0]} deleted."
            return f"Team not found: {rest[0]}"

        return f"Unknown team subcommand: {sub}"

    # ── Sync commands ───────────────────────────────────────────────

    def _sync_cmd(self, args: List[str]) -> str:
        if not args:
            return "Usage: aetheros sync <status|push|pull|conflicts|resolve> [args...]"
        sub = args[0]
        rest = args[1:]

        if sub == "status":
            pending = self._sync.get_pending()
            conflicts = self._sync.get_conflicts()
            return (
                f"Sync Status:\n"
                f"  Pending:  {len(pending)}\n"
                f"  Conflicts: {len(conflicts)}\n"
                f"  Auto-sync: {self._config.get('auto_sync', True)}\n"
                f"  Interval: {self._config.get('sync_interval', 30)}s\n"
                f"  Strategy: {self._config.get('conflict_strategy', 'last_write_wins')}"
            )

        elif sub == "conflicts":
            conflicts = self._sync.get_conflicts()
            if not conflicts:
                return "No sync conflicts."
            lines = [f"Conflicts ({len(conflicts)}):"]
            for c in conflicts:
                lines.append(f"  [{c.id[:8]}] {c.entity_type}:{c.entity_id} (v{c.local_version} vs v{c.remote_version})")
            return "\n".join(lines)

        elif sub == "resolve":
            if len(rest) < 2:
                return "Usage: aetheros sync resolve <conflict_id> <local|remote|merge>"
            cid, strategy = rest[0], rest[1]
            if self._sync.resolve_conflict(cid, strategy):
                return f"Conflict {cid} resolved ({strategy})."
            return f"Conflict not found: {cid}"

        return f"Unknown sync subcommand: {sub}"

    # ── Cloud connection commands ───────────────────────────────────

    def _cloud_cmd(self, args: List[str]) -> str:
        if not args:
            return "Usage: aetheros cloud <status|connect|disconnect|config> [args...]"
        sub = args[0]
        rest = args[1:]

        if sub == "status":
            cfg = self._config.config
            return (
                f"Cloud Status:\n"
                f"  Mode:     {cfg.mode.value}\n"
                f"  Provider: {cfg.provider.value}\n"
                f"  Endpoint: {cfg.endpoint or '(not set)'}\n"
                f"  Workspace: {cfg.workspace_id or '(not set)'}\n"
                f"  User:     {cfg.user_id or '(not set)'}\n"
                f"  Offline:  {cfg.offline_mode}\n"
                f"  Auto-sync: {cfg.auto_sync}\n"
                f"  Encrypted: {cfg.encryption_enabled}"
            )

        elif sub == "config":
            if len(rest) < 2:
                return "Usage: aetheros cloud config <key> <value>"
            key, value = rest[0], rest[1]
            if key == "mode":
                try:
                    value = CloudMode(value)
                except ValueError:
                    return f"Invalid mode. Choose: local, self_hosted, official"
            if key == "endpoint":
                self._config.update(endpoint=value)
            elif key == "sync_interval":
                self._config.update(sync_interval=int(value))
            elif key == "offline_mode":
                self._config.update(offline_mode=value.lower() in ("true", "1", "yes"))
            elif key == "auto_sync":
                self._config.update(auto_sync=value.lower() in ("true", "1", "yes"))
            else:
                self._config.update(**{key: value})
            return f"Cloud config updated: {key} = {value}"

        elif sub == "connect":
            self._config.update(offline_mode=False)
            return "Cloud mode enabled (offline_mode=False)."

        elif sub == "disconnect":
            self._config.update(offline_mode=True)
            return "Cloud mode disabled (offline_mode=True)."

        return f"Unknown cloud subcommand: {sub}"

    # ── Remote execution commands ───────────────────────────────────

    def _remote_cmd(self, args: List[str]) -> str:
        if not args:
            return "Usage: aetheros remote <add|list|connect|exec|deploy> [args...]"
        sub = args[0]
        rest = args[1:]

        if sub == "add":
            if len(rest) < 2:
                return "Usage: aetheros remote add <name> <host> [provider] [port] [user]"
            name, host = rest[0], rest[1]
            provider_str = rest[2] if len(rest) > 2 else "ssh"
            port = int(rest[3]) if len(rest) > 3 else 22
            user = rest[4] if len(rest) > 4 else os.environ.get("USER", "root")
            try:
                provider = RemoteProvider(provider_str)
            except ValueError:
                return f"Invalid provider. Choose: ssh, docker, kubernetes, cloud_vm"
            target = self._remote.register_target(
                name=name, provider=provider, host=host,
                port=port, username=user,
            )
            return f"Remote target added:\n  ID:   {target.id}\n  Name: {target.name}\n  Host: {target.host}"

        elif sub == "list":
            targets = self._remote.list_targets()
            if not targets:
                return "No remote targets configured."
            lines = [f"Remote Targets ({len(targets)}):"]
            for t in targets:
                lines.append(f"  [{t.id[:8]}] {t.name} — {t.provider.value}://{t.host}:{t.port} [{t.status.value}]")
            return "\n".join(lines)

        elif sub == "connect":
            target_id = rest[0] if rest else ""
            result = _run_async(self._remote.connect(target_id))
            return f"Remote {target_id}: {'Connected' if result else 'Failed'}"

        elif sub == "exec":
            if len(rest) < 2:
                return "Usage: aetheros remote exec <target_id> <command>"
            target_id, command = rest[0], " ".join(rest[1:])
            result = _run_async(self._remote.execute(target_id, command))
            if not result.get("success"):
                return f"Error: {result.get('error', 'Unknown')}"
            out = result.get("stdout", "")
            err = result.get("stderr", "")
            parts = []
            if out:
                parts.append(f"stdout:\n{out[:2000]}")
            if err:
                parts.append(f"stderr:\n{err[:500]}")
            return "\n".join(parts) if parts else "(no output)"

        elif sub == "deploy":
            if len(rest) < 3:
                return "Usage: aetheros remote deploy <name> <entity_type> <entity_id> <target_id>"
            name, etype, eid = rest[0], rest[1], rest[2]
            target_id = rest[3] if len(rest) > 3 else ""
            dep = _run_async(self._remote.deploy(name, etype, eid, target_id))
            if dep is None:
                return "Deployment failed."
            return f"Deployment {dep.id}: {dep.status}\n  " + "\n  ".join(dep.logs[-5:])

        return f"Unknown remote subcommand: {sub}"

    # ── Project commands ────────────────────────────────────────────

    def _project_cmd(self, args: List[str]) -> str:
        if not args:
            return "Usage: aetheros project <create|list|show|archive> [args...]"
        sub = args[0]
        rest = args[1:]
        if sub == "list":
            return "Projects: See 'aetheros task list' or use the dashboard."
        return f"Project subcommand '{sub}' not yet implemented via CLI. Use the dashboard."

    # ── Share commands ──────────────────────────────────────────────

    def _share_cmd(self, args: List[str]) -> str:
        if not args:
            return "Usage: aetheros share <create|list|revoke|resolve> [args...]"
        sub = args[0]
        rest = args[1:]

        if sub == "create":
            if len(rest) < 2:
                return "Usage: aetheros share create <entity_type> <entity_id> [permission]"
            etype, eid = rest[0], rest[1]
            perm_str = rest[2] if len(rest) > 2 else "read"
            try:
                perm = SharePermission(perm_str)
            except ValueError:
                return f"Invalid permission: {perm_str}"
            link = self._knowledge.create_share_link(etype, eid, perm)
            return f"Share link created:\n  Code: {link.code}\n  URL: aetheros://share/{link.code}"

        elif sub == "list":
            items = self._knowledge.list_shared()
            if not items:
                return "No shared items."
            lines = [f"Shared Items ({len(items)}):"]
            for i in items:
                lines.append(f"  [{i.id[:8]}] {i.name} ({i.entity_type}) — access: {i.access_count}")
            return "\n".join(lines)

        elif sub == "revoke":
            link_id = rest[0] if rest else ""
            if self._knowledge.revoke_share_link(link_id):
                return f"Share link {link_id} revoked."
            return f"Share link not found: {link_id}"

        elif sub == "resolve":
            code = rest[0] if rest else ""
            link = self._knowledge.resolve_share_link(code)
            if link is None:
                return f"Invalid or expired share code: {code}"
            return f"Shared: {link.entity_type}/{link.entity_id} ({link.permission.value} access)"

        return f"Unknown share subcommand: {sub}"

    # ── Audit commands ──────────────────────────────────────────────

    def _audit_cmd(self, args: List[str]) -> str:
        if not args:
            return "Usage: aetheros audit <query|export|status> [args...]"
        sub = args[0]
        rest = args[1:]

        if sub == "status":
            return (
                f"Audit Log: {self._audit.count()} entries\n"
                f"  Errors:   {self._audit.count(severity='error')}\n"
                f"  Warnings: {self._audit.count(severity='warning')}\n"
                f"  Info:     {self._audit.count(severity='info')}"
            )

        elif sub == "query":
            limit = int(rest[0]) if rest and rest[0].isdigit() else 20
            entries = self._audit.query(limit=limit)
            if not entries:
                return "No audit entries."
            lines = [f"Recent Audit Entries ({len(entries)}):"]
            for e in entries:
                lines.append(f"  [{e.severity.upper():7}] {e.event} — {e.actor_id[:24]} — {e.details.get('workspace_id', '')[:8]} at {e.created_at:.0f}")
            return "\n".join(lines)

        elif sub == "export":
            fmt = rest[0] if rest else "json"
            data = self._audit.export(fmt)
            return data[:5000] + ("..." if len(data) > 5000 else "")

        return f"Unknown audit subcommand: {sub}"


def _run_async(coro, timeout: float = 30):
    """Helper to run coroutines in CLI context."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            future = asyncio.run_coroutine_threadsafe(coro, loop)
            return future.result(timeout=timeout)
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)
