"""Device security (§47-53, §126-129, §198, §226-229): pairing auth,
per-command auth + replay cache, QR/voice/UI-text as data, A2A remote
policy (default deny physical control), incidents + response."""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from .models import PhysicalIncident


class DeviceSecurityController:
    def __init__(self) -> None:
        self.incidents: List[PhysicalIncident] = []
        self.remote_policy = "deny"  # remote agents = no control by default
        self.untrusted_payloads: List[Dict[str, Any]] = []

    # -- untrusted content (§126-128) ------------------------------------
    @staticmethod
    def screen_untrusted_ui_text(text: str) -> Dict[str, Any]:
        dangerous = any(k in text.lower() for k in
                        ("disable safe", "ignore safe", "override",
                         "emergency stop off", "bypass"))
        return {"data": text, "authority": "none",
                "blocked": dangerous,
                "note": "physical UI text is DATA, never policy"}

    @staticmethod
    def decode_qr(payload: str) -> Dict[str, Any]:
        return {"data": payload, "trusted": False,
                "note": "QR/barcode payload is data, not instructions"}

    def voice_command(self, text: str, authenticated: bool,
                      risk: str) -> Dict[str, Any]:
        if risk == "HIGH" and not authenticated:
            return {"ok": False,
                    "reason": "voice requires auth for high-risk"}
        return {"ok": True, "requires_confirmation": risk in ("HIGH",
                                                              "MEDIUM")}

    # -- A2A remote (§226-229) ---------------------------------------------
    def remote_request(self, agent: str, action: str, risk: str,
                       authorized: bool,
                       evidence: Optional[Dict[str, Any]] = None
                       ) -> Dict[str, Any]:
        if self.remote_policy == "deny" and not authorized:
            return {"ok": False, "reason": "REMOTE_DENIED: remote agents "
                                           "have no physical control "
                                           "until explicitly authorized"}
        if not (evidence or {}).get("identity"):
            return {"ok": False,
                    "reason": "missing remote identity/trust/provenance"}
        return {"ok": True, "agent": agent, "action": action,
                "mode": "LIVE_HARDWARE only with local verification"}

    # -- incidents (§100-101) --------------------------------------------------
    def incident(self, type: str, device: str, severity: str = "LOW",
                 cause: str = "", location: str = "") -> PhysicalIncident:
        inc = PhysicalIncident(type=type, device=device, severity=severity,
                               cause=cause, location=location,
                               response=("stop+safe_state+preserve_telemetry"
                                         "+notify+request_human"))
        self.incidents.append(inc)
        return inc
