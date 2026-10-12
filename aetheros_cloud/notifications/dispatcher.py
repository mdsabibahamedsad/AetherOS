"""Multi-channel notification dispatcher."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable, Dict, List, Optional

from aetheros_cloud.models import NotificationChannel, NotificationEvent

logger = logging.getLogger(__name__)


class NotificationDispatcher:
    """Dispatches notifications to configured channels.

    Reuses existing Hermes gateway/messaging infrastructure.
    """

    def __init__(self):
        self._handlers: Dict[NotificationChannel, List[Callable]] = {
            channel: [] for channel in NotificationChannel
        }
        self._event_routing: Dict[NotificationEvent, List[NotificationChannel]] = {}
        self._gateway = None

    def register_channel(self, channel: NotificationChannel, handler: Callable):
        self._handlers[channel].append(handler)

    def route_event(self, event: NotificationEvent, *channels: NotificationChannel):
        self._event_routing.setdefault(event, []).extend(channels)

    def set_gateway(self, gateway: Any):
        self._gateway = gateway

    async def notify(
        self,
        event: NotificationEvent,
        title: str,
        message: str,
        data: Optional[Dict[str, Any]] = None,
        channels: Optional[List[NotificationChannel]] = None,
        user_id: str = "",
    ):
        channels = channels or self._event_routing.get(event, [NotificationChannel.DESKTOP])
        payload = {
            "event": event.value,
            "title": title,
            "message": message,
            "data": data or {},
            "user_id": user_id,
        }
        for channel in channels:
            for handler in self._handlers.get(channel, []):
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(payload)
                    else:
                        handler(payload)
                except Exception as e:
                    logger.error("Notification handler failed on %s: %s", channel.value, e)

        if self._gateway and channels and not user_id:
            await self._send_via_gateway(event, title, message, data)

    async def _send_via_gateway(self, event: NotificationEvent, title: str, message: str, data: dict):
        try:
            if hasattr(self._gateway, "broadcast"):
                await self._gateway.broadcast("notification", {
                    "event": event.value, "title": title, "message": message, "data": data,
                })
        except Exception as e:
            logger.debug("Gateway notification failed: %s", e)

    def setup_default_routes(self):
        self.route_event(NotificationEvent.TASK_ASSIGNED, NotificationChannel.DESKTOP, NotificationChannel.MOBILE)
        self.route_event(NotificationEvent.TASK_COMPLETED, NotificationChannel.DESKTOP)
        self.route_event(NotificationEvent.WORKFLOW_COMPLETED, NotificationChannel.DESKTOP, NotificationChannel.EMAIL)
        self.route_event(NotificationEvent.WORKFLOW_FAILED, NotificationChannel.DESKTOP, NotificationChannel.EMAIL)
        self.route_event(NotificationEvent.MEMBER_JOINED, NotificationChannel.DESKTOP, NotificationChannel.SLACK)
        self.route_event(NotificationEvent.MEMBER_LEFT, NotificationChannel.DESKTOP)
        self.route_event(NotificationEvent.SHARE_CREATED, NotificationChannel.DESKTOP)
        self.route_event(NotificationEvent.DEPLOYMENT_COMPLETED, NotificationChannel.DESKTOP, NotificationChannel.TELEGRAM)
        self.route_event(NotificationEvent.DEPLOYMENT_FAILED, NotificationChannel.DESKTOP, NotificationChannel.TELEGRAM, NotificationChannel.EMAIL)
        self.route_event(NotificationEvent.SYSTEM_ALERT, NotificationChannel.DESKTOP, NotificationChannel.EMAIL, NotificationChannel.SLACK)
        self.route_event(NotificationEvent.MENTION, NotificationChannel.DESKTOP, NotificationChannel.MOBILE)
        self.route_event(NotificationEvent.COMMENT, NotificationChannel.DESKTOP)

    # Built-in handlers for desktop/logging
    def _setup_builtin_handlers(self):
        async def _desktop_handler(payload: dict):
            logger.info("NOTIFICATION [%s] %s: %s", payload["event"], payload["title"], payload["message"])

        async def _email_handler(payload: dict):
            logger.info("EMAIL [%s] To: %s Subject: %s", payload["event"], payload.get("user_id", "all"), payload["title"])

        self.register_channel(NotificationChannel.DESKTOP, _desktop_handler)
        self.register_channel(NotificationChannel.EMAIL, _email_handler)

    def __init__(self):
        self._handlers: Dict[NotificationChannel, List[Callable]] = {
            channel: [] for channel in NotificationChannel
        }
        self._event_routing: Dict[NotificationEvent, List[NotificationChannel]] = {}
        self._gateway = None
        self._setup_builtin_handlers()
