"""Git Runtime — real Git repository operations.

Uses git CLI under the hood for all operations.
No simulated execution — every command is real.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from tool_runtime.interface import (
    ToolInterface,
    ToolMetadata,
    ToolResult,
    ToolRiskLevel,
    ToolCategory,
    ToolStatus,
)

logger = logging.getLogger(__name__)


class GitRuntime(ToolInterface):
    """Git repository operations.

    Supports: clone, status, add, commit, branch, checkout, merge,
    rebase, pull, push, diff, log, tag, stash.
    """

    def __init__(self):
        meta = ToolMetadata(
            id="git",
            name="Git Runtime",
            description="Full Git operations: clone, commit, branch, merge, rebase, pull, push, diff, tag",
            category=ToolCategory.GIT,
            risk_level=ToolRiskLevel.WRITE,
            version="2.0.0",
            tags=["git", "vcs", "version-control"],
            requires_approval=False,
            timeout_seconds=60.0,
        )
        super().__init__(meta)

    def schema(self) -> Dict[str, Any]:
        return {
            "name": "git",
            "description": self.description(),
            "parameters": {
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": [
                            "clone", "status", "add", "commit", "branch",
                            "checkout", "merge", "rebase", "pull", "push",
                            "diff", "log", "tag", "stash", "init",
                            "remote", "fetch", "reset",
                        ],
                    },
                    "repo": {"type": "string", "description": "Repository URL for clone"},
                    "path": {"type": "string", "description": "Repository path (default: cwd)"},
                    "message": {"type": "string", "description": "Commit message"},
                    "branch": {"type": "string", "description": "Branch name"},
                    "target": {"type": "string", "description": "Target branch for merge/rebase"},
                    "files": {
                        "type": "array", "items": {"type": "string"},
                        "description": "Files for add/reset",
                    },
                    "tag_name": {"type": "string"},
                    "remote_name": {"type": "string"},
                    "remote_url": {"type": "string"},
                    "depth": {"type": "integer"},
                    "max_count": {"type": "integer"},
                },
                "required": ["operation"],
            },
        }

    def validate(self, params: Dict[str, Any]) -> List[str]:
        errors = []
        op = params.get("operation")
        if not op:
            errors.append("Missing required parameter: operation")
        if op == "clone" and "repo" not in params:
            errors.append("Operation 'clone' requires 'repo' parameter")
        if op == "commit" and "message" not in params:
            errors.append("Operation 'commit' requires 'message' parameter")
        return errors

    def authorize(self, context: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        return True, None

    def execute(self, params: Dict[str, Any], context: Dict[str, Any]) -> ToolResult:
        if self._cancelled:
            return ToolResult.fail("Execution cancelled")

        operation = params.get("operation")
        op_map = {
            "clone": self._clone,
            "status": self._status,
            "add": self._add,
            "commit": self._commit,
            "branch": self._branch,
            "checkout": self._checkout,
            "merge": self._merge,
            "rebase": self._rebase,
            "pull": self._pull,
            "push": self._push,
            "diff": self._diff,
            "log": self._log,
            "tag": self._tag,
            "stash": self._stash,
            "init": self._init,
            "remote": self._remote,
            "fetch": self._fetch,
            "reset": self._reset,
        }

        handler = op_map.get(operation)
        if not handler:
            return ToolResult.fail(f"Unknown git operation: {operation}")

        try:
            return handler(params)
        except Exception as e:
            logger.error("Git operation '%s' failed: %s", operation, e)
            return ToolResult.fail(f"Git error: {type(e).__name__}: {e}")

    def _git(self, args: List[str], cwd: Optional[str] = None) -> Tuple[int, str, str]:
        result = subprocess.run(
            ["git"] + args,
            capture_output=True, text=True,
            cwd=cwd,
            timeout=120,
        )
        return result.returncode, result.stdout, result.stderr

    def _get_repo_path(self, params: Dict[str, Any]) -> Optional[str]:
        return params.get("path") or os.getcwd()

    def _clone(self, params: Dict[str, Any]) -> ToolResult:
        repo = params["repo"]
        path = params.get("path")
        depth = params.get("depth")
        cmd = ["clone"]
        if depth:
            cmd.extend(["--depth", str(depth)])
        cmd.append(repo)
        if path:
            cmd.append(path)
        rc, out, err = self._git(cmd)
        if rc == 0:
            return ToolResult.ok({"repo": repo, "path": path or ".", "stdout": out.strip()})
        return ToolResult.fail(f"Clone failed: {err.strip()}", output={"stdout": out.strip()})

    def _status(self, params: Dict[str, Any]) -> ToolResult:
        repo_path = self._get_repo_path(params)
        rc, out, err = self._git(["status", "--porcelain"], cwd=repo_path)
        if rc == 0:
            lines = [l for l in out.split("\n") if l.strip()]
            return ToolResult.ok({
                "status": out.strip(),
                "changed_files": len(lines),
                "clean": len(lines) == 0,
            })
        return ToolResult.fail(err.strip())

    def _add(self, params: Dict[str, Any]) -> ToolResult:
        repo_path = self._get_repo_path(params)
        files = params.get("files", [])
        if files:
            rc, out, err = self._git(["add"] + files, cwd=repo_path)
        else:
            rc, out, err = self._git(["add", "."], cwd=repo_path)
        if rc == 0:
            return ToolResult.ok({"files": files or ["."], "added": True})
        return ToolResult.fail(err.strip())

    def _commit(self, params: Dict[str, Any]) -> ToolResult:
        repo_path = self._get_repo_path(params)
        message = params["message"]
        rc, out, err = self._git(["commit", "-m", message], cwd=repo_path)
        if rc == 0:
            sha = ""
            for line in out.split("\n"):
                if line.startswith("["):
                    sha = line.split("]")[0].split(" ")[-1] if " " in line else ""
            return ToolResult.ok({"message": message, "sha": sha, "stdout": out.strip()})
        return ToolResult.fail(err.strip(), output={"stdout": out.strip()})

    def _branch(self, params: Dict[str, Any]) -> ToolResult:
        repo_path = self._get_repo_path(params)
        branch = params.get("branch")
        if branch:
            rc, out, err = self._git(["branch", branch], cwd=repo_path)
            if rc == 0:
                return ToolResult.ok({"branch": branch, "created": True})
            return ToolResult.fail(err.strip())
        rc, out, err = self._git(["branch", "-a"], cwd=repo_path)
        if rc == 0:
            branches = [l.strip().replace("* ", "") for l in out.split("\n") if l.strip()]
            return ToolResult.ok({"branches": branches, "count": len(branches)})
        return ToolResult.fail(err.strip())

    def _checkout(self, params: Dict[str, Any]) -> ToolResult:
        repo_path = self._get_repo_path(params)
        branch = params.get("branch", "")
        rc, out, err = self._git(["checkout", branch], cwd=repo_path)
        if rc == 0:
            return ToolResult.ok({"branch": branch, "checked_out": True})
        return ToolResult.fail(err.strip())

    def _merge(self, params: Dict[str, Any]) -> ToolResult:
        repo_path = self._get_repo_path(params)
        target = params.get("target", "")
        rc, out, err = self._git(["merge", target], cwd=repo_path)
        if rc == 0:
            return ToolResult.ok({"merged": target, "stdout": out.strip()})
        return ToolResult.fail(err.strip(), output={"stdout": out.strip()})

    def _rebase(self, params: Dict[str, Any]) -> ToolResult:
        repo_path = self._get_repo_path(params)
        target = params.get("target", "")
        rc, out, err = self._git(["rebase", target], cwd=repo_path)
        if rc == 0:
            return ToolResult.ok({"rebased_onto": target, "stdout": out.strip()})
        return ToolResult.fail(err.strip())

    def _pull(self, params: Dict[str, Any]) -> ToolResult:
        repo_path = self._get_repo_path(params)
        rc, out, err = self._git(["pull"], cwd=repo_path)
        if rc == 0:
            return ToolResult.ok({"stdout": out.strip()})
        return ToolResult.fail(err.strip())

    def _push(self, params: Dict[str, Any]) -> ToolResult:
        repo_path = self._get_repo_path(params)
        remote = params.get("remote_name")
        branch = params.get("branch")
        cmd = ["push"]
        if remote:
            cmd.append(remote)
        if branch:
            cmd.append(branch)
        rc, out, err = self._git(cmd, cwd=repo_path)
        if rc == 0:
            return ToolResult.ok({"stdout": out.strip()})
        return ToolResult.fail(err.strip())
    
    def _diff(self, params: Dict[str, Any]) -> ToolResult:
        repo_path = self._get_repo_path(params)
        rc, out, err = self._git(["diff"], cwd=repo_path)
        if rc == 0:
            return ToolResult.ok({"diff": out.strip(), "has_changes": bool(out.strip())})
        return ToolResult.fail(err.strip())

    def _log(self, params: Dict[str, Any]) -> ToolResult:
        repo_path = self._get_repo_path(params)
        max_count = params.get("max_count", 10)
        rc, out, err = self._git(
            ["log", f"--max-count={max_count}", "--oneline", "--decorate"],
            cwd=repo_path,
        )
        if rc == 0:
            commits = [l for l in out.split("\n") if l.strip()]
            return ToolResult.ok({"commits": commits, "count": len(commits)})
        return ToolResult.fail(err.strip())

    def _tag(self, params: Dict[str, Any]) -> ToolResult:
        repo_path = self._get_repo_path(params)
        tag_name = params.get("tag_name")
        if tag_name:
            rc, out, err = self._git(["tag", tag_name], cwd=repo_path)
            if rc == 0:
                return ToolResult.ok({"tag": tag_name, "created": True})
            return ToolResult.fail(err.strip())
        rc, out, err = self._git(["tag", "-l"], cwd=repo_path)
        if rc == 0:
            tags = [l for l in out.split("\n") if l.strip()]
            return ToolResult.ok({"tags": tags, "count": len(tags)})
        return ToolResult.fail(err.strip())

    def _stash(self, params: Dict[str, Any]) -> ToolResult:
        repo_path = self._get_repo_path(params)
        rc, out, err = self._git(["stash"], cwd=repo_path)
        if rc == 0:
            return ToolResult.ok({"stashed": True, "stdout": out.strip()})
        return ToolResult.fail(err.strip())

    def _init(self, params: Dict[str, Any]) -> ToolResult:
        path = params.get("path", os.getcwd())
        rc, out, err = self._git(["init"], cwd=path)
        if rc == 0:
            return ToolResult.ok({"path": path, "initialized": True})
        return ToolResult.fail(err.strip())

    def _remote(self, params: Dict[str, Any]) -> ToolResult:
        repo_path = self._get_repo_path(params)
        remote_name = params.get("remote_name")
        remote_url = params.get("remote_url")
        if remote_name and remote_url:
            rc, out, err = self._git(["remote", "add", remote_name, remote_url], cwd=repo_path)
            if rc == 0:
                return ToolResult.ok({"remote": remote_name, "url": remote_url, "added": True})
            return ToolResult.fail(err.strip())
        rc, out, err = self._git(["remote", "-v"], cwd=repo_path)
        if rc == 0:
            remotes = [l for l in out.split("\n") if l.strip()]
            return ToolResult.ok({"remotes": remotes})
        return ToolResult.fail(err.strip())

    def _fetch(self, params: Dict[str, Any]) -> ToolResult:
        repo_path = self._get_repo_path(params)
        remote = params.get("remote_name", "")
        rc, out, err = self._git(["fetch", remote] if remote else ["fetch"], cwd=repo_path)
        if rc == 0:
            return ToolResult.ok({"fetched": True, "stdout": out.strip()})
        return ToolResult.fail(err.strip())

    def _reset(self, params: Dict[str, Any]) -> ToolResult:
        repo_path = self._get_repo_path(params)
        files = params.get("files", [])
        if files:
            rc, out, err = self._git(["reset"] + files, cwd=repo_path)
        else:
            rc, out, err = self._git(["reset"], cwd=repo_path)
        if rc == 0:
            return ToolResult.ok({"reset": True, "files": files})
        return ToolResult.fail(err.strip())
