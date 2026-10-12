"""
AetherOS Agent Hypervisor 1.0 — deterministic risk engine (§57-§58).

The primary risk engine is a deterministic weighted-factor sum over the
capsule's authority, side effects, data sensitivity, network exposure,
physical/financial reach, external communication, irreversibility, and
trust. An LLM is never asked "is this risky?".
"""

from __future__ import annotations

from typing import Dict, List

from kernel.core.hypervisor.types import (
    AgentCapsule,
    BlastRadius,
    NetworkMode,
    RiskAssessment,
)
from kernel.core.types import CapabilityRiskLevel, DataClassification


def _band(score: int) -> str:
    if score >= 75:
        return "CRITICAL"
    if score >= 50:
        return "HIGH"
    if score >= 25:
        return "MEDIUM"
    return "LOW"


def assess_capsule(capsule: AgentCapsule) -> RiskAssessment:
    """Deterministic risk assessment for a capsule (or capsule-to-be).

    Reads: capabilities (side-effect classes), network mode/allowlist,
    privacy class, trust level, device/physical reach, secret bindings,
    autonomy band, and irreversibility. Returns score 0-100 + band.
    """
    weights: Dict[str, int] = {}
    factors: List[str] = []

    def add(name: str, points: int, why: str) -> None:
        weights[name] = points
        if points:
            factors.append(f"{why} (+{points})")

    caps = set(capsule.capabilities)
    side_effects = {(c.split(".")[0], c) for c in caps}

    # Authority breadth: each capability family adds a little.
    families = {c.split(".")[0] for c in caps} | {c.split(":")[0] for c in caps}
    add("authority_breadth", min(12, 2 * len(families)),
        f"{len(families)} capability families")

    # Side-effect classes inferred from capability names.
    def has(*needles: str) -> bool:
        return any(any(n in c for n in needles) for c in caps)

    add("irreversible", 15 if has("delete", "destroy", "drop", "terminate",
                                  "financial", "pay", "transfer") else 0,
        "irreversible/financial-class capabilities")
    add("external_side_effect", 10 if has("execute", "terminal", "process",
                                          "browser", "network", "request",
                                          "message", "send", "publish") else 0,
        "external side-effect capabilities")
    add("communication", 8 if has("message", "send", "email", "discord",
                                  "slack", "telegram", "social") else 0,
        "external communication capabilities")
    add("physical", 20 if has("robot", "actuator", "device.control",
                              "computer.click", "computer.type") else 0,
        "physical/actuation capabilities")
    add("privacy_sensitive", 8 if has("sensor", "camera", "microphone",
                                      "screen", "observe") else 0,
        "sensor/observation capabilities")
    add("security_critical", 10 if has("secret", "credential", "auth",
                                       "token", "key") else 0,
        "credential-adjacent capabilities")

    # Network exposure.
    mode = capsule.network.mode if capsule.network else NetworkMode.NO_NETWORK
    add("network_full", 15 if mode == NetworkMode.FULL_NETWORK else 0,
        "FULL_NETWORK egress")
    add("network_allowlist", 5 if mode == NetworkMode.ALLOWLIST else 0,
        "allowlisted egress")
    add("network_local", 2 if mode in (NetworkMode.LOCAL_ONLY,
                                       NetworkMode.PRIVATE_NETWORK) else 0,
        "local/private egress")

    # Data sensitivity.
    privacy = capsule.contract.privacy_class if capsule.contract else DataClassification.INTERNAL
    sens = {DataClassification.PRIVATE: 5, DataClassification.CONFIDENTIAL: 8,
            DataClassification.SECRET: 12, DataClassification.HIGHLY_SENSITIVE: 15}
    add("data_sensitivity", sens.get(privacy, 0), f"privacy class {privacy.value}")

    # Trust and autonomy.
    add("low_trust", 8 if capsule.trust_level <= 1 else 0,
        f"trust level T{capsule.trust_level}")
    autonomy_n = int(capsule.autonomy.value.rsplit("_", 1)[-1])
    add("autonomy", min(10, 2 * autonomy_n), f"{capsule.autonomy.value}")

    # Child-of-untrusted lineage.
    if capsule.parent_capsule_id:
        add("delegated_lineage", 3, "delegated capsule lineage")

    score = min(100, sum(weights.values()))
    return RiskAssessment(score=score, band=_band(score),
                          factors=factors, weights=weights)


def blast_radius_for(capsule: AgentCapsule) -> BlastRadius:
    """Measurable blast radius from authority + mounts + policy (§57)."""
    auth = capsule.authority
    fs = sorted(set((auth.filesystem_scopes if auth else []) +
                    [m.capsule_path or f"/{m.name}" for m in capsule.mounts]))
    net = sorted(set((auth.network_scopes if auth else []) +
                     (capsule.network.allowlist if capsule.network else [])))
    creds = sorted(set(auth.credentials if auth else []))
    dev = sorted(set((auth.device_scopes if auth else []) +
                     list((capsule.device_policy or {}).get("sensors", []))))
    mem = [capsule.memory_policy.value, f"capsule:{capsule.capsule_id}"]
    fin = sorted({c for c in capsule.capabilities
                  if any(k in c for k in ("financial", "pay", "transfer", "buy"))})
    comm = sorted({c for c in capsule.capabilities
                   if any(k in c for k in ("message", "send", "email", "publish"))})
    return BlastRadius(
        filesystem_scope=fs, network_scope=net, credential_scope=creds,
        device_scope=dev, agent_scope=[capsule.agent_id],
        memory_scope=mem, financial_scope=fin, communication_scope=comm)
