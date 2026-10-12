"""Legacy security bypass audit (§107, §201). Statically scans for
consequential execution paths that bypass Trust Fabric and classifies
each as protected / partially protected / legacy bypass / unknown.
Run: .venv/Scripts/python scripts/trust_bypass_audit.py
"""
from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PATTERNS = {
    "raw subprocess execution": ["subprocess.run(", "subprocess.Popen(",
                                 "os.system(", "os.execv", "os.spawnl"],
    "raw network access": ["urllib.request.urlopen(", "requests.post(",
                           "requests.get(", "socket.create_connection("],
    "raw filesystem mutation": ["shutil.rmtree(", "os.remove(",
                                "os.removedirs(", "Path.unlink("],
    "secret access": ["keyring.get_password(", "os.environ[\"",
                      "os.environ['"],
    "browser action": ["page.goto(", "browser_navigate("],
    "robot action": ["set_velocity(", ".move_joints("],
    "A2A send": ["federation.send(", "send_remote("],
    "MCP execution": ["mcp.call_tool(", "tools/call"],
    "automation trigger": ["scheduler.add_job(", "cron.schedule("],
    "direct tool invocation": ["handle_function_call("],
}

SKIP_DIRS = {"tests", "website", "docs", "node_modules", ".venv",
             "__pycache__", ".git", "dist", "build", "dist-packaged",
             "release", "win-unpacked"}

# files that ARE the enforcement layer (trusted infrastructure, §108)
TRUSTED = {
    "trust/", "aetheros_control_plane/", "aetheros_security/",
    "tests/", "scripts/trust_bypass_audit.py", "benchmark/",
}


def is_trusted(path: str) -> bool:
    return any(t in path.replace("\\", "/") for t in TRUSTED)


def uses_gate(source: str) -> bool:
    markers = ("TrustFabric", "ActionFirewall", "plane.check",
               "ToolAuthorizationService", "tool_authz", "validate_tool",
               "SafetyController", "check_action", "ApprovalOrchestrator",
               "CapabilityAuthority", "SafetyPolicy", "_gate(")
    return any(m in source for m in markers)


def main() -> int:
    findings = []
    for path in sorted(ROOT.rglob("*.py")):
        parts = set(path.relative_to(ROOT).parts)
        if parts & SKIP_DIRS or "__pycache__" in str(path):
            continue
        rel = str(path.relative_to(ROOT)).replace("\\", "/")
        try:
            source = path.read_text(encoding="utf-8")
        except Exception:
            continue
        for category, markers in PATTERNS.items():
            hits = [m for m in markers if m in source]
            if not hits:
                continue
            if is_trusted(rel):
                status = "protected"
            elif uses_gate(source):
                status = "partially protected"
            else:
                status = "legacy bypass"
            findings.append({"file": rel, "category": category,
                             "markers": hits[:4], "status": status})
    by_status: dict = {}
    for fl in findings:
        by_status[fl["status"]] = by_status.get(fl["status"], 0) + 1
    report = {"summary": by_status, "findings": findings,
              "note": "static heuristic scan; 'legacy bypass' means no "
                      "Trust Fabric reference found in-file, not a proven "
                      "exploitable path. Each needs human review."}
    out = ROOT / "docs" / "security" / "AETHEROS_TRUST_FABRIC_MIGRATION_REPORT.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# Trust Fabric Migration Report (§201)", "",
             f"Files scanned with findings: {len(findings)}", ""]
    for status in ("protected", "partially protected", "legacy bypass"):
        lines.append(f"## {status} ({by_status.get(status, 0)})")
        for fl in findings:
            if fl["status"] == status:
                lines.append(
                    f"- `{fl['file']}` — {fl['category']}: "
                    f"{', '.join(fl['markers'])}")
        lines.append("")
    lines.append("## Trusted infrastructure exceptions (§108)")
    lines += ["- `trust/` + `aetheros_control_plane/` + `aetheros_security/`: "
              "the enforcement layer itself; owned by Trust Fabric, audited "
              "by tests/trust + tests/control_plane.",
              "- EmergencyController/PolicyEngine/IdentityAuthority paths: "
              "privileged by design; every use emits audit events."]
    out.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"summary": by_status,
                      "report": str(out),
                      "total_findings": len(findings)}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
