from __future__ import annotations

import json
import logging
from typing import Any

from aetheros_automation.terminal.runner import TerminalRunner

logger = logging.getLogger(__name__)


class K8sManager:
    """Kubernetes operations via kubectl."""

    @staticmethod
    async def apply(manifest_path: str, namespace: str | None = None) -> str:
        cmd = f"kubectl apply -f {manifest_path}"
        if namespace:
            cmd += f" -n {namespace}"
        result = await TerminalRunner.run(cmd)
        if result["exit_code"] != 0:
            raise RuntimeError(f"kubectl apply failed:\n{result['stderr']}")
        return result["stdout"]

    @staticmethod
    async def delete(manifest_path: str, namespace: str | None = None) -> str:
        cmd = f"kubectl delete -f {manifest_path}"
        if namespace:
            cmd += f" -n {namespace}"
        result = await TerminalRunner.run(cmd)
        if result["exit_code"] != 0:
            raise RuntimeError(f"kubectl delete failed:\n{result['stderr']}")
        return result["stdout"]

    @staticmethod
    async def get_pods(
        namespace: str = "default",
        label_selector: str | None = None,
    ) -> list[dict[str, Any]]:
        cmd = f"kubectl get pods -n {namespace} -o json"
        if label_selector:
            cmd += f" -l {label_selector}"
        result = await TerminalRunner.run(cmd)
        return _parse_kubectl_items(result["stdout"])

    @staticmethod
    async def get_deployments(namespace: str = "default") -> list[dict[str, Any]]:
        cmd = f"kubectl get deployments -n {namespace} -o json"
        result = await TerminalRunner.run(cmd)
        return _parse_kubectl_items(result["stdout"])

    @staticmethod
    async def get_services(namespace: str = "default") -> list[dict[str, Any]]:
        cmd = f"kubectl get services -n {namespace} -o json"
        result = await TerminalRunner.run(cmd)
        return _parse_kubectl_items(result["stdout"])

    @staticmethod
    async def get_nodes() -> list[dict[str, Any]]:
        cmd = "kubectl get nodes -o json"
        result = await TerminalRunner.run(cmd)
        return _parse_kubectl_items(result["stdout"])

    @staticmethod
    async def get_namespaces() -> list[dict[str, Any]]:
        cmd = "kubectl get namespaces -o json"
        result = await TerminalRunner.run(cmd)
        return _parse_kubectl_items(result["stdout"])

    @staticmethod
    async def logs(
        pod_name: str,
        container: str | None = None,
        namespace: str = "default",
        tail: int = 100,
    ) -> str:
        cmd = f"kubectl logs {pod_name} -n {namespace} --tail={tail}"
        if container:
            cmd += f" -c {container}"
        result = await TerminalRunner.run(cmd)
        return result["stdout"] + result["stderr"]

    @staticmethod
    async def rollout_status(deployment: str, namespace: str = "default") -> str:
        cmd = f"kubectl rollout status deployment/{deployment} -n {namespace}"
        result = await TerminalRunner.run(cmd)
        return result["stdout"] + result["stderr"]

    @staticmethod
    async def port_forward(
        resource: str,
        local_port: int,
        container_port: int,
        namespace: str = "default",
    ) -> str:
        cmd = f"kubectl port-forward -n {namespace} {resource} {local_port}:{container_port}"
        logger.debug("port-forward: %s", cmd)
        result = await TerminalRunner.run(cmd, timeout=30.0)
        return result["stdout"] + result["stderr"]

    @staticmethod
    async def exec(
        pod_name: str,
        command: str,
        container: str | None = None,
        namespace: str = "default",
    ) -> dict[str, Any]:
        cmd = f"kubectl exec {pod_name} -n {namespace}"
        if container:
            cmd += f" -c {container}"
        cmd += f" -- {command}"
        result = await TerminalRunner.run(cmd)
        return {
            "stdout": result["stdout"],
            "stderr": result["stderr"],
            "exit_code": result["exit_code"],
        }


def _parse_kubectl_items(json_output: str) -> list[dict[str, Any]]:
    try:
        data = json.loads(json_output)
        return data.get("items", [])
    except json.JSONDecodeError:
        return []
