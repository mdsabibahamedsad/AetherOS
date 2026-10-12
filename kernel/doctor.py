"""AetherOS Agent Kernel 1.0 — self-diagnostics (``aetheros kernel doctor``, §114)."""

from __future__ import annotations

from typing import Any, Dict, List


def _check(name: str, fn) -> Dict[str, Any]:
    try:
        detail = fn()
        status = "PASS" if detail.get("ok", True) else "WARN"
        return {"check": name, "status": status, "detail": detail}
    except Exception as exc:
        return {"check": name, "status": "FAIL", "detail": {"error": str(exc)[:300]}}


def run_doctor(kernel) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    checks.append(_check("kernel.health", lambda: {"ok": kernel.is_running(), "running": kernel.is_running()}))
    checks.append(_check("event_bus", lambda: {"ok": kernel.event_bus is not None}))
    checks.append(_check("scheduler", lambda: {"ok": kernel.scheduler is not None,
                                               "stats": kernel.scheduler.get_stats()}))
    checks.append(_check("resources", lambda: {"ok": True,
                                               "available_cpu": kernel.get_available_resources().cpu_cores}))
    checks.append(_check("memory", lambda: {"ok": kernel.memory_manager is not None,
                                            "stats": kernel.memory_manager.get_stats()}))
    checks.append(_check("tools", lambda: {"ok": len(kernel.tool_manager.list_tools()) > 0,
                                           "count": len(kernel.tool_manager.list_tools())}))
    checks.append(_check("capabilities", lambda: {"ok": len(kernel.capability_manager.list_capabilities()) > 0,
                                                  "count": len(kernel.capability_manager.list_capabilities())}))
    checks.append(_check("policies", lambda: {"ok": len(kernel.policy_engine.list_rules()) > 0,
                                              "count": len(kernel.policy_engine.list_rules())}))
    try:
        import mcp  # noqa: F401
        checks.append({"check": "mcp", "status": "PASS", "detail": {"sdk": "installed"}})
    except Exception:
        checks.append({"check": "mcp", "status": "NOT_AVAILABLE", "detail": {"sdk": "not installed"}})
    checks.append({"check": "a2a", "status": "NOT_AVAILABLE",
                   "detail": {"note": "remote federation requires explicit pairing; not configured"}})
    checks.append({"check": "devices", "status": "PASS" if kernel.device_manager else "WARN",
                   "detail": {"devices": len(kernel.device_manager.list_devices()) if kernel.device_manager else 0}})
    checks.append({"check": "disk", "status": "PASS", "detail": _disk()})
    failed = sum(1 for c in checks if c["status"] == "FAIL")
    return {"checks": checks, "summary": {"failed": failed, "total": len(checks)}}


def _disk() -> Dict[str, Any]:
    import shutil
    usage = shutil.disk_usage(".")
    return {"ok": usage.free > 512 * 1024 * 1024, "free_bytes": usage.free}
