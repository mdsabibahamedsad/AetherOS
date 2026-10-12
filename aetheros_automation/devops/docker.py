from __future__ import annotations

import json
import logging
import os
from typing import Any

from aetheros_automation.terminal.runner import TerminalRunner

logger = logging.getLogger(__name__)


class DockerManager:
    """Docker and docker-compose operations."""

    # ------------------------------------------------------------------
    # image management
    # ------------------------------------------------------------------

    @staticmethod
    async def build(path: str, tag: str, dockerfile: str = "Dockerfile") -> str:
        cmd = f"docker build -f {dockerfile} -t {tag} {path}"
        logger.debug("docker build: %s", cmd)
        result = await TerminalRunner.run(cmd)
        if result["exit_code"] != 0:
            raise RuntimeError(f"Build failed:\n{result['stderr']}")
        return result["stdout"]

    @staticmethod
    async def pull(image: str) -> str:
        cmd = f"docker pull {image}"
        logger.debug("docker pull: %s", cmd)
        result = await TerminalRunner.run(cmd)
        if result["exit_code"] != 0:
            raise RuntimeError(f"Pull failed:\n{result['stderr']}")
        return result["stdout"]

    @staticmethod
    async def push(image: str, tag: str | None = None) -> str:
        img = f"{image}:{tag}" if tag else image
        cmd = f"docker push {img}"
        logger.debug("docker push: %s", cmd)
        result = await TerminalRunner.run(cmd)
        if result["exit_code"] != 0:
            raise RuntimeError(f"Push failed:\n{result['stderr']}")
        return result["stdout"]

    # ------------------------------------------------------------------
    # containers
    # ------------------------------------------------------------------

    @staticmethod
    async def run(
        image: str,
        command: str | None = None,
        detach: bool = False,
        ports: dict[int, int] | None = None,
        volumes: dict[str, str] | None = None,
        env: dict[str, str] | None = None,
        name: str | None = None,
        rm: bool = False,
    ) -> str:
        parts = ["docker", "run"]
        if detach:
            parts.append("-d")
        if rm:
            parts.append("--rm")
        if name:
            parts.extend(["--name", name])
        if ports:
            for host_p, container_p in ports.items():
                parts.extend(["-p", f"{host_p}:{container_p}"])
        if volumes:
            for host_v, container_v in volumes.items():
                parts.extend(["-v", f"{host_v}:{container_v}"])
        if env:
            for k, v in env.items():
                parts.extend(["-e", f"{k}={v}"])
        parts.append(image)
        if command:
            parts.append(command)

        cmd = " ".join(str(p) for p in parts)
        logger.debug("docker run: %s", cmd)
        result = await TerminalRunner.run(cmd)
        if result["exit_code"] != 0:
            raise RuntimeError(f"Run failed:\n{result['stderr']}")
        return result["stdout"].strip()

    @staticmethod
    async def stop(container_id: str) -> str:
        cmd = f"docker stop {container_id}"
        result = await TerminalRunner.run(cmd)
        return result["stdout"]

    @staticmethod
    async def logs(container_id: str, tail: int = 100) -> str:
        cmd = f"docker logs --tail {tail} {container_id}"
        result = await TerminalRunner.run(cmd)
        return result["stdout"] + result["stderr"]

    @staticmethod
    async def ps(all: bool = False) -> list[dict[str, Any]]:
        cmd = "docker ps -a --format json" if all else "docker ps --format json"
        result = await TerminalRunner.run(cmd)
        containers: list[dict[str, Any]] = []
        for line in result["stdout"].splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                containers.append(json.loads(line))
            except json.JSONDecodeError:
                containers.append({"raw": line})
        return containers

    # ------------------------------------------------------------------
    # compose
    # ------------------------------------------------------------------

    @staticmethod
    async def compose_up(
        path: str,
        services: list[str] | None = None,
        detach: bool = True,
    ) -> str:
        cmd = f"docker-compose -f {path} up"
        if detach:
            cmd += " -d"
        if services:
            cmd += " " + " ".join(services)
        logger.debug("compose up: %s", cmd)
        result = await TerminalRunner.run(cmd)
        return result["stdout"] + result["stderr"]

    @staticmethod
    async def compose_down(path: str) -> str:
        cmd = f"docker-compose -f {path} down"
        result = await TerminalRunner.run(cmd)
        return result["stdout"] + result["stderr"]

    @staticmethod
    async def compose_logs(path: str, service: str | None = None) -> str:
        cmd = f"docker-compose -f {path} logs"
        if service:
            cmd += f" {service}"
        result = await TerminalRunner.run(cmd)
        return result["stdout"] + result["stderr"]

    @staticmethod
    async def compose_ps(path: str) -> list[dict[str, Any]]:
        cmd = f"docker-compose -f {path} ps --format json"
        result = await TerminalRunner.run(cmd)
        services: list[dict[str, Any]] = []
        for line in result["stdout"].splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                services.append(json.loads(line))
            except json.JSONDecodeError:
                services.append({"raw": line})
        return services
