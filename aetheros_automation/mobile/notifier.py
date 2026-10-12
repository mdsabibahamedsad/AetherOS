from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlencode

from aetheros_automation.models.models import ApprovalRequest

logger = logging.getLogger(__name__)

_NOTIFIERS_DIR = os.path.expanduser("~/.aetheros/automation/notifiers")


@dataclass
class _Device:
    token: str = ""
    platform: str = "ios"
    registered_at: float = 0.0


class MobileNotifier:
    """Send push notifications through one of several supported backends.

    Backends are tried in priority order — the first configured backend
    wins.  Supported backends:

    * `pushover <https://pushover.net>`_ — user + token required
    * `gotify <https://gotify.net>`_ — server URL + app token required
    * `ntfy <https://ntfy.sh>`_ — topic required
    * `apprise <https://github.com/caronc/apprise>`_ — URL required

    Devices are persisted to ``~/.aetheros/automation/notifiers/devices.json``
    so push registrations survive restarts.
    """

    def __init__(self) -> None:
        os.makedirs(_NOTIFIERS_DIR, exist_ok=True)
        self._devices: dict[str, _Device] = {}
        self._loaded = False

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------

    async def send_notification(
        self,
        title: str,
        body: str,
        data: dict[str, Any] | None = None,
    ) -> bool:
        """Send a generic push notification through the first available backend.

        Returns ``True`` if at least one backend delivered successfully.
        """
        if data is None:
            data = {}

        backends = [
            self._send_pushover,
            self._send_gotify,
            self._send_ntfy,
            self._send_apprise,
        ]

        for backend in backends:
            try:
                result = await backend(title, body, data)
                if result:
                    logger.info(
                        "Notification sent via %s: %s",
                        backend.__name__,
                        title,
                    )
                    return True
            except Exception:
                logger.debug(
                    "Backend %s failed for notification",
                    backend.__name__,
                    exc_info=True,
                )

        logger.warning("No backend could deliver notification: %s", title)
        return False

    async def send_task_update(
        self,
        task: Any,
        event_type: str,
    ) -> bool:
        """Send a notification about a task status change."""
        status = task.status.value if hasattr(task, "status") and task.status else "unknown"
        title = f"Task {event_type}: {task.name}"
        body = (
            f"Task {task.id[:8]} is now {status}.\n"
            f"Agent: {task.agent.value if hasattr(task, 'agent') and task.agent else 'N/A'}\n"
            f"Progress: {getattr(task, 'progress', 0):.0f}%"
        )
        if getattr(task, "error", None):
            body += f"\nError: {task.error}"

        return await self.send_notification(
            title=title,
            body=body,
            data={
                "task_id": task.id,
                "event_type": event_type,
                "status": status,
            },
        )

    async def send_approval_request(
        self,
        approval_id: str,
        description: str,
    ) -> bool:
        """Notify the user that an action requires approval."""
        return await self.send_notification(
            title="Approval Required",
            body=description,
            data={
                "approval_id": approval_id,
                "type": "approval",
            },
        )

    async def send_emergency_alert(self, message: str) -> bool:
        """Send a high-priority emergency alert."""
        return await self.send_notification(
            title="🚨 Emergency Alert",
            body=message,
            data={
                "priority": "emergency",
                "type": "emergency",
            },
        )

    async def register_device(
        self,
        token: str,
        platform: str = "ios",
    ) -> bool:
        """Register a mobile device token for push notifications."""
        await self._ensure_loaded()
        device = _Device(
            token=token,
            platform=platform,
            registered_at=time.time(),
        )
        self._devices[token] = device
        await self._persist_devices()
        logger.info("Device registered: %s (%s)", token[:8], platform)
        return True

    # ------------------------------------------------------------------
    # backend: Pushover
    # ------------------------------------------------------------------

    async def _send_pushover(
        self,
        title: str,
        body: str,
        data: dict[str, Any],
    ) -> bool:
        user = os.environ.get("PUSHOVER_USER", "")
        token = os.environ.get("PUSHOVER_TOKEN", "")
        if not user or not token:
            return False

        payload = {
            "token": token,
            "user": user,
            "title": title,
            "message": body,
            "priority": data.get("priority", 0),
            "sound": "pushover",
        }

        try:
            import httpx

            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    "https://api.pushover.net/1/messages.json",
                    data=payload,
                )
                return resp.status_code == 200
        except ImportError:
            return await self._send_pushover_sync(title, body, data)
        except Exception:
            logger.exception("Pushover send failed")
            return False

    async def _send_pushover_sync(
        self,
        title: str,
        body: str,
        data: dict[str, Any],
    ) -> bool:
        """Fallback using urllib when httpx is not available."""
        user = os.environ.get("PUSHOVER_USER", "")
        token = os.environ.get("PUSHOVER_TOKEN", "")
        if not user or not token:
            return False

        try:
            from urllib.request import Request, urlopen

            payload = {
                "token": token,
                "user": user,
                "title": title,
                "message": body,
                "priority": data.get("priority", 0),
                "sound": "pushover",
            }
            req = Request(
                "https://api.pushover.net/1/messages.json",
                data=urlencode(payload).encode(),
            )
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, lambda: urlopen(req).status == 200)
            return result
        except Exception:
            logger.exception("Pushover sync send failed")
            return False

    # ------------------------------------------------------------------
    # backend: Gotify
    # ------------------------------------------------------------------

    async def _send_gotify(
        self,
        title: str,
        body: str,
        data: dict[str, Any],
    ) -> bool:
        server = os.environ.get("GOTIFY_SERVER", "")
        app_token = os.environ.get("GOTIFY_TOKEN", "")
        if not server or not app_token:
            return False

        payload = {
            "title": title,
            "message": body,
            "priority": data.get("priority", 5),
        }

        try:
            import httpx

            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    f"{server.rstrip('/')}/message?token={app_token}",
                    json=payload,
                )
                return resp.status_code == 200
        except ImportError:
            return await self._send_gotify_sync(title, body, data, server, app_token)
        except Exception:
            logger.exception("Gotify send failed")
            return False

    async def _send_gotify_sync(
        self,
        title: str,
        body: str,
        data: dict[str, Any],
        server: str,
        app_token: str,
    ) -> bool:
        try:
            from urllib.request import Request, urlopen

            payload = json.dumps({
                "title": title,
                "message": body,
                "priority": data.get("priority", 5),
            }).encode()
            url = f"{server.rstrip('/')}/message?token={app_token}"
            req = Request(url, data=payload, headers={"Content-Type": "application/json"})
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, lambda: urlopen(req).status == 200)
            return result
        except Exception:
            logger.exception("Gotify sync send failed")
            return False

    # ------------------------------------------------------------------
    # backend: ntfy
    # ------------------------------------------------------------------

    async def _send_ntfy(
        self,
        title: str,
        body: str,
        data: dict[str, Any],
    ) -> bool:
        topic = os.environ.get("NTFY_TOPIC", "")
        server = os.environ.get("NTFY_SERVER", "https://ntfy.sh")
        if not topic:
            return False

        payload = {
            "topic": topic,
            "title": title,
            "message": body,
            "priority": data.get("priority", 3),
            "tags": data.get("tags", []),
        }

        auth_header = {}
        auth_token = os.environ.get("NTFY_TOKEN", "")
        if auth_token:
            auth_header["Authorization"] = f"Bearer {auth_token}"

        try:
            import httpx

            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    f"{server.rstrip('/')}",
                    json=payload,
                    headers=auth_header,
                )
                return resp.status_code == 200
        except ImportError:
            return await self._send_ntfy_sync(
                title, body, data, topic, server, auth_header,
            )
        except Exception:
            logger.exception("ntfy send failed")
            return False

    async def _send_ntfy_sync(
        self,
        title: str,
        body: str,
        data: dict[str, Any],
        topic: str,
        server: str,
        auth_header: dict[str, str],
    ) -> bool:
        try:
            from urllib.request import Request, urlopen

            payload = json.dumps({
                "topic": topic,
                "title": title,
                "message": body,
                "priority": data.get("priority", 3),
                "tags": data.get("tags", []),
            }).encode()
            headers = {"Content-Type": "application/json"}
            headers.update(auth_header)
            req = Request(f"{server.rstrip('/')}", data=payload, headers=headers)
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, lambda: urlopen(req).status == 200)
            return result
        except Exception:
            logger.exception("ntfy sync send failed")
            return False

    # ------------------------------------------------------------------
    # backend: Apprise
    # ------------------------------------------------------------------

    async def _send_apprise(
        self,
        title: str,
        body: str,
        data: dict[str, Any],
    ) -> bool:
        url = os.environ.get("APPRISE_URL", "")
        if not url:
            return False

        payload = {
            "title": title,
            "body": body,
            "type": "info",
            "format": "text",
            "priority": data.get("priority", 0),
        }

        try:
            import httpx

            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    f"{url.rstrip('/')}/notify",
                    json=payload,
                )
                return resp.status_code in (200, 201, 204)
        except ImportError:
            return await self._send_apprise_sync(title, body, data, url)
        except Exception:
            logger.exception("Apprise send failed")
            return False

    async def _send_apprise_sync(
        self,
        title: str,
        body: str,
        data: dict[str, Any],
        url: str,
    ) -> bool:
        try:
            from urllib.request import Request, urlopen

            payload = json.dumps({
                "title": title,
                "body": body,
                "type": "info",
                "format": "text",
                "priority": data.get("priority", 0),
            }).encode()
            req = Request(
                f"{url.rstrip('/')}/notify",
                data=payload,
                headers={"Content-Type": "application/json"},
            )
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, lambda: urlopen(req).status in (200, 201, 204)
            )
            return result
        except Exception:
            logger.exception("Apprise sync send failed")
            return False

    # ------------------------------------------------------------------
    # persistence
    # ------------------------------------------------------------------

    async def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        self._loaded = True
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._load_devices)

    def _load_devices(self) -> None:
        path = os.path.join(_NOTIFIERS_DIR, "devices.json")
        if not os.path.isfile(path):
            return
        try:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
            for entry in data.get("devices", []):
                device = _Device(
                    token=entry.get("token", ""),
                    platform=entry.get("platform", "ios"),
                    registered_at=entry.get("registered_at", 0.0),
                )
                if device.token:
                    self._devices[device.token] = device
        except Exception:
            logger.exception("Failed to load devices")

    async def _persist_devices(self) -> None:
        path = os.path.join(_NOTIFIERS_DIR, "devices.json")
        data = {
            "devices": [
                {
                    "token": d.token,
                    "platform": d.platform,
                    "registered_at": d.registered_at,
                }
                for d in self._devices.values()
            ]
        }
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _write_json, path, data)


def _write_json(path: str, data: dict[str, Any]) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, default=str)
