from __future__ import annotations
import logging, os, subprocess, time
from typing import Any

logger = logging.getLogger(__name__)

class GitIntegration:
    def __init__(self):
        self._git_available = self._check_git()

    def _check_git(self) -> bool:
        try:
            subprocess.run(["git", "--version"], capture_output=True, timeout=10)
            return True
        except Exception:
            return False

    def _run(self, args: list[str], cwd: str) -> dict[str, Any]:
        if not self._git_available:
            return {"success": False, "error": "Git is not available on this system"}
        try:
            result = subprocess.run(["git"] + args, cwd=cwd, capture_output=True, text=True, timeout=60)
            return {"success": result.returncode == 0, "stdout": result.stdout, "stderr": result.stderr, "exit_code": result.returncode}
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Git operation timed out"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def status(self, repo_path: str) -> dict[str, Any]:
        r = self._run(["status", "--porcelain"], repo_path)
        if not r["success"]:
            return {"success": False, "error": r.get("error", r.get("stderr", ""))}
        lines = [l for l in r["stdout"].split("\n") if l.strip()]
        changes = []
        for line in lines[:200]:
            if len(line) > 3:
                status_code = line[:2].strip()
                file_path = line[3:].strip()
                changes.append({"status": status_code, "file": file_path})
        branch_r = self._run(["rev-parse", "--abbrev-ref", "HEAD"], repo_path)
        branch = branch_r["stdout"].strip() if branch_r["success"] else "unknown"
        ahead_r = self._run(["rev-list", "--count", "@{upstream}..HEAD", "--"], repo_path)
        behind_r = self._run(["rev-list", "--count", "HEAD..@{upstream}", "--"], repo_path)
        ahead = int(ahead_r["stdout"].strip()) if ahead_r["success"] and ahead_r["stdout"].strip().isdigit() else 0
        behind = int(behind_r["stdout"].strip()) if behind_r["success"] and behind_r["stdout"].strip().isdigit() else 0
        return {"success": True, "branch": branch, "changes": changes, "ahead": ahead, "behind": behind, "total_changes": len(changes)}

    def branches(self, repo_path: str) -> dict[str, Any]:
        r = self._run(["branch", "-a"], repo_path)
        if not r["success"]:
            return {"success": False, "error": r.get("error", r.get("stderr", ""))}
        branches = []
        current = ""
        for line in r["stdout"].split("\n"):
            line = line.strip()
            if not line:
                continue
            if line.startswith("* "):
                current = line[2:]
                branches.append({"name": current, "current": True, "remote": False})
            else:
                is_remote = line.startswith("remotes/")
                name = line.replace("remotes/", "") if is_remote else line
                branches.append({"name": name, "current": False, "remote": is_remote})
        return {"success": True, "current": current, "branches": branches}

    def log(self, repo_path: str, max_count: int = 50) -> dict[str, Any]:
        r = self._run(["log", f"--max-count={max_count}", "--format=%H|%an|%ae|%at|%s"], repo_path)
        if not r["success"]:
            return {"success": False, "error": r.get("error", r.get("stderr", ""))}
        commits = []
        for line in r["stdout"].split("\n"):
            line = line.strip()
            if not line:
                continue
            parts = line.split("|", 4)
            if len(parts) >= 5:
                commits.append({"hash": parts[0][:12], "full_hash": parts[0], "author": parts[1], "email": parts[2], "timestamp": int(parts[3]), "message": parts[4]})
        return {"success": True, "commits": commits}

    def diff(self, repo_path: str, target: str = "HEAD", staged: bool = False) -> dict[str, Any]:
        args = ["diff"]
        if staged:
            args.append("--cached")
        args.extend(["--unified=3", target])
        r = self._run(args, repo_path)
        if not r["success"]:
            return {"success": False, "error": r.get("error", r.get("stderr", ""))}
        return {"success": True, "diff": r["stdout"]}

    def commit(self, repo_path: str, message: str, files: list[str] = None) -> dict[str, Any]:
        if files:
            for f in files:
                self._run(["add", f], repo_path)
        else:
            self._run(["add", "-A"], repo_path)
        r = self._run(["commit", "-m", message], repo_path)
        return {"success": r["success"], "stdout": r.get("stdout", ""), "stderr": r.get("stderr", "")}

    def checkout(self, repo_path: str, branch: str, create: bool = False) -> dict[str, Any]:
        args = ["checkout"]
        if create:
            args.extend(["-b", branch])
        else:
            args.append(branch)
        r = self._run(args, repo_path)
        return {"success": r["success"], "stdout": r.get("stdout", ""), "stderr": r.get("stderr", "")}

    def push(self, repo_path: str, remote: str = "origin", branch: str = "") -> dict[str, Any]:
        args = ["push", remote]
        if branch:
            args.append(branch)
        r = self._run(args, repo_path)
        return {"success": r["success"], "stdout": r.get("stdout", ""), "stderr": r.get("stderr", "")}

    def pull(self, repo_path: str, remote: str = "origin", branch: str = "") -> dict[str, Any]:
        args = ["pull", remote]
        if branch:
            args.append(branch)
        r = self._run(args, repo_path)
        return {"success": r["success"], "stdout": r.get("stdout", ""), "stderr": r.get("stderr", "")}

    def stash(self, repo_path: str, action: str = "push", message: str = "") -> dict[str, Any]:
        if action == "push":
            args = ["stash", "push", "-m", message or f"Stash at {time.time():.0f}"]
        elif action == "pop":
            args = ["stash", "pop"]
        elif action == "list":
            args = ["stash", "list"]
        else:
            return {"success": False, "error": f"Unknown stash action: {action}"}
        r = self._run(args, repo_path)
        return {"success": r["success"], "stdout": r.get("stdout", ""), "stderr": r.get("stderr", "")}

    def merge(self, repo_path: str, branch: str) -> dict[str, Any]:
        r = self._run(["merge", branch], repo_path)
        return {"success": r["success"], "stdout": r.get("stdout", ""), "stderr": r.get("stderr", "")}

    def rebase(self, repo_path: str, branch: str) -> dict[str, Any]:
        r = self._run(["rebase", branch], repo_path)
        return {"success": r["success"], "stdout": r.get("stdout", ""), "stderr": r.get("stderr", "")}

    def blame(self, repo_path: str, file_path: str) -> dict[str, Any]:
        r = self._run(["blame", "--line-porcelain", file_path], repo_path)
        if not r["success"]:
            return {"success": False, "error": r.get("error", r.get("stderr", ""))}
        lines = []
        current_commit = ""
        current_author = ""
        for line in r["stdout"].split("\n"):
            if not line:
                continue
            if line.startswith("\t"):
                lines.append({"commit": current_commit[:12], "author": current_author, "content": line[1:]})
            elif " " not in line:
                current_commit = line
            elif line.startswith("author "):
                current_author = line[7:]
        return {"success": True, "lines": lines}

    def fetch(self, repo_path: str, remote: str = "origin") -> dict[str, Any]:
        r = self._run(["fetch", remote], repo_path)
        return {"success": r["success"], "stdout": r.get("stdout", ""), "stderr": r.get("stderr", "")}

    def tag(self, repo_path: str, tag_name: str, message: str = "") -> dict[str, Any]:
        args = ["tag"]
        if message:
            args.extend(["-a", tag_name, "-m", message])
        else:
            args.append(tag_name)
        r = self._run(args, repo_path)
        return {"success": r["success"], "stdout": r.get("stdout", ""), "stderr": r.get("stderr", "")}

    def is_repo(self, path: str) -> bool:
        return os.path.isdir(os.path.join(path, ".git"))
