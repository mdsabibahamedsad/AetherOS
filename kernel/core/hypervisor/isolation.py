"""
AetherOS Agent Hypervisor 1.0 — isolation providers (§7-§11).

Layered abstraction over the strongest *real* isolation primitive on the
current host. Every provider reports SUPPORTED / UNAVAILABLE /
REQUIRES_CONFIGURATION via capability detection — never assumed, never
claimed without evidence.
"""

from __future__ import annotations

import logging
import os
import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from kernel.core.hypervisor.types import IsolationLevel, IsolationStatus

logger = logging.getLogger(__name__)


@dataclass
class IsolationReport:
    """Capability-detection outcome for one provider."""
    provider: str
    level: IsolationLevel
    status: IsolationStatus
    detail: str = ""
    evidence: Dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, object]:
        return {
            "provider": self.provider,
            "level": self.level.value,
            "status": self.status.value,
            "detail": self.detail,
            "evidence": dict(self.evidence),
        }


class IsolationProvider:
    """Base class for isolation backends (§8)."""

    name: str = "base"
    level: IsolationLevel = IsolationLevel.LEVEL_0_PROCESS

    def detect(self) -> IsolationReport:
        raise NotImplementedError

    def provision(self, capsule_id: str, config: Dict[str, object]) -> Dict[str, object]:
        """Create backend state for a capsule. Returns backend handle info."""
        return {"provider": self.name, "capsule_id": capsule_id, "handle": None}

    def teardown(self, capsule_id: str, handle: Dict[str, object] | None) -> None:
        """Release backend state for a capsule."""

    def describe(self) -> Dict[str, object]:
        return {"provider": self.name, "level": self.level.value}


class NativeProcessIsolation(IsolationProvider):
    """LEVEL_0: restricted child-process environment (always available).

    Real mechanisms: scrubbed environment block, capsule-root cwd jailing,
    no handle inheritance, resource-accounted spawning via the process
    policy. This is genuine process isolation — and it is honestly labeled
    LEVEL_0, never more.
    """

    name = "native_process"
    level = IsolationLevel.LEVEL_0_PROCESS

    def detect(self) -> IsolationReport:
        return IsolationReport(
            provider=self.name, level=self.level, status=IsolationStatus.SUPPORTED,
            detail="Restricted process environment available on all platforms.",
            evidence={"python": sys.version.split()[0], "platform": platform.system()},
        )


class SandboxedProcessIsolation(IsolationProvider):
    """LEVEL_1: OS user-space sandbox wrapping process isolation.

    Reuses the existing, tested `aetheros_security.sandbox` backends
    (firejail / restricted execution configs) where the host provides them.
    Status is detected, not assumed.
    """

    name = "sandboxed_process"
    level = IsolationLevel.LEVEL_1_SANDBOXED_PROCESS

    def detect(self) -> IsolationReport:
        evidence: Dict[str, object] = {}
        try:
            from aetheros_security import sandbox as _sb  # noqa: F401
            evidence["sandbox_module"] = True
        except ImportError:
            evidence["sandbox_module"] = False
        system = platform.system()
        if system == "Linux" and shutil.which("firejail"):
            return IsolationReport(
                provider=self.name, level=self.level, status=IsolationStatus.SUPPORTED,
                detail="firejail present on Linux host.", evidence=evidence)
        if system == "Windows":
            # Windows Sandbox is an opt-in Windows feature; report honestly.
            wsb = os.path.exists(os.path.expandvars(
                r"%SystemRoot%\System32\WindowsSandbox.exe"))
            evidence["windows_sandbox_binary"] = wsb
            if wsb:
                return IsolationReport(
                    provider=self.name, level=self.level,
                    status=IsolationStatus.REQUIRES_CONFIGURATION,
                    detail="Windows Sandbox binary present; per-capsule .wsb "
                           "configuration required before use.",
                    evidence=evidence)
        if system == "Darwin":
            evidence["seatbelt"] = shutil.which("sandbox-exec") is not None
        return IsolationReport(
            provider=self.name, level=self.level,
            status=IsolationStatus.REQUIRES_CONFIGURATION if evidence.get("sandbox_module")
            else IsolationStatus.UNAVAILABLE,
            detail="No OS sandbox backend detected; configure firejail / "
                   "Windows Sandbox / container runtime to enable.",
            evidence=evidence)


class WindowsIsolationAdapter(IsolationProvider):
    """LEVEL_1 (Windows): Job Objects, restricted tokens, ACLs (§9).

    Probes real primitives via ctypes where possible. Nothing is assumed:
    each mechanism reports its own status.
    """

    name = "windows_native"
    level = IsolationLevel.LEVEL_1_SANDBOXED_PROCESS

    def detect(self) -> IsolationReport:
        if platform.system() != "Windows":
            return IsolationReport(
                provider=self.name, level=self.level,
                status=IsolationStatus.UNAVAILABLE,
                detail="Windows-only primitives on a non-Windows host.")
        evidence: Dict[str, object] = {}
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            job = kernel32.CreateJobObjectW(None, None)
            evidence["job_objects"] = bool(job)
            if job:
                kernel32.CloseHandle(job)
        except Exception as exc:  # pragma: no cover - host dependent
            evidence["job_objects"] = False
            evidence["job_error"] = str(exc)[:200]
        try:
            import ctypes
            advapi = ctypes.windll.advapi32
            evidence["advapi_present"] = bool(advapi)
        except Exception:  # pragma: no cover - host dependent
            evidence["advapi_present"] = False
        status = (IsolationStatus.SUPPORTED if evidence.get("job_objects")
                  else IsolationStatus.UNAVAILABLE)
        return IsolationReport(
            provider=self.name, level=self.level, status=status,
            detail=("Job Objects available for child-process containment."
                    if status == IsolationStatus.SUPPORTED else
                    "Job Objects unavailable on this host."),
            evidence=evidence)


class LinuxNamespaceAdapter(IsolationProvider):
    """LEVEL_1/2 (Linux): namespaces, cgroups, seccomp, capabilities (§10)."""

    name = "linux_namespaces"
    level = IsolationLevel.LEVEL_1_SANDBOXED_PROCESS

    def detect(self) -> IsolationReport:
        if platform.system() != "Linux":
            return IsolationReport(
                provider=self.name, level=self.level,
                status=IsolationStatus.UNAVAILABLE,
                detail="Linux-only primitives on a non-Linux host.")
        evidence: Dict[str, object] = {
            "unshare": shutil.which("unshare") is not None,
            "cgroup_v2": os.path.exists("/sys/fs/cgroup/cgroup.controllers"),
            "uid": os.geteuid() if hasattr(os, "geteuid") else None,
        }
        status = (IsolationStatus.SUPPORTED if evidence["unshare"]
                  else IsolationStatus.REQUIRES_CONFIGURATION)
        return IsolationReport(
            provider=self.name, level=self.level, status=status,
            detail=("Rootless userns/cgroup containment possible."
                    if status == IsolationStatus.SUPPORTED else
                    "util-linux 'unshare' missing; install it to enable."),
            evidence=evidence)


class ContainerAdapter(IsolationProvider):
    """LEVEL_2: Docker/Podman container isolation (detected, never assumed)."""

    name = "container"
    level = IsolationLevel.LEVEL_2_CONTAINER

    def detect(self) -> IsolationReport:
        evidence: Dict[str, object] = {}
        for rt in ("docker", "podman", "nerdctl"):
            path = shutil.which(rt)
            evidence[rt] = path or False
            if path:
                try:
                    proc = subprocess.run(
                        [path, "info", "--format", "{{json .}}"],
                        capture_output=True, timeout=5)
                    evidence[rt + "_daemon"] = proc.returncode == 0
                except Exception:
                    evidence[rt + "_daemon"] = False
        usable = any(evidence.get(r + "_daemon") for r in ("docker", "podman", "nerdctl"))
        status = (IsolationStatus.SUPPORTED if usable
                  else IsolationStatus.REQUIRES_CONFIGURATION
                  if any(evidence.get(r) for r in ("docker", "podman", "nerdctl"))
                  else IsolationStatus.UNAVAILABLE)
        return IsolationReport(
            provider=self.name, level=self.level, status=status,
            detail=("Container daemon reachable." if usable else
                    "No reachable container daemon; install/start Docker or "
                    "Podman to enable LEVEL_2."),
            evidence=evidence)


class MacOSAdapter(IsolationProvider):
    """LEVEL_1 (macOS): documented/current mechanisms only (§11)."""

    name = "macos_native"
    level = IsolationLevel.LEVEL_1_SANDBOXED_PROCESS

    def detect(self) -> IsolationReport:
        if platform.system() != "Darwin":
            return IsolationReport(
                provider=self.name, level=self.level,
                status=IsolationStatus.UNAVAILABLE,
                detail="macOS-only primitives on a non-macOS host.")
        evidence: Dict[str, object] = {
            "sandbox_exec": shutil.which("sandbox-exec") is not None,
        }
        # sandbox-exec is deprecated; report as requires-configuration, never
        # production-safe by default.
        return IsolationReport(
            provider=self.name, level=self.level,
            status=IsolationStatus.REQUIRES_CONFIGURATION,
            detail="sandbox-exec is deprecated; use container/VM providers for "
                   "production isolation on macOS.",
            evidence=evidence)


class VMAdapter(IsolationProvider):
    """LEVEL_3: VM isolation — reported honestly (§7, §125)."""

    name = "vm"
    level = IsolationLevel.LEVEL_3_VM

    def detect(self) -> IsolationReport:
        evidence = {rt: bool(shutil.which(rt))
                    for rt in ("qemu-system-x86_64", "VBoxManage", "hyper-v", "lima", "colima")}
        return IsolationReport(
            provider=self.name, level=self.level,
            status=IsolationStatus.UNAVAILABLE,
            detail="No managed VM backend is wired to capsules in 1.0; "
                   "LEVEL_3 is NOT claimed.",
            evidence=evidence)


class RemoteNodeAdapter(IsolationProvider):
    """LEVEL_2 (remote): trusted AetherOS node execution (§12)."""

    name = "remote_node"
    level = IsolationLevel.LEVEL_2_CONTAINER

    def detect(self) -> IsolationReport:
        return IsolationReport(
            provider=self.name, level=self.level,
            status=IsolationStatus.REQUIRES_CONFIGURATION,
            detail="Remote capsules require explicit node pairing, mTLS "
                   "identity, and resource reservation (not configured).")


_ALL_PROVIDERS: List[IsolationProvider] = [
    NativeProcessIsolation(),
    SandboxedProcessIsolation(),
    WindowsIsolationAdapter(),
    LinuxNamespaceAdapter(),
    ContainerAdapter(),
    MacOSAdapter(),
    VMAdapter(),
    RemoteNodeAdapter(),
]


def detect_isolation_support() -> List[IsolationReport]:
    """Probe every provider on this host. Real detection, no assumptions."""
    reports = []
    for provider in _ALL_PROVIDERS:
        try:
            reports.append(provider.detect())
        except Exception as exc:
            reports.append(IsolationReport(
                provider=provider.name, level=provider.level,
                status=IsolationStatus.UNAVAILABLE,
                detail=f"detection failed: {exc}"))
    return reports


def strongest_available_level(
        reports: Optional[List[IsolationReport]] = None) -> IsolationLevel:
    """Strongest SUPPORTED level on this host (honest floor)."""
    order = list(IsolationLevel)
    best = IsolationLevel.LEVEL_0_PROCESS
    for rep in reports or detect_isolation_support():
        if rep.status == IsolationStatus.SUPPORTED and order.index(rep.level) > order.index(best):
            best = rep.level
    return best


def select_provider(requested: Optional[str] = None) -> IsolationProvider:
    """Select an isolation provider; falls back to native process isolation."""
    if requested:
        for provider in _ALL_PROVIDERS:
            if provider.name == requested:
                return provider
        raise ValueError(f"Unknown isolation provider: {requested!r}")
    # Prefer strongest SUPPORTED provider, defaulting to native process.
    reports = {r.provider: r for r in detect_isolation_support()}
    for name in ("container", "linux_namespaces", "windows_native",
                 "sandboxed_process", "native_process"):
        provider = next(p for p in _ALL_PROVIDERS if p.name == name)
        if reports.get(name) and reports[name].status == IsolationStatus.SUPPORTED:
            return provider
    return NativeProcessIsolation()
