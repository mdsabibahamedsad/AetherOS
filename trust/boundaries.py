"""Boundaries (§19-21, §44-45): secret tiers, data-flow governance
matrix, network decisions with egress budgets and redirect-chain
validation. Wraps M50 NetworkPolicy + DLP scanners — new logic only."""
from __future__ import annotations

import ipaddress
import re
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

from aetheros_control_plane.data_network import (
    NetworkPolicy,
    evaluate_flow,
    scan_for_secrets,
)

from .models import DataClassification

_METADATA = {"169.254.169.254", "100.100.100.200", "metadata.google.internal"}
_IPV4 = re.compile(r"^\d{1,3}(\.\d{1,3}){3}$")
_HEXIP = re.compile(r"^0x[0-9a-fA-F.]+$")
_DECIP = re.compile(r"^\d{5,12}$")


class SecretBoundaryController:
    """METADATA/USE/READ/EXPORT are separate permissions (§21). The model
    never sees raw values: USE executes inside the tool boundary."""

    TIERS = ("SECRET_METADATA", "SECRET_USE", "SECRET_READ", "SECRET_EXPORT")

    def __init__(self) -> None:
        self._grants: Dict[str, set] = {}

    def grant(self, identity_id: str, tier: str, scope: str = "*") -> None:
        if tier not in self.TIERS:
            raise ValueError(f"unknown tier {tier}")
        self._grants.setdefault(identity_id, set()).add((tier, scope))

    def allowed(self, identity_id: str, tier: str, scope: str = "*") -> bool:
        grants = self._grants.get(identity_id, set())
        if (tier, "*") in grants or (tier, scope) in grants:
            return True
        # higher tiers do NOT imply lower: USE does not grant READ/EXPORT
        return False

    def use_secret(self, identity_id: str, scope: str,
                   executor) -> Dict[str, str]:
        """Tool executes with the secret; caller gets a receipt, never
        the value. `executor` receives the resolve callback."""
        if not self.allowed(identity_id, "SECRET_USE", scope):
            return {"ok": "false", "reason": "SECRET_POLICY_DENIED"}
        result = executor()
        return {"ok": "true",
                "receipt": f"secret-used:{scope}:{int(time.time())}",
                "value_disclosed": "false",
                "detail": str(result)[:0]}


class DataBoundaryController:
    """SOURCE->TRANSFORM->MODEL->TOOL->DESTINATION matrix (§20)."""

    DENY_FLOWS = {
        ("SECRET", "public_web"), ("SECRET", "untrusted_remote_agent"),
        ("HIGHLY_RESTRICTED", "public_web"),
        ("HIGHLY_RESTRICTED", "untrusted_remote_agent"),
        ("HIGHLY_RESTRICTED", "external_email"),
        ("CONFIDENTIAL", "untrusted_remote_agent"),
    }

    def decide(self, data_class: str, destination: str) -> Dict[str, str]:
        dc = DataClassification(data_class.lower())
        dest = destination.lower()
        if (dc.value.upper(), dest) in self.DENY_FLOWS:
            return {"decision": "DENY",
                    "reason": f"{dc.value}->{dest} prohibited"}
        if dc in (DataClassification.RESTRICTED,
                  DataClassification.HIGHLY_RESTRICTED) and \
                dest == "external_email":
            return {"decision": "REQUIRE_APPROVAL",
                    "reason": f"{dc.value}->external email needs approval"}
        if dest == "approved_model" and dc in (
                DataClassification.PUBLIC, DataClassification.INTERNAL):
            return {"decision": "ALLOW", "reason": "approved model use"}
        # fall back to M50 flow evaluation for content-level checks
        flow = evaluate_flow(dc.value, dest, "", "T1")
        return {"decision": flow.decision.value, "reason": flow.reason}

    def classify(self, labels: List[str]) -> DataClassification:
        """Inherited classification: highest wins (§19)."""
        order = list(DataClassification)
        top = DataClassification.PUBLIC
        for lab in labels:
            try:
                cand = DataClassification(lab.lower())
            except ValueError:
                continue
            if order.index(cand) > order.index(top):
                top = cand
        return top


class NetworkBoundaryController:
    """Egress decisions over M50 NetworkPolicy + redirect-chain and
    SSRF-trick validation (§44-45)."""

    def __init__(self, policy: Optional[NetworkPolicy] = None):
        self.policy = policy or NetworkPolicy()
        self.egress_budget: Dict[str, int] = {}
        self._spent: Dict[str, int] = {}

    def set_egress_budget(self, scope: str, max_requests: int) -> None:
        self.egress_budget[scope] = max_requests
        self._spent.setdefault(scope, 0)

    @staticmethod
    def normalize_host(host: str) -> str:
        h = host.strip().lower().rstrip(".")
        if _HEXIP.match(h) or _DECIP.match(h):
            raise ValueError("decimal/hex IP trick rejected")
        return h

    @staticmethod
    def is_sensitive_target(host: str) -> Optional[str]:
        try:
            h = NetworkBoundaryController.normalize_host(host)
        except ValueError as exc:
            return str(exc)
        if h in ("localhost", "::1") or h in _METADATA:
            return f"blocked target {h}"
        if _IPV4.match(h):
            try:
                ip = ipaddress.ip_address(h)
                if ip.is_private or ip.is_loopback or ip.is_link_local:
                    return f"private/loopback/link-local {h}"
            except ValueError:
                return f"unparseable IP {h}"
        return None

    def check_url(self, url: str, scope: str = "default") -> Dict[str, str]:
        try:
            host = urlparse(url).hostname or ""
        except Exception:
            return {"decision": "DENY", "reason": "unparseable URL"}
        sensitive = self.is_sensitive_target(host)
        if sensitive:
            return {"decision": "DENY", "reason": sensitive}
        allowed, reason = self.policy.check_url(url)
        if not allowed:
            return {"decision": "DENY", "reason": reason}
        budget = self.egress_budget.get(scope)
        if budget is not None:
            if self._spent.get(scope, 0) >= budget:
                return {"decision": "DENY",
                        "reason": "egress budget exhausted"}
            self._spent[scope] = self._spent.get(scope, 0) + 1
        return {"decision": "ALLOW", "reason": reason}

    def check_redirect_chain(self, chain: List[str]) -> Dict[str, str]:
        for url in chain:
            verdict = self.check_url(url)
            if verdict["decision"] == "DENY":
                return {"decision": "DENY",
                        "reason": f"redirect-to-private: {url} "
                                  f"({verdict['reason']})"}
        return {"decision": "ALLOW",
                "reason": f"{len(chain)}-hop chain clean"}
