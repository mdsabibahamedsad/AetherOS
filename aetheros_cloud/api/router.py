"""FastAPI router for Aether Cloud endpoints.

Mount onto an existing FastAPI app (from aetheros_cli.web_server).
"""

from __future__ import annotations

import logging
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

logger = logging.getLogger(__name__)


class CloudAPIRouter:
    """FastAPI router group for cloud endpoints.

    Usage::

        from fastapi import FastAPI
        from aetheros_cloud.api.router import CloudAPIRouter

        app = FastAPI()
        cloud = CloudAPIRouter()
        cloud.mount(app)
    """

    def __init__(
        self,
        workspace_mgr: Optional[WorkspaceManager] = None,
        team_mgr: Optional[TeamManager] = None,
        sync_engine: Optional[SyncEngine] = None,
        remote_mgr: Optional[RemoteManager] = None,
        storage_mgr: Optional[StorageManager] = None,
        audit: Optional[AuditLogger] = None,
        notifications: Optional[NotificationDispatcher] = None,
        knowledge: Optional[KnowledgeManager] = None,
        presence: Optional[PresenceManager] = None,
    ):
        self._ws = workspace_mgr or WorkspaceManager()
        self._team = team_mgr or TeamManager()
        self._sync = sync_engine or SyncEngine()
        self._remote = remote_mgr or RemoteManager()
        self._storage = storage_mgr or StorageManager()
        self._audit = audit or AuditLogger()
        self._notifications = notifications or NotificationDispatcher()
        self._knowledge = knowledge or KnowledgeManager()
        self._presence = presence or PresenceManager()

    def mount(self, app: Any, prefix: str = "/api/cloud"):
        """Register all FastAPI routes on *app* under *prefix*."""
        try:
            from fastapi import APIRouter, Depends, HTTPException, Query
            from fastapi.responses import JSONResponse
            from pydantic import BaseModel
        except ImportError:
            logger.warning("FastAPI not available; cloud API routes not mounted")
            return

        router = APIRouter(prefix=prefix, tags=["cloud"])

        # ── Request/Response models ─────────────────────────────────
        class WorkspaceCreate(BaseModel):
            name: str
            description: str = ""
            type: str = "personal"
            settings: dict = {}

        class WorkspaceUpdate(BaseModel):
            name: Optional[str] = None
            description: Optional[str] = None
            settings: Optional[dict] = None

        class MemberAdd(BaseModel):
            user_id: str
            display_name: str = ""
            role: str = "member"

        class TeamCreate(BaseModel):
            name: str
            description: str = ""
            workspace_id: str = ""

        class RemoteTargetCreate(BaseModel):
            name: str
            provider: str = "ssh"
            host: str = ""
            port: int = 22
            username: str = ""
            key_path: str = ""
            tags: list = []

        class ShareCreate(BaseModel):
            entity_type: str
            entity_id: str
            permission: str = "read"
            expires_in: Optional[int] = None

        class DeployRequest(BaseModel):
            name: str
            entity_type: str
            entity_id: str
            target_id: str
            config: dict = {}

        class SyncPush(BaseModel):
            entity_type: str
            entity_id: str
            data: dict
            action: str = "update"

        # ── Workspace endpoints ────────────────────────────────────
        @router.get("/workspaces")
        async def list_workspaces(type: Optional[str] = Query(None)):
            from aetheros_cloud.models import WorkspaceType
            wt = WorkspaceType(type) if type else None
            ws_list = self._ws.list_workspaces(wt)
            return JSONResponse([self._serialize_workspace(w) for w in ws_list])

        @router.post("/workspaces")
        async def create_workspace(body: WorkspaceCreate):
            from aetheros_cloud.models import WorkspaceType
            try:
                wtype = WorkspaceType(body.type)
            except ValueError:
                wtype = WorkspaceType.PERSONAL
            ws = self._ws.create_workspace(
                name=body.name, description=body.description,
                type=wtype, settings=body.settings,
            )
            return JSONResponse(self._serialize_workspace(ws), status_code=201)

        @router.get("/workspaces/{workspace_id}")
        async def get_workspace(workspace_id: str):
            ws = self._ws.get_workspace(workspace_id)
            if ws is None:
                raise HTTPException(status_code=404, detail="Workspace not found")
            return JSONResponse(self._serialize_workspace(ws))

        @router.patch("/workspaces/{workspace_id}")
        async def update_workspace(workspace_id: str, body: WorkspaceUpdate):
            kwargs = {k: v for k, v in body.dict().items() if v is not None}
            ws = self._ws.update_workspace(workspace_id, **kwargs)
            if ws is None:
                raise HTTPException(status_code=404, detail="Workspace not found")
            return JSONResponse(self._serialize_workspace(ws))

        @router.delete("/workspaces/{workspace_id}")
        async def delete_workspace(workspace_id: str):
            ok = self._ws.delete_workspace(workspace_id)
            if not ok:
                raise HTTPException(status_code=404, detail="Workspace not found")
            return JSONResponse({"status": "deleted"})

        @router.get("/workspaces/{workspace_id}/members")
        async def list_members(workspace_id: str):
            members = self._ws.get_members(workspace_id)
            return JSONResponse([
                {"user_id": m.user_id, "display_name": m.display_name, "role": m.role.value, "joined_at": m.joined_at}
                for m in members
            ])

        @router.post("/workspaces/{workspace_id}/members")
        async def add_member(workspace_id: str, body: MemberAdd):
            from aetheros_cloud.models import WorkspaceRole
            try:
                role = WorkspaceRole(body.role)
            except ValueError:
                role = WorkspaceRole.MEMBER
            member = self._ws.add_member(workspace_id, body.user_id, body.display_name, role)
            if member is None:
                raise HTTPException(status_code=404, detail="Workspace not found")
            return JSONResponse({"user_id": member.user_id, "role": member.role.value, "status": "added"})

        @router.delete("/workspaces/{workspace_id}/members/{user_id}")
        async def remove_member(workspace_id: str, user_id: str):
            ok = self._ws.remove_member(workspace_id, user_id)
            if not ok:
                raise HTTPException(status_code=404, detail="Workspace or member not found")
            return JSONResponse({"status": "removed"})

        # ── Team endpoints ─────────────────────────────────────────
        @router.get("/teams")
        async def list_teams(workspace_id: Optional[str] = Query(None)):
            teams = self._team.list_teams(workspace_id)
            return JSONResponse([self._serialize_team(t) for t in teams])

        @router.post("/teams")
        async def create_team(body: TeamCreate):
            team = self._team.create_team(body.name, body.workspace_id, body.description)
            return JSONResponse(self._serialize_team(team), status_code=201)

        @router.get("/teams/{team_id}")
        async def get_team(team_id: str):
            team = self._team.get_team(team_id)
            if team is None:
                raise HTTPException(status_code=404)
            return JSONResponse(self._serialize_team(team))

        @router.delete("/teams/{team_id}")
        async def delete_team(team_id: str):
            ok = self._team.delete_team(team_id)
            if not ok:
                raise HTTPException(status_code=404)
            return JSONResponse({"status": "deleted"})

        # ── Remote targets ─────────────────────────────────────────
        @router.get("/remote/targets")
        async def list_targets():
            targets = self._remote.list_targets()
            return JSONResponse([self._serialize_target(t) for t in targets])

        @router.post("/remote/targets")
        async def create_target(body: RemoteTargetCreate):
            from aetheros_cloud.models import RemoteProvider
            try:
                provider = RemoteProvider(body.provider)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid provider: {body.provider}")
            target = self._remote.register_target(
                name=body.name, provider=provider, host=body.host,
                port=body.port, username=body.username,
                key_path=body.key_path, tags=body.tags,
            )
            return JSONResponse(self._serialize_target(target), status_code=201)

        @router.post("/remote/targets/{target_id}/connect")
        async def connect_target(target_id: str):
            import asyncio
            ok = await self._remote.connect(target_id)
            if not ok:
                raise HTTPException(status_code=500, detail="Connection failed")
            return JSONResponse({"status": "connected"})

        @router.post("/remote/targets/{target_id}/execute")
        async def execute_on_target(target_id: str, body: dict):
            import asyncio
            result = await self._remote.execute(target_id, body.get("command", ""), timeout=body.get("timeout", 60))
            return JSONResponse(result)

        # ── Deployments ────────────────────────────────────────────
        @router.post("/deploy")
        async def deploy(body: DeployRequest):
            import asyncio
            dep = await self._remote.deploy(
                name=body.name, entity_type=body.entity_type,
                entity_id=body.entity_id, target_id=body.target_id, config=body.config,
            )
            if dep is None:
                raise HTTPException(status_code=400, detail="Deployment failed")
            return JSONResponse({"deployment_id": dep.id, "status": dep.status})

        @router.get("/deployments")
        async def list_deployments():
            deps = self._remote.list_deployments()
            return JSONResponse([{"id": d.id, "name": d.name, "status": d.status, "entity_type": d.entity_type} for d in deps])

        # ── Sync ───────────────────────────────────────────────────
        @router.get("/sync/pending")
        async def get_pending_sync():
            items = self._sync.get_pending()
            return JSONResponse([{"id": i.id, "entity_type": i.entity_type, "entity_id": i.entity_id, "action": i.action.value} for i in items])

        @router.post("/sync/push")
        async def push_sync(body: SyncPush):
            from aetheros_cloud.models import SyncAction
            try:
                action = SyncAction(body.action)
            except ValueError:
                action = SyncAction.UPDATE
            item = self._sync.track_change(body.entity_type, body.entity_id, body.data, action)
            return JSONResponse({"id": item.id, "status": "tracked"})

        @router.get("/sync/conflicts")
        async def get_sync_conflicts():
            conflicts = self._sync.get_conflicts()
            return JSONResponse([{"id": c.id, "entity_type": c.entity_type, "entity_id": c.entity_id} for c in conflicts])

        # ── Knowledge sharing ──────────────────────────────────────
        @router.post("/share")
        async def share(body: ShareCreate):
            from aetheros_cloud.models import SharePermission
            try:
                perm = SharePermission(body.permission)
            except ValueError:
                perm = SharePermission.READ
            link = self._knowledge.create_share_link(
                entity_type=body.entity_type, entity_id=body.entity_id,
                permission=perm, expires_in=body.expires_in,
            )
            return JSONResponse({"code": link.code, "id": link.id, "permission": perm.value})

        @router.get("/share/resolve/{code}")
        async def resolve_share(code: str):
            link = self._knowledge.resolve_share_link(code)
            if link is None:
                raise HTTPException(status_code=404, detail="Share link not found or expired")
            return JSONResponse({
                "entity_type": link.entity_type, "entity_id": link.entity_id,
                "permission": link.permission.value,
            })

        @router.get("/knowledge/shared")
        async def list_shared(workspace_id: Optional[str] = Query(None)):
            items = self._knowledge.list_shared(workspace_id=workspace_id)
            return JSONResponse([{"id": i.id, "name": i.name, "entity_type": i.entity_type, "tags": i.tags} for i in items])

        # ── Audit ──────────────────────────────────────────────────
        @router.get("/audit")
        async def query_audit(
            event: Optional[str] = Query(None),
            actor_id: Optional[str] = Query(None),
            workspace_id: Optional[str] = Query(None),
            severity: Optional[str] = Query(None),
            limit: int = Query(100),
        ):
            entries = self._audit.query(
                event=event, actor_id=actor_id,
                workspace_id=workspace_id, severity=severity, limit=limit,
            )
            return JSONResponse([{"id": e.id, "event": e.event, "actor_id": e.actor_id, "severity": e.severity, "created_at": e.created_at} for e in entries])

        # ── Presence ───────────────────────────────────────────────
        @router.get("/presence/online")
        async def get_online_users(workspace_id: Optional[str] = Query(None)):
            users = self._presence.get_online_users(workspace_id)
            return JSONResponse({"online_users": users})

        # ── Storage ────────────────────────────────────────────────
        @router.get("/storage/backends")
        async def list_storage_backends():
            backends = self._storage.list_backends()
            return JSONResponse([{"id": b.id, "provider": b.provider.value, "name": b.name, "is_primary": b.is_primary} for b in backends])

        @router.get("/health")
        async def health():
            return JSONResponse({
                "status": "ok",
                "workspaces": len(self._ws.list_workspaces()),
                "teams": len(self._team.list_teams()),
                "targets": len(self._remote.list_targets()),
                "sync_pending": len(self._sync.get_pending()),
                "audit_entries": self._audit.count(),
            })

        app.include_router(router)
        logger.info("Cloud API routes mounted at %s", prefix)

    # ── Serialization helpers ───────────────────────────────────────

    @staticmethod
    def _serialize_workspace(ws) -> dict:
        return {
            "id": ws.id, "name": ws.name, "description": ws.description,
            "type": ws.type.value, "status": ws.status.value,
            "owner_id": ws.owner_id,
            "member_count": len(ws.members),
            "created_at": ws.created_at, "updated_at": ws.updated_at,
            "tags": ws.tags, "settings": ws.settings,
        }

    @staticmethod
    def _serialize_team(team) -> dict:
        return {
            "id": team.id, "name": team.name, "description": team.description,
            "workspace_id": team.workspace_id,
            "member_count": len(team.members),
            "created_at": team.created_at, "updated_at": team.updated_at,
            "tags": team.tags,
        }

    @staticmethod
    def _serialize_target(target) -> dict:
        return {
            "id": target.id, "name": target.name,
            "provider": target.provider.value, "host": target.host,
            "port": target.port, "username": target.username,
            "status": target.status.value, "tags": target.tags,
            "created_at": target.created_at,
        }
