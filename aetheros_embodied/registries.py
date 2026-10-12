"""Registries: devices, robots, actuators, capabilities (§6-8) +
secure pairing (§48) + credential broker (§49: secrets never reach LLM).

Unknown devices are UNTRUSTED_DEVICE and get OBSERVE_ONLY (§169).
"""
from __future__ import annotations

import secrets
import time
from typing import Any, Dict, List, Optional

from .models import DeviceCapability, Permission, PhysicalDevice, Robot

DEVICE_KINDS = ["camera", "microphone", "lidar", "radar", "imu", "gps",
                "temperature", "humidity", "pressure", "force", "touch",
                "distance", "motion", "industrial", "lab_instrument",
                "robotic_arm", "mobile_robot", "drone", "printer_3d",
                "cnc", "plc", "smart_device", "iot_device"]

CAPABILITIES = ["READ_TEMPERATURE", "READ_POSITION", "CAPTURE_IMAGE",
                "MOVE", "ROTATE", "GRIP", "RELEASE", "PUSH", "PULL",
                "PRESS", "PICK", "PLACE", "WELD", "PRINT", "DRILL",
                "DISPENSE", "HEAT", "COOL", "MIX", "MEASURE"]


class CapabilityRegistry:
    def __init__(self) -> None:
        self.caps: Dict[str, DeviceCapability] = {}
        for name in CAPABILITIES:
            risky = name in ("WELD", "DRILL", "HEAT", "MOVE", "PICK",
                             "PLACE", "DISPENSE")
            self.caps[name] = DeviceCapability(
                name=name,
                risk="HIGH" if risky else "LOW",
                required_permission=(Permission.CONTROLLED_ACTION
                                     if risky else Permission.OBSERVE),
                verification_method=("sensor" if risky else "telemetry"))

    def get(self, name: str) -> Optional[DeviceCapability]:
        return self.caps.get(name)

    def register(self, cap: DeviceCapability) -> None:
        self.caps[cap.name] = cap


class CredentialBroker:
    """Holds device secrets; hands adapters short-lived scoped tokens.
    Nothing here is ever serialized into prompts."""

    def __init__(self) -> None:
        self._secrets: Dict[str, str] = {}
        self._tokens: Dict[str, Dict[str, Any]] = {}

    def store(self, device_id: str, secret: str) -> None:
        self._secrets[device_id] = secret

    def token_for(self, device_id: str, scope: str,
                  ttl_s: float = 300.0) -> str:
        if device_id not in self._secrets:
            raise ValueError(f"no credential for {device_id}")
        tok = secrets.token_hex(16)
        self._tokens[tok] = {"device": device_id, "scope": scope,
                             "exp": time.time() + ttl_s}
        return tok

    def check(self, token: str, device_id: str, scope: str) -> bool:
        rec = self._tokens.get(token)
        if not rec or rec["exp"] < time.time():
            self._tokens.pop(token, None)
            return False
        return rec["device"] == device_id and rec["scope"] == scope


class PhysicalDeviceRegistry:
    def __init__(self, broker: Optional[CredentialBroker] = None) -> None:
        self.devices: Dict[str, PhysicalDevice] = {}
        self.broker = broker or CredentialBroker()
        self.audit: List[Dict[str, Any]] = []

    def _log(self, kind: str, **kw: Any) -> None:
        self.audit.append({"kind": kind, "at": time.time(), **kw})

    # -- pairing: discover -> authenticate -> verify -> authorize -> register
    def pair(self, device: PhysicalDevice, credential: str,
             verifier: str = "operator") -> PhysicalDevice:
        if not credential:
            raise ValueError("pairing requires a credential")
        self.broker.store(device.id, credential)
        device.trust = "UNTRUSTED_DEVICE"  # paired != trusted
        self.devices[device.id] = device
        self._log("paired", device=device.id, by=verifier)
        return device

    def attest(self, device_id: str, firmware_ok: bool,
               identity_ok: bool) -> str:
        dev = self._require(device_id)
        dev.trust = ("TRUSTED" if (firmware_ok and identity_ok)
                     else "UNTRUSTED_DEVICE")
        self._log("attested", device=device_id, trust=dev.trust)
        return dev.trust

    def authorize(self, device_id: str,
                  permissions: List[str]) -> None:
        dev = self._require(device_id)
        if dev.trust != "TRUSTED":
            raise ValueError("UNTRUSTED_DEVICE cannot receive permissions")
        dev.permissions = permissions
        self._log("authorized", device=device_id,
                  permissions=permissions)

    def revoke(self, device_id: str) -> None:
        dev = self._require(device_id)
        dev.permissions = [Permission.READ_ONLY]
        dev.trust = "UNTRUSTED_DEVICE"
        self._log("revoked", device=device_id)

    def lock(self, device_id: str, locked: bool = True) -> None:
        dev = self._require(device_id)
        dev.locked_by_human = locked
        self._log("lock", device=device_id, locked=locked)

    def set_health(self, device_id: str, health: str) -> None:
        self._require(device_id).health = health

    def list(self, kind: str = "") -> List[PhysicalDevice]:
        return [d for d in self.devices.values()
                if not kind or d.kind == kind]

    def controllable(self, device_id: str) -> bool:
        d = self._require(device_id)
        return (d.trust == "TRUSTED" and not d.locked_by_human
                and not d.maintenance and d.health != "fault")

    def _require(self, device_id: str) -> PhysicalDevice:
        try:
            return self.devices[device_id]
        except KeyError:
            raise ValueError(f"HARDWARE_UNAVAILABLE: unknown device {device_id}")


class RobotRegistry(PhysicalDeviceRegistry):
    def __init__(self, broker: Optional[CredentialBroker] = None) -> None:
        super().__init__(broker)
        self.robots: Dict[str, Robot] = {}

    def register_robot(self, robot: Robot) -> Robot:
        self.robots[robot.id] = robot
        return robot

    def get_robot(self, robot_id: str) -> Robot:
        try:
            return self.robots[robot_id]
        except KeyError:
            raise ValueError(f"HARDWARE_UNAVAILABLE: unknown robot {robot_id}")


class ActuatorRegistry:
    def __init__(self) -> None:
        self.actuators: Dict[str, Dict[str, Any]] = {}

    def register(self, actuator_id: str, device_id: str,
                 capabilities: List[str]) -> None:
        self.actuators[actuator_id] = {"device": device_id,
                                       "capabilities": capabilities,
                                       "state": "idle"}

    def state(self, actuator_id: str) -> Dict[str, Any]:
        try:
            return self.actuators[actuator_id]
        except KeyError:
            raise ValueError(f"HARDWARE_UNAVAILABLE: {actuator_id}")
