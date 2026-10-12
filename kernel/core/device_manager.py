"""
Device Manager — manages device connections, capabilities, and security.

Handles device pairing, capability discovery, trust levels, and secure communication.
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Callable
from enum import Enum
from pathlib import Path

from kernel.core.types import (
    ProvenanceType,
    DataClassification,
    CapabilityRiskLevel,
    new_id,
    _now,
)
from kernel.event_bus import EventBus

logger = logging.getLogger(__name__)


class DeviceStatus(Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    AUTHENTICATING = "authenticating"
    AUTHENTICATED = "authenticated"
    ERROR = "error"
    QUARANTINED = "quarantined"


class DeviceClass(Enum):
    SENSOR = "sensor"
    ACTUATOR = "actuator"
    COMPUTE = "compute"
    STORAGE = "storage"
    NETWORK = "network"
    DISPLAY = "display"
    INPUT = "input"
    ROBOT = "robot"
    WEARABLE = "wearable"
    XR = "xr"
    IOT = "iot"
    MOBILE = "mobile"
    CUSTOM = "custom"


@dataclass
class DeviceCapability:
    """A device capability."""
    capability_id: str
    name: str
    description: str
    capability_type: str  # sensor, actuator, compute, etc.
    data_type: str = ""  # temperature, position, image, etc.
    unit: str = ""
    range_min: float = 0.0
    range_max: float = 0.0
    frequency_hz: float = 0.0
    risk_level: CapabilityRiskLevel = CapabilityRiskLevel.READ_ONLY
    requires_approval: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DeviceDescriptor:
    """Complete device descriptor."""
    device_id: str
    name: str
    device_class: DeviceClass
    manufacturer: str = ""
    model: str = ""
    firmware_version: str = ""
    serial_number: str = ""
    capabilities: List[DeviceCapability] = field(default_factory=list)
    status: DeviceStatus = DeviceStatus.DISCONNECTED
    trust_level: int = 0  # 0=unknown, 1=unverified, 2=verified, 3=trusted, 4=high, 5=system
    owner_id: str = ""
    paired_at: Optional[float] = None
    last_seen: float = field(default_factory=_now)
    location_scope: str = "local"  # local, room, building, global
    privacy_scope: DataClassification = DataClassification.INTERNAL
    battery_percent: Optional[float] = None
    thermal_celsius: Optional[float] = None
    health: str = "unknown"
    metadata: Dict[str, Any] = field(default_factory=dict)
    endpoint: str = ""  # Connection endpoint
    transport: str = ""  # bluetooth, usb, wifi, serial, etc.


class DeviceManager:
    """
    Manages device connections, capabilities, and security.
    
    Supports secure pairing, capability discovery, trust management,
    and capability-controlled device access.
    """

    def __init__(self, config, event_bus: EventBus):
        self.config = config
        self.event_bus = event_bus
        self._lock = threading.RLock()
        
        self._devices: Dict[str, DeviceDescriptor] = {}
        self._device_callbacks: Dict[str, Callable] = {}
        self._capability_handlers: Dict[str, Callable] = {}
        
        # Pairing
        self._pairing_codes: Dict[str, Dict[str, Any]] = {}
        self._pairing_timeout = 300  # 5 minutes

    def register_device(
        self,
        name: str,
        device_class: DeviceClass,
        endpoint: str,
        transport: str,
        manufacturer: str = "",
        model: str = "",
        firmware_version: str = "",
        capabilities: List[DeviceCapability] = None,
        owner_id: str = "",
        location_scope: str = "local",
        privacy_scope: DataClassification = DataClassification.INTERNAL,
        metadata: Dict[str, Any] = None,
    ) -> DeviceDescriptor:
        """Register a new device."""
        device = DeviceDescriptor(
            device_id=new_id("dev"),
            name=name,
            device_class=device_class,
            manufacturer=manufacturer,
            model=model,
            firmware_version=firmware_version,
            capabilities=capabilities or [],
            endpoint=endpoint,
            transport=transport,
            owner_id=owner_id,
            location_scope=location_scope,
            privacy_scope=privacy_scope,
            metadata=metadata or {},
        )

        with self._lock:
            self._devices[device.device_id] = device

        if self.event_bus:
            self.event_bus.emit("device.registered", {
                "device_id": device.device_id,
                "name": name,
                "class": device_class.value,
            })

        logger.info("DeviceManager: registered device %s (%s)", device.device_id, name)
        return device

    def get_device(self, device_id: str) -> Optional[DeviceDescriptor]:
        """Get a device by ID."""
        with self._lock:
            return self._devices.get(device_id)

    def list_devices(
        self,
        device_class: DeviceClass = None,
        status: DeviceStatus = None,
        owner_id: str = "",
    ) -> List[DeviceDescriptor]:
        """List devices with filters."""
        with self._lock:
            devices = list(self._devices.values())
        
        if device_class:
            devices = [d for d in devices if d.device_class == device_class]
        if status:
            devices = [d for d in devices if d.status == status]
        if owner_id:
            devices = [d for d in devices if d.owner_id == owner_id]
        
        return devices

    def connect_device(self, device_id: str) -> bool:
        """Connect to a device."""
        device = self.get_device(device_id)
        if not device:
            return False
        
        device.status = DeviceStatus.CONNECTING
        
        # In production, would establish actual connection
        # For now, simulate connection
        device.status = DeviceStatus.CONNECTED
        device.last_seen = _now()
        
        if self.event_bus:
            self.event_bus.emit("device.connected", {
                "device_id": device_id,
            })
        
        return True

    def disconnect_device(self, device_id: str) -> bool:
        """Disconnect a device."""
        device = self.get_device(device_id)
        if not device:
            return False
        
        device.status = DeviceStatus.DISCONNECTED
        
        if self.event_bus:
            self.event_bus.emit("device.disconnected", {
                "device_id": device_id,
            })
        
        return True

    def pair_device(self, device_id: str, pairing_code: str = None) -> str:
        """Initiate device pairing."""
        device = self.get_device(device_id)
        if not device:
            raise ValueError(f"Device not found: {device_id}")
        
        code = pairing_code or str(uuid.uuid4().int)[:6]
        
        pairing_info = {
            "device_id": device_id,
            "code": code,
            "created_at": _now(),
            "expires_at": _now() + self._pairing_timeout,
            "verified": False,
        }
        
        with self._lock:
            self._pairing_codes[code] = pairing_info
        
        if self.event_bus:
            self.event_bus.emit("device.pairing_initiated", {
                "device_id": device_id,
                "code": code,
            })
        
        return code

    def verify_pairing(self, code: str) -> bool:
        """Verify a pairing code."""
        with self._lock:
            pairing = self._pairing_codes.get(code)
        
        if not pairing:
            return False
        
        if _now() > pairing["expires_at"]:
            with self._lock:
                self._pairing_codes.pop(code, None)
            return False
        
        device_id = pairing["device_id"]
        device = self.get_device(device_id)
        if not device:
            return False
        
        device.status = DeviceStatus.AUTHENTICATED
        device.paired_at = _now()
        pairing["verified"] = True
        
        if self.event_bus:
            self.event_bus.emit("device.paired", {
                "device_id": device_id,
            })
        
        return True

    def update_device_status(self, device_id: str, status: DeviceStatus) -> bool:
        """Update device status."""
        device = self.get_device(device_id)
        if not device:
            return False
        
        device.status = status
        device.last_seen = _now()
        
        if self.event_bus:
            self.event_bus.emit("device.status_changed", {
                "device_id": device_id,
                "status": status.value,
            })
        
        return True

    def update_device_telemetry(
        self,
        device_id: str,
        battery_percent: float = None,
        thermal_celsius: float = None,
        health: str = None,
    ) -> bool:
        """Update device telemetry."""
        device = self.get_device(device_id)
        if not device:
            return False
        
        if battery_percent is not None:
            device.battery_percent = battery_percent
        if thermal_celsius is not None:
            device.thermal_celsius = thermal_celsius
        if health:
            device.health = health
        
        device.last_seen = _now()
        return True

    def register_capability_handler(
        self,
        capability_id: str,
        handler: Callable[[DeviceCapability, Dict[str, Any]], Any],
    ) -> None:
        """Register a handler for a device capability."""
        with self._lock:
            self._capability_handlers[capability_id] = handler

    def invoke_capability(
        self,
        device_id: str,
        capability_id: str,
        params: Dict[str, Any] = None,
    ) -> Any:
        """Invoke a device capability."""
        device = self.get_device(device_id)
        if not device:
            raise ValueError(f"Device not found: {device_id}")
        
        if device.status != DeviceStatus.AUTHENTICATED:
            raise PermissionError(f"Device not authenticated: {device_id}")
        
        # Find capability
        capability = None
        for cap in device.capabilities:
            if cap.capability_id == capability_id:
                capability = cap
                break
        
        if not capability:
            raise ValueError(f"Capability not found: {capability_id}")
        
        # Check approval requirement
        if capability.requires_approval:
            raise PermissionError(f"Capability requires approval: {capability_id}")
        
        # Invoke handler
        handler = self._capability_handlers.get(capability_id)
        if not handler:
            raise ValueError(f"No handler for capability: {capability_id}")
        
        result = handler(capability, params or {})
        
        if self.event_bus:
            self.event_bus.emit("device.capability_invoked", {
                "device_id": device_id,
                "capability_id": capability_id,
                "params": params,
            })
        
        return result

    def register_callback(self, event: str, callback: Callable) -> None:
        """Register a device event callback."""
        self._device_callbacks[event] = callback

    def quarantine_device(self, device_id: str, reason: str = "security") -> bool:
        """Quarantine a device."""
        device = self.get_device(device_id)
        if not device:
            return False
        
        device.status = DeviceStatus.QUARANTINED
        
        if self.event_bus:
            self.event_bus.emit("device.quarantined", {
                "device_id": device_id,
                "reason": reason,
            })
        
        return True

    def release_quarantine(self, device_id: str) -> bool:
        """Release device from quarantine."""
        device = self.get_device(device_id)
        if not device:
            return False
        
        device.status = DeviceStatus.DISCONNECTED
        
        if self.event_bus:
            self.event_bus.emit("device.quarantine_released", {
                "device_id": device_id,
            })
        
        return True

    def get_device_capabilities(self, device_id: str) -> List[DeviceCapability]:
        """Get device capabilities."""
        device = self.get_device(device_id)
        if not device:
            return []
        return device.capabilities

    def get_stats(self) -> Dict[str, Any]:
        """Get device manager statistics."""
        with self._lock:
            total = len(self._devices)
            by_status: Dict[str, int] = {}
            by_class: Dict[str, int] = {}
            connected = 0
            
            for device in self._devices.values():
                by_status[device.status.value] = by_status.get(device.status.value, 0) + 1
                by_class[device.device_class.value] = by_class.get(device.device_class.value, 0) + 1
                if device.status == DeviceStatus.CONNECTED:
                    connected += 1

        return {
            "total_devices": total,
            "connected": connected,
            "by_status": by_status,
            "by_class": by_class,
        }

    def shutdown(self) -> None:
        """Shutdown the device manager."""
        logger.info("DeviceManager: shutting down")
        with self._lock:
            # Disconnect all devices
            for device in self._devices.values():
                if device.status in (DeviceStatus.CONNECTED, DeviceStatus.AUTHENTICATED):
                    device.status = DeviceStatus.DISCONNECTED
            
            self._devices.clear()
            self._device_callbacks.clear()
            self._capability_handlers.clear()
            self._pairing_codes.clear()