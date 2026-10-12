"""AetherOS Integrations — Enterprise Automation, Integrations & Workflow Engine.

A single architecture for connecting AetherOS to cloud services, desktop
apps, communication platforms, developer tools, business software, and AI
providers — with authentication, permissions, health monitoring,
synchronization, background jobs, webhooks, events, streaming, caching, and
an offline queue.

Facade: ``IntegrationPlatform`` wires the Integration Manager, Auth Engine,
Webhook Engine, Event Bus, Scheduler, Workflow Engine, Monitor, Offline
Queue, and Sync Engine together.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, Optional

from aetheros_integrations import auth, context, events, manager, monitoring, scheduler, security, sync, webhooks, workflow
from aetheros_integrations.config import get_aetheros_dir, load_integrations_settings
from aetheros_integrations.events import EventBus
from aetheros_integrations.manager import IntegrationManager
from aetheros_integrations.monitoring import Monitor
from aetheros_integrations.scheduler import Scheduler
from aetheros_integrations.sync import SyncEngine
from aetheros_integrations.webhooks import WebhookEngine
from aetheros_integrations.workflow import WorkflowEngine

logger = logging.getLogger(__name__)

__version__ = "1.0.0"

_PLATFORM = None
_PLATFORM_LOCK = object()


class IntegrationPlatform:
    """Top-level facade bundling every integration subsystem."""

    def __init__(self, settings=None, dirpath=None):
        self._settings = settings or load_integrations_settings()
        self._dir = dirpath or get_aetheros_dir(self._settings.data_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self.security = security
        self.manager = IntegrationManager(self._settings, dirpath=self._dir)
        self.auth_engine = self.manager._auth
        self.event_bus = EventBus(dirpath=self._dir)
        self.webhooks = WebhookEngine(self._settings, audit=self.manager._audit, dirpath=self._dir)
        self.monitor = Monitor(dirpath=self._dir, settings=self._settings)
        self.scheduler = Scheduler(event_bus=self.event_bus, audit=self.manager._audit, dirpath=self._dir, executor=self._default_job_executor)
        self.sync = SyncEngine(dirpath=self._dir, settings=self._settings)
        self.workflow_engine = WorkflowEngine(
            self.manager,
            event_bus=self.event_bus,
            monitor=self.monitor,
            audit=self.manager._audit,
            dirpath=self._dir,
        )

    # -- convenience ------------------------------------------------------

    @property
    def vault(self):
        return self.manager._vault

    @property
    def audit(self):
        return self.manager._audit

    @property
    def permissions(self):
        return self.manager._perms

    def install_provider(self, provider_key: str, credential_id: str = "", label: str = "", config: Optional[Dict[str, Any]] = None):
        return self.manager.install(provider_key, label=label, config=config, credential_id=credential_id)

    def get_provider(self, integration_id: str):
        return self.manager.get_provider(integration_id)

    # -- scheduler wiring -------------------------------------------------

    def _default_job_executor(self, job):
        """Default scheduler executor: dispatch to a workflow by action name or
        call a provider action on the referenced integration."""
        from aetheros_integrations.models import ScheduledJob

        if job.action.startswith("workflow:"):
            wf_id = job.action.split(":", 1)[1]
            return self.workflow_engine.trigger(wf_id, job.params)
        if job.integration_id:
            provider = self.manager.get_provider(job.integration_id)
            method = getattr(provider, job.action, None)
            if method is None:
                raise NotImplementedError(f"No action {job.action}")
            return method(**job.params)
        raise NotImplementedError(f"No executor for action {job.action}")

    # -- webhook → workflow bridge ----------------------------------------

    def on_webhook(self, url: str, workflow_id: str, *, secret: str = ""):
        """Register a workflow to be triggered by an outgoing webhook delivery."""
        def handler(payload, delivery):
            self.workflow_engine.trigger(workflow_id, {"_webhook": payload, "_webhook_delivery": delivery.to_dict()})

        self.webhooks.register_handler(handler)
        return handler

    # -- lifecycle --------------------------------------------------------

    def status(self) -> Dict[str, Any]:
        return {
            "version": __version__,
            "providers": self.manager.list_providers(),
            "installed_integrations": self.manager.count(),
            "webhook_stats": self.webhooks.stats(),
            "event_stats": self.event_bus.stats(),
            "scheduled_jobs": len(self.scheduler.list()),
            "monitor_summary": self.monitor.summary(),
        }

    def start(self) -> None:
        self.scheduler.start()

    def stop(self) -> None:
        self.scheduler.stop()
        self.workflow_engine.close()
        self.manager.close()

    def close(self) -> None:
        self.stop()


def get_platform(settings=None, dirpath=None) -> IntegrationPlatform:
    global _PLATFORM
    if _PLATFORM is None:
        _PLATFORM = IntegrationPlatform(settings, dirpath)
    return _PLATFORM


def reset_platform() -> None:
    global _PLATFORM
    _PLATFORM = None
