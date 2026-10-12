"""Multi-device and offline execution support for the orchestrator."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
import uuid
from typing import Any, Optional

from aetheros_automation.orchestrator.models import (
    Plan, Checkpoint, OrchestrationResult,
)

logger = logging.getLogger(__name__)

_QUEUE_DIR = os.path.join(
    os.path.expanduser("~/.aetheros"), "automation", "queue"
)


class DeviceManager:
    def __init__(self):
        self._devices: dict[str, dict] = {}
        self._offline_queue: list[dict] = []
        self._online = True
        os.makedirs(_QUEUE_DIR, exist_ok=True)

    def register_device(self, device_id: str, device_info: dict):
        self._devices[device_id] = {
            **device_info,
            "registered_at": time.time(),
            "last_seen": time.time(),
        }
        logger.info("Registered device: %s", device_id)

    def unregister_device(self, device_id: str):
        self._devices.pop(device_id, None)

    def update_device_heartbeat(self, device_id: str):
        if device_id in self._devices:
            self._devices[device_id]["last_seen"] = time.time()

    def get_device(self, device_id: str) -> Optional[dict]:
        return self._devices.get(device_id)

    def list_devices(self) -> list[dict]:
        return [
            {
                "id": did,
                "last_seen": info.get("last_seen", 0),
                "registered_at": info.get("registered_at", 0),
                "name": info.get("name", did),
                "status": "online" if time.time() - info.get("last_seen", 0) < 300 else "offline",
            }
            for did, info in self._devices.items()
        ]

    async def handoff_plan(self, plan: Plan, target_device: str) -> bool:
        if target_device not in self._devices:
            logger.warning("Target device %s not registered", target_device)
            return False
        plan.metadata["handoff_to"] = target_device
        plan.metadata["handoff_from"] = "local"
        plan.metadata["handoff_at"] = time.time()
        path = os.path.join(
            _QUEUE_DIR, f"handoff_{plan.id}_{uuid.uuid4().hex[:8]}.json"
        )
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump({
                    "plan_id": plan.id,
                    "target_device": target_device,
                    "source_device": "local",
                    "plan_data": {
                        "id": plan.id,
                        "goal": plan.goal,
                        "status": plan.status,
                        "metadata": plan.metadata,
                    },
                    "timestamp": time.time(),
                }, f)
            return True
        except Exception as e:
            logger.error("Handoff failed: %s", e)
            return False

    async def handle_incoming_handoff(self, data: dict) -> Optional[Plan]:
        logger.info("Received handoff: %s", data.get("plan_id", ""))
        return None

    def set_online(self, online: bool):
        self._online = online
        logger.info("Device connectivity: %s", "online" if online else "offline")

    def is_online(self) -> bool:
        return self._online

    def queue_for_offline(self, action: dict):
        self._offline_queue.append(action)
        path = os.path.join(
            _QUEUE_DIR, f"offline_{uuid.uuid4().hex[:12]}.json"
        )
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(action, f)
        except Exception:
            pass

    async def process_offline_queue(self):
        if not self._online:
            return
        queue = list(self._offline_queue)
        self._offline_queue.clear()
        for action in queue:
            try:
                logger.info("Processing queued offline action: %s", action.get("type", "unknown"))
                await asyncio.sleep(0.1)
            except Exception as e:
                logger.error("Failed to process queued action: %s", e)

    def get_offline_queue_size(self) -> int:
        return len(self._offline_queue)

    def get_stats(self) -> dict:
        return {
            "registered_devices": len(self._devices),
            "online_devices": sum(
                1 for d in self._devices.values()
                if time.time() - d.get("last_seen", 0) < 300
            ),
            "offline_queue_size": len(self._offline_queue),
            "network_status": "online" if self._online else "offline",
        }
