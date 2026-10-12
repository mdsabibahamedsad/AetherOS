"""Activity log — track all connection events with search and filtering."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from connect.store import ConnectStore


class ActivityLog:
    def __init__(self, store: Optional[ConnectStore] = None):
        self.store = store or ConnectStore()

    def get_all(self, limit: int = 100) -> list[dict]:
        return self.store.get_activity(limit=limit)

    def get_for_connection(self, connection_id: str, limit: int = 50) -> list[dict]:
        return self.store.get_activity(connection_id=connection_id, limit=limit)

    def search(self, query: str = "", action: str = None,
                status: str = None, limit: int = 100) -> list[dict]:
        entries = self.store.get_activity(limit=1000)
        results = []
        q = query.lower()
        for e in entries:
            if action and e.get("action") != action:
                continue
            if status and e.get("status") != status:
                continue
            if query and q not in e.get("message", "").lower() \
                    and q not in e.get("service_name", "").lower():
                continue
            results.append(e)
        return results[:limit]

    def get_summary(self) -> dict:
        entries = self.store.get_activity(limit=500)
        summary = {
            "total": len(entries),
            "by_action": {},
            "by_status": {},
            "recent": entries[:10] if entries else [],
        }
        for e in entries:
            action = e.get("action", "unknown")
            status = e.get("status", "unknown")
            summary["by_action"][action] = summary["by_action"].get(action, 0) + 1
            summary["by_status"][status] = summary["by_status"].get(status, 0) + 1
        return summary
