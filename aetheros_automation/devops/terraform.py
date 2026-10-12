from __future__ import annotations

import json
import logging
from typing import Any

from aetheros_automation.terminal.runner import TerminalRunner

logger = logging.getLogger(__name__)


class TerraformRunner:
    """Terraform lifecycle operations (init, plan, apply, destroy, validate)."""

    @staticmethod
    async def init(path: str, upgrade: bool = False) -> str:
        cmd = "terraform init"
        if upgrade:
            cmd += " -upgrade"
        result = await TerminalRunner.run(cmd, cwd=path)
        if result["exit_code"] != 0:
            raise RuntimeError(f"terraform init failed:\n{result['stderr']}")
        return result["stdout"]

    @staticmethod
    async def plan(
        path: str,
        out: str = "plan.tfplan",
        var_file: str | None = None,
        targets: list[str] | None = None,
    ) -> str:
        cmd = f"terraform plan -out={out}"
        if var_file:
            cmd += f" -var-file={var_file}"
        if targets:
            for t in targets:
                cmd += f" -target={t}"
        result = await TerminalRunner.run(cmd, cwd=path)
        if result["exit_code"] != 0:
            raise RuntimeError(f"terraform plan failed:\n{result['stderr']}")
        return result["stdout"]

    @staticmethod
    async def apply(path: str, plan: str = "plan.tfplan", auto_approve: bool = True) -> str:
        cmd = f"terraform apply {plan}"
        if auto_approve:
            cmd += " -auto-approve"
        result = await TerminalRunner.run(cmd, cwd=path)
        if result["exit_code"] != 0:
            raise RuntimeError(f"terraform apply failed:\n{result['stderr']}")
        return result["stdout"]

    @staticmethod
    async def destroy(path: str, auto_approve: bool = True, targets: list[str] | None = None) -> str:
        cmd = "terraform destroy"
        if auto_approve:
            cmd += " -auto-approve"
        if targets:
            for t in targets:
                cmd += f" -target={t}"
        result = await TerminalRunner.run(cmd, cwd=path)
        if result["exit_code"] != 0:
            raise RuntimeError(f"terraform destroy failed:\n{result['stderr']}")
        return result["stdout"]

    @staticmethod
    async def output(path: str, name: str | None = None, raw: bool = True) -> dict[str, Any]:
        cmd = "terraform output -json"
        if name:
            cmd += f" {name}"
        result = await TerminalRunner.run(cmd, cwd=path)
        if result["exit_code"] != 0:
            raise RuntimeError(f"terraform output failed:\n{result['stderr']}")
        try:
            outputs: dict[str, Any] = json.loads(result["stdout"])
            return outputs
        except json.JSONDecodeError:
            return {"raw": result["stdout"]}

    @staticmethod
    async def validate(path: str) -> bool:
        """Validate terraform configuration; returns True if valid."""
        result = await TerminalRunner.run("terraform validate", cwd=path)
        return result["exit_code"] == 0

    @staticmethod
    async def fmt(path: str, check: bool = False, recursive: bool = True) -> str:
        cmd = "terraform fmt"
        if check:
            cmd += " -check"
        if recursive:
            cmd += " -recursive"
        result = await TerminalRunner.run(cmd, cwd=path)
        return result["stdout"] + result["stderr"]

    @staticmethod
    async def workspace_list(path: str) -> list[str]:
        result = await TerminalRunner.run("terraform workspace list", cwd=path)
        workspaces: list[str] = []
        for line in result["stdout"].splitlines():
            line = line.strip().strip("*").strip()
            if line:
                workspaces.append(line)
        return workspaces

    @staticmethod
    async def workspace_select(path: str, workspace: str) -> str:
        cmd = f"terraform workspace select {workspace}"
        result = await TerminalRunner.run(cmd, cwd=path)
        return result["stdout"] + result["stderr"]

    @staticmethod
    async def workspace_new(path: str, workspace: str) -> str:
        cmd = f"terraform workspace new {workspace}"
        result = await TerminalRunner.run(cmd, cwd=path)
        return result["stdout"] + result["stderr"]
