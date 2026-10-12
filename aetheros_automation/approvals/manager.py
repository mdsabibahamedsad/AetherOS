from __future__ import annotations

import asyncio
import json
import logging
import os
import time
import uuid
from typing import Any

from aetheros_automation.models.models import ApprovalRequest

logger = logging.getLogger(__name__)

_APPROVALS_DIR = os.path.expanduser("~/.aetheros/automation/approvals")


class ApprovalManager:
    """Manage human-in-the-loop approval lifecycle for risky automation actions.

    In-flight approvals live in memory and are persisted to
    ``~/.aetheros/automation/approvals/`` as JSON files so that
    they survive engine restarts.
    """

    _RISKY_ACTIONS: list[str] = [
        "delete_file",
        "format_disk",
        "send_email",
        "payment",
        "publish_code",
        "deploy",
        "shutdown",
        "install_software",
        "run_privileged",
    ]

    def __init__(self) -> None:
        os.makedirs(_APPROVALS_DIR, exist_ok=True)
        self._pending: dict[str, ApprovalRequest] = {}
        self._history: list[ApprovalRequest] = []
        self._loaded = False

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------

    async def request_approval(
        self,
        task_id: str,
        action: str,
        description: str,
        details: dict[str, Any] | None = None,
    ) -> ApprovalRequest:
        """Create a new pending approval request and return it."""
        now = time.time()
        request = ApprovalRequest(
            id=uuid.uuid4().hex[:12],
            task_id=task_id,
            action=action,
            description=description,
            details=details or {},
            status="pending",
            created_at=now,
        )
        self._pending[request.id] = request
        await self._persist(request)
        logger.info(
            "Approval requested  id=%s  task=%s  action=%s",
            request.id,
            task_id,
            action,
        )
        return request

    async def respond(
        self,
        approval_id: str,
        approved: bool,
        reason: str = "",
    ) -> bool:
        """Respond to a pending approval request.

        Returns ``True`` if the request was found and resolved, ``False``
        if the request does not exist or has already been answered.
        """
        request = self._pending.pop(approval_id, None)
        if request is None:
            logger.warning("respond: unknown or already-resolved approval %s", approval_id)
            return False

        request.status = "approved" if approved else "denied"
        request.responded_at = time.time()
        request.response = reason or ("approved" if approved else "denied")

        self._history.append(request)
        await self._persist(request)
        logger.info(
            "Approval %s  id=%s  task=%s  action=%s",
            request.status,
            approval_id,
            request.task_id,
            request.action,
        )
        return True

    async def get_pending(self) -> list[ApprovalRequest]:
        """Return every unresolved approval request."""
        await self._ensure_loaded()
        return list(self._pending.values())

    async def get_history(self) -> list[ApprovalRequest]:
        """Return every resolved approval request (most recent first)."""
        await self._ensure_loaded()
        return sorted(self._history, key=lambda r: r.responded_at or r.created_at, reverse=True)

    @staticmethod
    def requires_approval(action: str, details: dict[str, Any] | None = None) -> bool:
        """Decide whether *action* is classified as risky.

        Subclasses may override this to add context-sensitive heuristics.
        """
        _ = details
        return action in ApprovalManager._RISKY_ACTIONS

    async def auto_approve_if_safe(self, action: str, context: dict[str, Any]) -> bool:
        """Auto-approve *action* when it is clearly low-risk.

        Returns ``True`` if the action was auto-approved (callers can skip
        ``request_approval``), ``False`` if it still needs human review.
        """
        if action not in self._RISKY_ACTIONS:
            return True

        safe_destinations = {"/tmp", "/private/tmp", os.path.expanduser("~/Downloads")}

        if action == "delete_file":
            path = context.get("path", "")
            parent = os.path.dirname(os.path.abspath(path)) if path else ""
            if parent in safe_destinations or parent.startswith(
                os.path.expanduser("~/.aetheros")
            ):
                return True

        if action == "send_email":
            to = context.get("to", [])
            internal_domains = context.get("internal_domains", [])
            if internal_domains and all(
                any(domain in addr for domain in internal_domains) for addr in to
            ):
                return True

        return False

    # ------------------------------------------------------------------
    # persistence
    # ------------------------------------------------------------------

    async def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        self._loaded = True
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._load_all)

    def _load_all(self) -> None:
        if not os.path.isdir(_APPROVALS_DIR):
            return
        for name in os.listdir(_APPROVALS_DIR):
            if not name.endswith(".json"):
                continue
            path = os.path.join(_APPROVALS_DIR, name)
            try:
                with open(path, encoding="utf-8") as fh:
                    data = json.load(fh)
                request = ApprovalRequest(
                    id=data["id"],
                    task_id=data.get("task_id", ""),
                    action=data.get("action", ""),
                    description=data.get("description", ""),
                    details=data.get("details", {}),
                    status=data.get("status", "pending"),
                    created_at=data.get("created_at", 0.0),
                    responded_at=data.get("responded_at", 0.0),
                    response=data.get("response", ""),
                    responded_by=data.get("responded_by", ""),
                )
                if request.status == "pending":
                    self._pending[request.id] = request
                else:
                    self._history.append(request)
            except Exception:
                logger.exception("Failed to load approval %s", path)

    async def _persist(self, request: ApprovalRequest) -> None:
        path = os.path.join(_APPROVALS_DIR, f"{request.id}.json")
        data = {
            "id": request.id,
            "task_id": request.task_id,
            "action": request.action,
            "description": request.description,
            "details": request.details,
            "status": request.status,
            "created_at": request.created_at,
            "responded_at": request.responded_at,
            "response": request.response,
            "responded_by": request.responded_by,
        }
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _write_json, path, data)


def _write_json(path: str, data: dict[str, Any]) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, default=str)
