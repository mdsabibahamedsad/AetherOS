from __future__ import annotations

import time
from typing import Any


class ConsentManager:
    def __init__(self):
        self._consented: dict[str, float] = {}
        self._pending: list[dict] = []
        self._history_delete_consent = False

    def request(self, action: str, description: str = "") -> bool:
        self._pending.append({"action": action, "description": description, "timestamp": time.time()})
        return True

    def grant(self, action: str):
        self._consented[action] = time.time()
        self._pending = [p for p in self._pending if p["action"] != action]

    def revoke(self, action: str):
        self._consented.pop(action, None)

    def is_granted(self, action: str) -> bool:
        return action in self._consented

    def grant_history_delete(self):
        self._history_delete_consent = True

    def revoke_history_delete(self):
        self._history_delete_consent = False

    def can_delete_history(self) -> bool:
        return self._history_delete_consent

    @property
    def pending_requests(self) -> list[dict]:
        return list(self._pending)

    def reset(self):
        self._consented.clear()
        self._pending.clear()
