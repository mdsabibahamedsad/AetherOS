from __future__ import annotations
import asyncio, json, logging, os, re, subprocess, time, uuid
from typing import Any

logger = logging.getLogger(__name__)

class TaskRunner:
    def __init__(self):
        self._running_tasks: dict[str, dict[str, Any]] = {}
        self._task_history: dict[str, list[dict[str, Any]]] = {}

    def detect_tasks(self, project_path: str) -> list[dict[str, Any]]:
        tasks: list[dict[str, Any]] = []
        package_json = os.path.join(project_path, "package.json")
        if os.path.isfile(package_json):
            try:
                with open(package_json, encoding="utf-8") as f:
                    pkg = json.load(f)
                scripts = pkg.get("scripts", {})
                for name, cmd in scripts.items():
                    tasks.append({"name": name, "command": cmd, "type": "npm_script", "manager": "npm"})
            except Exception:
                pass
        pyproject = os.path.join(project_path, "pyproject.toml")
        if os.path.isfile(pyproject):
            tasks.append({"name": "build", "command": "python -m build", "type": "python", "manager": "pip"})
            tasks.append({"name": "test", "command": "python -m pytest", "type": "python", "manager": "pip"})
            tasks.append({"name": "lint", "command": "python -m ruff check .", "type": "python", "manager": "pip"})
            tasks.append({"name": "format", "command": "python -m ruff format .", "type": "python", "manager": "pip"})
        cargo = os.path.join(project_path, "Cargo.toml")
        if os.path.isfile(cargo):
            tasks.append({"name": "build", "command": "cargo build", "type": "rust", "manager": "cargo"})
            tasks.append({"name": "test", "command": "cargo test", "type": "rust", "manager": "cargo"})
            tasks.append({"name": "lint", "command": "cargo clippy", "type": "rust", "manager": "cargo"})
            tasks.append({"name": "format", "command": "cargo fmt", "type": "rust", "manager": "cargo"})
        go_mod = os.path.join(project_path, "go.mod")
        if os.path.isfile(go_mod):
            tasks.append({"name": "build", "command": "go build ./...", "type": "go", "manager": "go"})
            tasks.append({"name": "test", "command": "go test ./...", "type": "go", "manager": "go"})
            tasks.append({"name": "lint", "command": "go vet ./...", "type": "go", "manager": "go"})
        makefile = os.path.join(project_path, "Makefile")
        if os.path.isfile(makefile):
            tasks.append({"name": "build", "command": "make", "type": "make", "manager": "make"})
            tasks.append({"name": "test", "command": "make test", "type": "make", "manager": "make"})
        return tasks

    async def run_task(self, task_id: str, command: str, cwd: str, env: dict[str, str] | None = None) -> dict[str, Any]:
        state = {"id": task_id, "command": command, "cwd": cwd, "status": "running", "output": "", "error": "", "started_at": time.time(), "completed_at": 0.0, "exit_code": None}
        self._running_tasks[task_id] = state
        try:
            proc = await asyncio.create_subprocess_shell(command, cwd=cwd, env=env, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=3600)
            state["output"] = stdout.decode("utf-8", errors="replace")
            state["error"] = stderr.decode("utf-8", errors="replace")
            state["exit_code"] = proc.returncode
            state["status"] = "completed" if proc.returncode == 0 else "failed"
        except asyncio.TimeoutError:
            if proc:
                proc.kill()
            state["status"] = "timeout"
            state["error"] = "Task timed out after 3600s"
        except Exception as e:
            state["status"] = "failed"
            state["error"] = str(e)
        state["completed_at"] = time.time()
        task_id_key = task_id.split("-")[0] if "-" in task_id else task_id
        self._task_history.setdefault(task_id_key, []).append(state)
        self._running_tasks.pop(task_id, None)
        return state

    def stop_task(self, task_id: str):
        self._running_tasks.pop(task_id, None)

    def get_running_tasks(self) -> list[dict[str, Any]]:
        return [t for t in self._running_tasks.values() if t["status"] == "running"]

    def get_task_history(self, task_name: str, limit: int = 10) -> list[dict[str, Any]]:
        return self._task_history.get(task_name, [])[-limit:]
