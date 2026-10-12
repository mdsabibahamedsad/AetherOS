"""
AetherOS Agent Hypervisor 1.0 — standard capsule profiles (§6).

Profiles are *defaults*, never authorization bypasses: every capsule still
passes admission (intent → authority → policy → risk → resources →
isolation) and the manifest gate (undeclared == unavailable).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from kernel.core.hypervisor.types import (
    CapsuleMount,
    CapsuleProfileName,
    MountType,
    NetworkMode,
    NetworkPolicy,
)
from kernel.core.types import DataClassification, ResourceBudget


@dataclass(frozen=True)
class CapsuleProfile:
    """Default configuration bundle for a capsule class."""
    name: str
    description: str
    capabilities: List[str] = field(default_factory=list)
    network: NetworkPolicy = field(default_factory=NetworkPolicy)
    mounts: List[CapsuleMount] = field(default_factory=list)
    resources: ResourceBudget = field(default_factory=ResourceBudget)
    model_policy: Dict[str, object] = field(default_factory=dict)
    tool_policy: Dict[str, object] = field(default_factory=dict)
    device_policy: Dict[str, object] = field(default_factory=dict)
    secret_policy: Dict[str, object] = field(default_factory=dict)
    process_policy: Dict[str, object] = field(default_factory=dict)
    memory_scope: str = "task"
    isolation_floor: str = "level_0_process_isolation"
    max_autonomy: str = "autonomy_2"
    privacy_class: DataClassification = DataClassification.INTERNAL
    notes: str = ""


def _std_mounts(extra: List[CapsuleMount] | None = None) -> List[CapsuleMount]:
    base = [
        CapsuleMount(name="workspace", mount_type=MountType.READ_WRITE),
        CapsuleMount(name="scratch", mount_type=MountType.TEMPORARY),
        CapsuleMount(name="artifacts", mount_type=MountType.ARTIFACT_MOUNT),
        CapsuleMount(name="cache", mount_type=MountType.TEMPORARY),
        CapsuleMount(name="tmp", mount_type=MountType.TEMPORARY),
        CapsuleMount(name="memory", mount_type=MountType.READ_WRITE),
        CapsuleMount(name="readonly", mount_type=MountType.READ_ONLY, read_only=True),
    ]
    return base + list(extra or [])


def _budget(**over: object) -> ResourceBudget:
    # Lean by default: scarce session/slot pools are requested only by the
    # profiles that semantically need them (deny-by-default footprint).
    b = ResourceBudget(browser_sessions=0, computer_sessions=0,
                       device_sessions=0, agent_slots=0, automation_slots=0)
    for k, v in over.items():
        setattr(b, k, v)
    return b


def _model(local_only: bool = False, **over: object) -> Dict[str, object]:
    p: Dict[str, object] = {
        "cloud_allowed": not local_only,
        "local_only": local_only,
        "vision_allowed": False,
        "audio_allowed": False,
        "tool_calling_allowed": True,
    }
    p.update(over)
    return p


PROFILES: Dict[str, CapsuleProfile] = {}


def _register(p: CapsuleProfile) -> None:
    PROFILES[p.name] = p


_register(CapsuleProfile(
    name=CapsuleProfileName.MINIMAL.value,
    description="Smallest viable capsule: workspace-only files, no network, local model.",
    capabilities=["fs.read", "fs.write", "memory.read", "memory.write"],
    network=NetworkPolicy(mode=NetworkMode.NO_NETWORK),
    mounts=_std_mounts(),
    resources=_budget(cpu_cores=0.5, ram_mb=512, disk_mb=512, llm_tokens_per_minute=20000,
                      browser_sessions=0, computer_sessions=0, device_sessions=0, agent_slots=0),
    model_policy=_model(local_only=True, maximum_tokens=8000, context_limit=32000),
    tool_policy={"sandboxed": True},
    memory_scope="ephemeral",
    max_autonomy="autonomy_1",
))

_register(CapsuleProfile(
    name=CapsuleProfileName.STANDARD.value,
    description="Default general-purpose capsule.",
    capabilities=["fs.read", "fs.write", "fs.list", "terminal.execute", "memory.read",
                  "memory.write", "research.search", "research.fetch"],
    network=NetworkPolicy(mode=NetworkMode.ALLOWLIST, allowlist=["github.com", "api.openai.com"]),
    mounts=_std_mounts(),
    resources=_budget(),
    model_policy=_model(maximum_tokens=16000, context_limit=128000),
    tool_policy={"sandboxed": True},
))

_register(CapsuleProfile(
    name=CapsuleProfileName.DEVELOPER.value,
    description="Coding agent: workspace RW, git/compiler/tests, terminal; no secrets, no home access.",
    capabilities=["fs.read", "fs.write", "fs.list", "fs.patch", "terminal.execute",
                  "process.execute", "memory.read", "memory.write"],
    network=NetworkPolicy(mode=NetworkMode.ALLOWLIST, allowlist=["github.com"]),
    mounts=_std_mounts(),
    resources=_budget(cpu_cores=2.0, ram_mb=4096, disk_mb=10240),
    model_policy=_model(maximum_tokens=32000, context_limit=200000),
    tool_policy={"sandboxed": True},
    process_policy={"max_processes": 16, "allow_shell": True, "allow_privilege_escalation": False,
                    "allow_debugger_attach": False, "allow_host_process_access": False},
    secret_policy={"expose_plaintext": False, "broker_only": True},
    notes="Personal directories, unrelated repos, system settings and credentials are never mounted.",
))

_register(CapsuleProfile(
    name=CapsuleProfileName.RESEARCH.value,
    description="Research capsule: browser+web+docs, untrusted-source handling, evidence store.",
    capabilities=["research.search", "research.fetch", "browser.navigate", "browser.extract",
                  "memory.read", "memory.write", "fs.write"],
    network=NetworkPolicy(mode=NetworkMode.ALLOWLIST,
                          allowlist=["github.com", "arxiv.org", "api.openai.com"]),
    mounts=_std_mounts([CapsuleMount(name="evidence", mount_type=MountType.READ_WRITE)]),
    resources=_budget(),
    model_policy=_model(maximum_tokens=24000, context_limit=200000),
    notes="Downloaded content enters as UNTRUSTED DATA before research context.",
))

_register(CapsuleProfile(
    name=CapsuleProfileName.BROWSER.value,
    description="Browser automation with per-capsule isolated session state.",
    capabilities=["browser.navigate", "browser.click", "browser.type", "browser.extract",
                  "browser.screenshot", "memory.read", "memory.write"],
    network=NetworkPolicy(mode=NetworkMode.ALLOWLIST, allowlist=["github.com"]),
    mounts=_std_mounts([CapsuleMount(name="browser_profile", mount_type=MountType.TEMPORARY)]),
    resources=_budget(browser_sessions=1, agent_slots=0),
    tool_policy={"sandboxed": True, "browser_isolated_session": True},
))

_register(CapsuleProfile(
    name=CapsuleProfileName.COMPUTER_USE.value,
    description="Computer-use capsule: OBSERVE/ACT separated, minimal UI surface.",
    capabilities=["computer.observe", "computer.screenshot", "memory.read", "memory.write"],
    network=NetworkPolicy(mode=NetworkMode.NO_NETWORK),
    mounts=_std_mounts(),
    resources=_budget(computer_sessions=1),
    tool_policy={"sandboxed": True, "observe_only": True},
    notes="ACT capabilities (click/type) require explicit grant + approval; never bundled by default.",
))

_register(CapsuleProfile(
    name=CapsuleProfileName.AUTOMATION.value,
    description="Automation capsule with recursion and trigger budgets.",
    capabilities=["fs.read", "fs.write", "terminal.execute", "memory.read", "memory.write"],
    network=NetworkPolicy(mode=NetworkMode.ALLOWLIST, allowlist=["github.com"]),
    mounts=_std_mounts(),
    resources=_budget(automation_slots=1),
    tool_policy={"sandboxed": True, "max_recursion_depth": 2, "trigger_budget": 100,
                 "execution_budget": 50},
    max_autonomy="autonomy_3",
))

_register(CapsuleProfile(
    name=CapsuleProfileName.SWARM.value,
    description="Swarm worker capsule: reduced authority, collective quota enforced by parent.",
    capabilities=["fs.read", "memory.read", "memory.write"],
    network=NetworkPolicy(mode=NetworkMode.NO_NETWORK),
    mounts=_std_mounts(),
    resources=_budget(cpu_cores=0.5, ram_mb=512, llm_tokens_per_minute=10000, agent_slots=0),
    tool_policy={"sandboxed": True},
    process_policy={"max_children": 0},
    memory_scope="ephemeral",
    max_autonomy="autonomy_1",
))

_register(CapsuleProfile(
    name=CapsuleProfileName.UNTRUSTED.value,
    description="High-isolation capsule for unknown repos, downloaded scripts, generated code.",
    capabilities=["fs.read", "memory.read"],
    network=NetworkPolicy(mode=NetworkMode.NO_NETWORK),
    mounts=_std_mounts(),
    resources=_budget(cpu_cores=0.5, ram_mb=512, disk_mb=512, llm_tokens_per_minute=5000,
                      browser_sessions=0, computer_sessions=0, device_sessions=0, agent_slots=0),
    model_policy=_model(local_only=True, maximum_tokens=4000, tool_calling_allowed=False),
    tool_policy={"sandboxed": True, "approval_required": ["*"]},
    process_policy={"max_processes": 4, "allow_shell": False, "allow_privilege_escalation": False,
                    "allow_debugger_attach": False, "allow_host_process_access": False},
    secret_policy={"expose_plaintext": False, "broker_only": True, "allow_secret_use": False},
    memory_scope="ephemeral",
    isolation_floor="level_1_sandboxed_process",
    max_autonomy="autonomy_0",
    privacy_class=DataClassification.CONFIDENTIAL,
))

_register(CapsuleProfile(
    name=CapsuleProfileName.HIGH_SECURITY.value,
    description="Financial/privileged operations: strong identity, limits, approvals, immutable audit.",
    capabilities=["fs.read", "memory.read", "memory.write"],
    network=NetworkPolicy(mode=NetworkMode.ALLOWLIST, allowlist=[]),
    mounts=_std_mounts(),
    resources=_budget(),
    tool_policy={"sandboxed": True, "approval_required": ["*"]},
    secret_policy={"expose_plaintext": False, "broker_only": True},
    isolation_floor="level_1_sandboxed_process",
    max_autonomy="autonomy_1",
    privacy_class=DataClassification.SECRET,
    notes="Payment/send authority is never inherited; per-transaction approval required.",
))

_register(CapsuleProfile(
    name=CapsuleProfileName.PHYSICAL.value,
    description="Embodied operations: highest isolation, safe-state termination, human approval.",
    capabilities=["sensor.read", "robot.observe", "memory.read", "memory.write"],
    network=NetworkPolicy(mode=NetworkMode.LOCAL_ONLY),
    mounts=_std_mounts(),
    resources=_budget(device_sessions=1),
    device_policy={"sensors": ["read"], "actuators": []},
    tool_policy={"sandboxed": True, "approval_required": ["robot.*", "actuator.*", "device.*"]},
    isolation_floor="level_1_sandboxed_process",
    max_autonomy="autonomy_1",
    privacy_class=DataClassification.CONFIDENTIAL,
    notes="Actuation (navigate/manipulate/control) requires separate authorization + safe-state config.",
))

_register(CapsuleProfile(
    name=CapsuleProfileName.AMBIENT.value,
    description="Ambient sensing with per-sensor permissions and retention policy.",
    capabilities=["sensor.read", "memory.read", "memory.write"],
    network=NetworkPolicy(mode=NetworkMode.NO_NETWORK),
    mounts=_std_mounts(),
    resources=_budget(device_sessions=1),
    device_policy={"sensors": [], "require_explicit_sensor_grant": True},
    tool_policy={"sandboxed": True},
    secret_policy={"expose_plaintext": False, "broker_only": True},
    privacy_class=DataClassification.PRIVATE,
    notes="Microphone/camera/gaze/location/wearable granted individually; privacy zones enforced.",
))

_register(CapsuleProfile(
    name=CapsuleProfileName.LOCAL_ONLY.value,
    description="Privacy-sensitive tasks: local models/memory/files/tools only.",
    capabilities=["fs.read", "fs.write", "terminal.execute", "memory.read", "memory.write"],
    network=NetworkPolicy(mode=NetworkMode.NO_NETWORK),
    mounts=_std_mounts(),
    resources=_budget(),
    model_policy=_model(local_only=True, maximum_tokens=16000, context_limit=128000),
    tool_policy={"sandboxed": True},
    privacy_class=DataClassification.PRIVATE,
    notes="Cloud fallback is denied by policy; context never leaves the node.",
))

_register(CapsuleProfile(
    name=CapsuleProfileName.OFFLINE.value,
    description="Air-gapped: no network, no remote models, no A2A, no cloud.",
    capabilities=["fs.read", "fs.write", "memory.read", "memory.write"],
    network=NetworkPolicy(mode=NetworkMode.NO_NETWORK),
    mounts=_std_mounts(),
    resources=_budget(network_mbps=0.0),
    model_policy=_model(local_only=True, maximum_tokens=8000, tool_calling_allowed=False),
    tool_policy={"sandboxed": True, "allow_a2a": False, "allow_cloud": False},
    memory_scope="ephemeral",
    max_autonomy="autonomy_1",
    notes="Only explicitly mounted local capabilities.",
))


def get_profile(name: str) -> CapsuleProfile:
    key = (name or "").strip().lower()
    if key not in PROFILES:
        raise ValueError(f"Unknown capsule profile: {name!r}. Known: {sorted(PROFILES)}")
    return PROFILES[key]


def list_profiles() -> List[CapsuleProfile]:
    return [PROFILES[k] for k in sorted(PROFILES)]
