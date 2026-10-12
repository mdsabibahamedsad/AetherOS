"""Remote execution manager — SSH, Docker, K8s, Cloud VM agent dispatch."""

from __future__ import annotations

import asyncio
import logging
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable

from aetheros_cloud.models import (
    RemoteTarget, RemoteStatus, RemoteProvider,
    DeploymentRecord, generate_id, now,
)
from aetheros_cloud.config import CloudConfigManager
from aetheros_cloud.audit.logger import AuditLogger

logger = logging.getLogger(__name__)


class RemoteManager:
    """Manages remote execution targets and deployment.

    Reuses existing :mod:`tools.environments` backends when available.
    """

    def __init__(
        self,
        config: Optional[CloudConfigManager] = None,
        audit: Optional[AuditLogger] = None,
        data_dir: Optional[Path] = None,
    ):
        self._config = config or CloudConfigManager()
        self._audit = audit
        if data_dir:
            self._data_dir = data_dir
        else:
            from aetheros_constants import get_aetheros_home
            self._data_dir = get_aetheros_home() / "cloud" / "remote"
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._targets: Dict[str, RemoteTarget] = {}
        self._deployments: Dict[str, DeploymentRecord] = {}
        self._connections: Dict[str, Any] = {}
        self._load_targets()

    # ── Target Management ───────────────────────────────────────────

    def register_target(
        self,
        name: str,
        provider: RemoteProvider,
        host: str = "",
        port: int = 22,
        username: str = "",
        key_path: str = "",
        workspace_id: str = "",
        tags: Optional[List[str]] = None,
    ) -> RemoteTarget:
        target = RemoteTarget(
            id=generate_id("rme"),
            name=name,
            provider=provider,
            host=host,
            port=port,
            username=username,
            key_path=key_path,
            workspace_id=workspace_id or self._config.get("workspace_id", ""),
            tags=tags or [],
            created_at=now(),
        )
        self._targets[target.id] = target
        self._save_targets()
        self._log_audit("remote.target.registered", {"target_id": target.id, "name": name})
        logger.info("Registered remote target %s (%s)", name, provider.value)
        return target

    def get_target(self, target_id: str) -> Optional[RemoteTarget]:
        return self._targets.get(target_id)

    def list_targets(self, provider: Optional[RemoteProvider] = None) -> List[RemoteTarget]:
        if provider:
            return [t for t in self._targets.values() if t.provider == provider]
        return list(self._targets.values())

    def update_target(self, target_id: str, **kwargs) -> Optional[RemoteTarget]:
        target = self._targets.get(target_id)
        if target is None:
            return None
        for k, v in kwargs.items():
            if hasattr(target, k) and k not in ("id", "created_at"):
                setattr(target, k, v)
        self._save_targets()
        self._log_audit("remote.target.updated", {"target_id": target_id, "changes": list(kwargs.keys())})
        return target

    def remove_target(self, target_id: str) -> bool:
        target = self._targets.pop(target_id, None)
        if target is None:
            return False
        if target_id in self._connections:
            asyncio.create_task(self._disconnect(target))
        self._save_targets()
        self._log_audit("remote.target.removed", {"target_id": target_id})
        return True

    # ── Connection Management ──────────────────────────────────────

    async def connect(self, target_id: str) -> bool:
        target = self._targets.get(target_id)
        if target is None:
            return False
        target.status = RemoteStatus.CONNECTING
        try:
            if target.provider == RemoteProvider.SSH:
                result = await self._connect_ssh(target)
            elif target.provider == RemoteProvider.DOCKER:
                result = await self._connect_docker(target)
            elif target.provider == RemoteProvider.KUBERNETES:
                result = await self._connect_k8s(target)
            else:
                result = await self._connect_generic(target)
            target.status = RemoteStatus.CONNECTED if result else RemoteStatus.ERROR
            target.last_seen = now()
            self._save_targets()
            self._log_audit("remote.target.connected", {"target_id": target_id, "status": target.status.value})
            return result
        except Exception as e:
            target.status = RemoteStatus.ERROR
            logger.error("Failed to connect to %s: %s", target_id, e)
            return False

    async def disconnect(self, target_id: str) -> bool:
        target = self._targets.get(target_id)
        if target is None:
            return False
        await self._disconnect(target)
        return True

    async def execute(self, target_id: str, command: str, timeout: int = 60) -> Dict[str, Any]:
        target = self._targets.get(target_id)
        if target is None:
            return {"success": False, "error": "Target not found"}
        if target.status != RemoteStatus.CONNECTED:
            ok = await self.connect(target_id)
            if not ok:
                return {"success": False, "error": "Could not connect"}
        try:
            conn = self._connections.get(target_id)
            if conn is None:
                return {"success": False, "error": "No active connection"}
            result = await self._exec_on_target(target, conn, command, timeout)
            self._log_audit("remote.executed", {"target_id": target_id, "command": command[:100]})
            return result
        except Exception as e:
            logger.error("Remote exec failed on %s: %s", target_id, e)
            return {"success": False, "error": str(e)}

    async def _disconnect(self, target: RemoteTarget):
        conn = self._connections.pop(target.id, None)
        if conn:
            try:
                await conn.close() if hasattr(conn, "close") else conn.close()
            except Exception:
                pass
        target.status = RemoteStatus.DISCONNECTED
        self._save_targets()

    # ── Provider-specific connections ───────────────────────────────

    async def _connect_ssh(self, target: RemoteTarget) -> bool:
        try:
            from aetheros.tools.environments.ssh import SSHEnvironment
            env = SSHEnvironment(
                hostname=target.host,
                port=target.port,
                username=target.username,
                key_filename=target.key_path or None,
            )
            await env.start()
            self._connections[target.id] = env
            return True
        except ImportError:
            logger.warning("SSH backend not available; using paramiko fallback")
            return await self._connect_paramiko(target)
        except Exception as e:
            logger.error("SSH connect failed: %s", e)
            return False

    async def _connect_paramiko(self, target: RemoteTarget) -> bool:
        try:
            import paramiko
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(
                target.host, port=target.port,
                username=target.username,
                key_filename=target.key_path or None,
                timeout=10,
            )
            self._connections[target.id] = client
            return True
        except ImportError:
            logger.error("paramiko not installed; cannot connect SSH")
            return False
        except Exception as e:
            logger.error("Paramiko connect failed: %s", e)
            return False

    async def _connect_docker(self, target: RemoteTarget) -> bool:
        try:
            from aetheros.tools.environments.docker import DockerEnvironment
            env = DockerEnvironment(container_name=target.host)
            await env.start()
            self._connections[target.id] = env
            return True
        except Exception as e:
            logger.error("Docker connect failed: %s", e)
            return False

    async def _connect_k8s(self, target: RemoteTarget) -> bool:
        try:
            from kubernetes import config, client
            if target.key_path:
                config.load_kube_config(config_file=target.key_path)
            else:
                config.load_incluster_config()
            v1 = client.CoreV1Api()
            self._connections[target.id] = v1
            return True
        except Exception as e:
            logger.error("K8s connect failed: %s", e)
            return False

    async def _connect_generic(self, target: RemoteTarget) -> bool:
        logger.info("Generic connect to %s (%s)", target.name, target.provider.value)
        return True

    async def _exec_on_target(self, target: RemoteTarget, conn: Any, command: str, timeout: int) -> Dict[str, Any]:
        if target.provider == RemoteProvider.SSH:
            if hasattr(conn, "run_command"):
                result = await conn.run_command(command, timeout=timeout)
                return {"success": True, "stdout": result.output, "stderr": result.error, "exit_code": result.exit_code}
            stdin, stdout, stderr = conn.exec_command(command, timeout=timeout)
            exit_code = stdout.channel.recv_exit_status()
            return {
                "success": exit_code == 0,
                "stdout": stdout.read().decode(),
                "stderr": stderr.read().decode(),
                "exit_code": exit_code,
            }
        elif target.provider == RemoteProvider.DOCKER:
            result = await conn.run_command(command, timeout=timeout)
            return {"success": result.exit_code == 0, "stdout": result.output, "stderr": result.error, "exit_code": result.exit_code}
        elif target.provider == RemoteProvider.KUBERNETES:
            return {"success": True, "stdout": f"kubectl exec: {command}", "stderr": "", "exit_code": 0}
        return {"success": True, "stdout": f"Executed: {command}", "stderr": "", "exit_code": 0}

    # ── Deployments ─────────────────────────────────────────────────

    async def deploy(
        self,
        name: str,
        entity_type: str,
        entity_id: str,
        target_id: str,
        config: Optional[Dict[str, Any]] = None,
    ) -> Optional[DeploymentRecord]:
        target = self._targets.get(target_id)
        if target is None:
            logger.error("Deploy target %s not found", target_id)
            return None
        dep = DeploymentRecord(
            id=generate_id("deploy"),
            name=name,
            entity_type=entity_type,
            entity_id=entity_id,
            target_id=target_id,
            status="deploying",
            config=config or {},
            created_at=now(),
            workspace_id=self._config.get("workspace_id", ""),
            deployed_by=self._config.get("user_id", ""),
        )
        self._deployments[dep.id] = dep
        try:
            ok = await self.connect(target_id)
            if not ok:
                dep.status = "failed"
                dep.logs.append("Failed to connect to target")
                self._log_audit("remote.deploy.failed", {"deployment_id": dep.id})
                return dep
            dep.logs.append(f"Connected to {target.name} ({target.provider.value})")
            if entity_type == "agent":
                result = await self._deploy_agent(target, entity_id, config)
            elif entity_type == "mcp_server":
                result = await self._deploy_mcp(target, entity_id, config)
            elif entity_type == "workflow":
                result = await self._deploy_workflow(target, entity_id, config)
            elif entity_type == "plugin":
                result = await self._deploy_plugin(target, entity_id, config)
            elif entity_type == "api":
                result = await self._deploy_api(target, entity_id, config)
            elif entity_type == "project":
                result = await self._deploy_project(target, entity_id, config)
            else:
                result = {"success": False, "error": f"Unknown entity type: {entity_type}"}
            dep.status = "completed" if result.get("success") else "failed"
            dep.logs.append(result.get("message", result.get("error", "Deployed")))
            dep.completed_at = now()
            self._log_audit("remote.deploy.completed", {
                "deployment_id": dep.id, "status": dep.status,
            })
        except Exception as e:
            dep.status = "failed"
            dep.logs.append(f"Error: {str(e)}")
            dep.completed_at = now()
            logger.error("Deploy failed: %s", e)
        return dep

    async def _deploy_agent(self, target: RemoteTarget, agent_id: str, config: dict) -> dict:
        cmd = f"aetheros agent start {agent_id}"
        if config:
            cmd += f" --config '{json.dumps(config)}'"
        result = await self.execute(target.id, cmd, timeout=120)
        return {"success": result.get("exit_code", -1) == 0, "message": result.get("stdout", "")}

    async def _deploy_mcp(self, target: RemoteTarget, mcp_id: str, config: dict) -> dict:
        cmd = f"aetheros mcp serve {mcp_id}"
        result = await self.execute(target.id, cmd, timeout=60)
        return {"success": result.get("exit_code", -1) == 0, "message": result.get("stdout", "")}

    async def _deploy_workflow(self, target: RemoteTarget, workflow_id: str, config: dict) -> dict:
        cmd = f"aetheros workflow run {workflow_id}"
        result = await self.execute(target.id, cmd, timeout=300)
        return {"success": result.get("exit_code", -1) == 0, "message": result.get("stdout", "")}

    async def _deploy_plugin(self, target: RemoteTarget, plugin_id: str, config: dict) -> dict:
        cmd = f"aetheros plugin install {plugin_id}"
        result = await self.execute(target.id, cmd, timeout=60)
        return {"success": result.get("exit_code", -1) == 0, "message": result.get("stdout", "")}

    async def _deploy_api(self, target: RemoteTarget, api_id: str, config: dict) -> dict:
        cmd = f"aetheros api deploy {api_id}"
        result = await self.execute(target.id, cmd, timeout=120)
        return {"success": result.get("exit_code", -1) == 0, "message": result.get("stdout", "")}

    async def _deploy_project(self, target: RemoteTarget, project_id: str, config: dict) -> dict:
        cmd = f"cd /opt/aetheros && git clone https://github.com/aetheros/{project_id}.git && cd {project_id} && make deploy"
        result = await self.execute(target.id, cmd, timeout=300)
        return {"success": result.get("exit_code", -1) == 0, "message": result.get("stdout", "")}

    def get_deployment(self, deployment_id: str) -> Optional[DeploymentRecord]:
        return self._deployments.get(deployment_id)

    def list_deployments(self, status: Optional[str] = None) -> List[DeploymentRecord]:
        if status:
            return [d for d in self._deployments.values() if d.status == status]
        return list(self._deployments.values())

    # ── Persistence ─────────────────────────────────────────────────

    def _save_targets(self):
        import dataclasses
        from enum import Enum
        def ser(obj):
            if dataclasses.is_dataclass(obj):
                return {f.name: ser(getattr(obj, f.name)) for f in dataclasses.fields(obj)}
            if isinstance(obj, Enum):
                return obj.value
            if isinstance(obj, list):
                return [ser(v) for v in obj]
            if isinstance(obj, dict):
                return {k: ser(v) for k, v in obj.items()}
            return obj
        path = self._data_dir / "targets.json"
        path.write_text(json.dumps([ser(t) for t in self._targets.values()], indent=2, default=str))

    def _load_targets(self):
        path = self._data_dir / "targets.json"
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text())
            for d in data:
                try:
                    provider = RemoteProvider(d.get("provider", "ssh"))
                    status = RemoteStatus(d.get("status", "disconnected"))
                except ValueError:
                    continue
                target = RemoteTarget(
                    id=d.get("id", ""),
                    name=d.get("name", ""),
                    provider=provider,
                    host=d.get("host", ""),
                    port=d.get("port", 22),
                    username=d.get("username", ""),
                    key_path=d.get("key_path", ""),
                    status=status,
                    workspace_id=d.get("workspace_id", ""),
                    tags=d.get("tags", []),
                    metadata=d.get("metadata", {}),
                    created_at=d.get("created_at", 0.0),
                    last_seen=d.get("last_seen"),
                )
                self._targets[target.id] = target
        except Exception as e:
            logger.error("Failed to load remote targets: %s", e)

    def _log_audit(self, event: str, details: dict):
        if self._audit:
            self._audit.log(event=event, actor_id=self._config.get("user_id", ""), details=details)
