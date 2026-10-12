"""Tool/extension/robot/network registration contracts (§242-247):
every consequential capability declares identity, risk, permissions,
resources, data/network/secret access, audit level. Missing metadata
rejects registration. Includes a registry auditor for legacy tools."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class ToolManifest:
    identity: str = ""
    capabilities: tuple = ()
    permissions: tuple = ()
    risk: str = "R1"
    side_effects: tuple = ()
    reversibility: str = "reversible"
    data_access: tuple = ()
    network_access: tuple = ()
    secret_access: tuple = ()
    audit_level: str = "standard"
    version: str = "v1"


@dataclass(frozen=True)
class PhysicalToolContract(ToolManifest):
    force_n: float = 0.0
    speed_ms: float = 0.0
    energy_j: float = 0.0
    workspace: str = ""
    collision_policy: str = ""
    human_proximity: str = ""
    emergency_stop: bool = True


@dataclass(frozen=True)
class NetworkToolContract(ToolManifest):
    origins: tuple = ()
    protocols: tuple = ("https",)
    ports: tuple = (443,)
    redirects: str = "deny"
    data: tuple = ()
    credentials: str = "none"


class ToolContractValidator:
    REQUIRED = ("identity", "capabilities", "permissions", "risk",
                "reversibility", "audit_level")

    def validate(self, manifest: ToolManifest) -> Dict[str, Any]:
        missing = [f for f in self.REQUIRED if not getattr(manifest, f)]
        valid_risks = {f"R{i}" for i in range(9)}
        errors = [f"missing {m}" for m in missing]
        if manifest.risk not in valid_risks:
            errors.append(f"invalid risk {manifest.risk}")
        if manifest.secret_access and "secret" not in " ".join(
                manifest.permissions).lower():
            errors.append("secret access without secret permission")
        return {"valid": not errors, "errors": errors}

    def audit_registry(self, entries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Classify legacy tools: full manifest / partial / missing."""
        full, partial, missing = [], [], []
        for e in entries:
            keys = set(e)
            need = {"identity", "capabilities", "permissions", "risk",
                    "reversibility", "audit_level", "data_access",
                    "network_access", "secret_access"}
            if need <= keys:
                full.append(e.get("name", "?"))
            elif keys & need:
                partial.append(e.get("name", "?"))
            else:
                missing.append(e.get("name", "?"))
        return {"full": full, "partial": partial, "missing": missing,
                "maturity": ("S4" if not partial and not missing else
                             "S2" if full else "S0")}
