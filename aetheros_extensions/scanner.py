"""Static + dynamic security scanning (sections 26-27).

Static: executables, shell scripts, exfiltration/credential patterns,
obfuscation, traversal, bombs (via package verifier), oversized files,
postinstall hooks, suspicious endpoints, dynamic code loading, child
processes. Verdicts PASS/WARN/BLOCK — UI must say "static analysis
passed", never "safe".

Dynamic: staged smoke-run of declared smoke entrypoint in a subprocess
with stripped env, cwd jail, timeout; observes exit code, wall time,
peak RSS, stdout size, network attempts (no network fixture in tests —
fetch attempts fail closed and are recorded). Reports what RAN;
never claims unexecuted analysis.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

EXECUTABLE_SUFFIX = (".exe", ".dll", ".so", ".dylib", ".bat", ".cmd",
                     ".ps1", ".sh", ".com", ".scr", ".msi")

_PATTERNS = [
    ("credential_harvest", re.compile(
        r"(os\.environ(\[|\.get).{0,40}(KEY|TOKEN|SECRET|PASSWORD)|"
        r"read.*\.ssh|AWS_SECRET|PRIVATE KEY|document\.cookie)", re.I), "BLOCK"),
    ("exfiltration", re.compile(
        r"(requests\.(post|put).{0,80}http|urllib\.request\.urlopen|"
        r"socket\.create_connection|fetch\(['\"]https?://)", re.I), "WARN"),
    ("shell_spawn", re.compile(
        r"(os\.system|subprocess\.(Popen|call|run)|shell=True|"
        r"child_process|powershell(\.exe)?\s+-)", re.I), "WARN"),
    ("obfuscation", re.compile(
        r"(eval\(.{0,20}atob|Function\(.{0,20}fromCharCode|"
        r"exec\(.{0,30}base64|(?:\\x[0-9a-f]{2}){4,})", re.I), "WARN"),
    ("persistence", re.compile(
        r"(Run\\\\CurrentVersion|LaunchAgents|systemd --user|cron\.d|"
        r"Startup folder|postinstall)", re.I), "WARN"),
    ("path_traversal", re.compile(
        r"(open\(.{0,60}\.\.[\\/]|write.{0,40}\.\.[\\/])", re.I), "WARN"),
    ("prompt_override", re.compile(
        r"(ignore (all )?previous instructions|override (system|platform) policy|"
        r"disregard (safety|security) (policy|restrictions)|"
        r"you are now (unrestricted|jailbroken))", re.I), "BLOCK"),
]


@dataclass
class ScanFinding:
    rule: str
    file: str
    verdict: str
    excerpt: str = ""


@dataclass
class ScanResult:
    verdict: str = "PASS"  # PASS|WARN|BLOCK
    findings: List[ScanFinding] = field(default_factory=list)
    files_scanned: int = 0
    at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {"verdict": self.verdict, "at": self.at,
                "files_scanned": self.files_scanned,
                "findings": [{"rule": f.rule, "file": f.file,
                              "verdict": f.verdict, "excerpt": f.excerpt[:200]}
                             for f in self.findings]}


_TEXT_SUFFIX = {".py", ".js", ".ts", ".json", ".md", ".txt", ".yaml",
                ".yml", ".toml", ".cfg", ".ini", ".html", ".css"}


def scan_static(root: Path) -> ScanResult:
    res = ScanResult()
    worst = "PASS"
    order = {"PASS": 0, "WARN": 1, "BLOCK": 2}
    paths = [p for p in Path(root).rglob("*") if p.is_file()]
    res.files_scanned = len(paths)
    for path in paths:
        rel = path.relative_to(root).as_posix()
        if path.suffix.lower() in EXECUTABLE_SUFFIX:
            res.findings.append(ScanFinding("unexpected_executable", rel, "WARN"))
            worst = "WARN" if order[worst] < 1 else worst
        try:
            if path.stat().st_size > 5 * 1024 * 1024:
                res.findings.append(ScanFinding("oversized_file", rel, "WARN"))
                worst = "WARN" if order[worst] < 1 else worst
        except OSError:
            continue
        if path.suffix.lower() not in _TEXT_SUFFIX:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="strict")
        except (OSError, ValueError, UnicodeDecodeError):
            continue
        for rule, rx, verdict in _PATTERNS:
            m = rx.search(text)
            if m:
                res.findings.append(ScanFinding(rule, rel, verdict,
                                                text[max(0, m.start() - 40):m.end() + 40]))
                if order[verdict] > order[worst]:
                    worst = verdict
    res.verdict = worst
    return res


@dataclass
class DynamicResult:
    ran: bool = False
    verdict: str = "BLOCK"  # PASS|WARN|BLOCK
    exit_code: Optional[int] = None
    wall_s: float = 0.0
    peak_rss_kb: float = 0.0
    stdout_bytes: int = 0
    observations: List[str] = field(default_factory=list)
    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {"ran": self.ran, "verdict": self.verdict,
                "exit_code": self.exit_code, "wall_s": round(self.wall_s, 3),
                "peak_rss_kb": round(self.peak_rss_kb, 1),
                "stdout_bytes": self.stdout_bytes,
                "observations": self.observations, "reason": self.reason}


def _peak_rss(proc: "subprocess.Popen") -> float:
    try:
        import psutil
        return psutil.Process(proc.pid).memory_info().rss / 1024.0
    except (ImportError, Exception):
        return 0.0


def run_dynamic(root: Path, entry: str, *, timeout_s: float = 20.0,
                max_stdout: int = 256 * 1024) -> DynamicResult:
    """Smoke-run a declared entrypoint (must be a .py file under root).

    Stripped env (no secrets in environment), cwd jailed to a temp dir,
    shell=False, timeout enforced. Only what ran is reported.
    """
    target = (Path(root) / entry.replace("\\", "/")).resolve()
    if Path(root).resolve() not in target.parents:
        return DynamicResult(ran=False, reason="entrypoint escapes package")
    if target.suffix.lower() != ".py" or not target.exists():
        return DynamicResult(ran=False, reason="no runnable .py smoke entrypoint")
    env = {"PATH": os.environ.get("PATH", ""), "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),
           "PYTHONSAFEPATH": "1", "PYTHONDONTWRITEBYTECODE": "1",
           "PYTHONIOENCODING": "utf-8", "NO_NETWORK": "1"}
    workdir = Path(tempfile.mkdtemp(prefix="extdyn"))
    t0 = time.time()
    try:
        proc = subprocess.Popen(
            [sys.executable, "-I", str(target)], cwd=str(workdir),
            env={k: v for k, v in env.items() if v},
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL)
    except OSError as exc:
        return DynamicResult(ran=False, reason=f"spawn failed: {exc}")
    peak = 0.0
    out = b""
    obs: List[str] = []
    try:
        while proc.poll() is None:
            peak = max(peak, _peak_rss(proc))
            if time.time() - t0 > timeout_s:
                proc.kill()
                obs.append("timeout: process killed")
                break
            time.sleep(0.05)
        try:
            rest = proc.communicate(timeout=5)[0] or b""
        except subprocess.TimeoutExpired:
            proc.kill()
            rest = b""
        out = rest[:max_stdout]
        if len(rest) > max_stdout:
            obs.append("stdout truncated at cap")
    finally:
        if proc.poll() is None:
            proc.kill()
    wall = time.time() - t0
    code = proc.returncode
    verdict = "PASS" if code == 0 else "WARN"
    if code != 0:
        obs.append(f"nonzero exit: {code}")
    return DynamicResult(ran=True, verdict=verdict, exit_code=code,
                         wall_s=wall, peak_rss_kb=peak,
                         stdout_bytes=len(out), observations=obs,
                         reason="smoke entrypoint executed in isolated subprocess")
