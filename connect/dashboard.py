"""Connect Hub dashboard — status overview, health summary, recommendations."""

from __future__ import annotations

from typing import Optional

from connect.store import ConnectStore
from connect.registry import (SERVICE_REGISTRY, get_services_by_category,
                               get_categories, get_all_services)
from connect.models import ServiceCategory


class ConnectDashboard:
    def __init__(self, store: Optional[ConnectStore] = None):
        self.store = store or ConnectStore()

    def get_overview(self) -> dict:
        stats = self.store.get_stats()
        categories = get_categories()
        connections = self.store.list_connections()
        connected = [c for c in connections if c.get("status") == "connected"]
        return {
            "total_services": len(SERVICE_REGISTRY),
            "total_categories": len(categories),
            "connected": stats["connected"],
            "disconnected": stats["disconnected"],
            "connection_health": self._get_health_summary(connections),
            "categories": categories,
            "recent_activity": self.store.get_activity(limit=10),
        }

    def get_category_status(self, category: ServiceCategory) -> dict:
        services = get_services_by_category(category)
        connections = self.store.list_connections(category=category.value)
        connected_ids = {c["service_id"] for c in connections
                         if c.get("status") == "connected"}
        return {
            "category": category.value,
            "category_name": category.value.replace("_", " ").title(),
            "total_services": len(services),
            "connected": len(connected_ids),
            "available": [{"id": s.id, "name": s.name, "connected": s.id in connected_ids,
                            "icon": s.icon, "official": s.official}
                           for s in services],
            "connections": connections,
        }

    def get_recommendations(self) -> list[dict]:
        connections = self.store.list_connections()
        connected_ids = {c["service_id"] for c in connections}
        available = [s for s in get_all_services()
                     if not s.auto_discoverable and s.id not in connected_ids]
        from connect.registry import get_services_by_category

        recs = []
        priority_cats = [ServiceCategory.COMMUNICATION, ServiceCategory.EMAIL,
                         ServiceCategory.DEVELOPMENT, ServiceCategory.PRODUCTIVITY,
                         ServiceCategory.CLOUD_STORAGE]
        for cat in priority_cats:
            cat_services = get_services_by_category(cat)
            for s in cat_services[:2]:
                if s.id not in connected_ids:
                    recs.append({
                        "service_id": s.id,
                        "name": s.name,
                        "description": s.description,
                        "category": s.category.value,
                        "icon": s.icon,
                        "official": s.official,
                    })
        return recs[:8]

    def search_services(self, query: str, category: str = None) -> list[dict]:
        from connect.registry import search_services
        services = search_services(query, category)
        connections = self.store.list_connections()
        connected_ids = {c["service_id"]: c for c in connections}
        results = []
        for s in services:
            conn = connected_ids.get(s.id)
            results.append({
                "id": s.id, "name": s.name, "description": s.description,
                "category": s.category.value, "icon": s.icon,
                "official": s.official, "connected": conn is not None,
                "connection_id": conn["id"] if conn else None,
                "status": conn.get("status") if conn else "disconnected",
            })
        return results

    def _get_health_summary(self, connections: list[dict]) -> dict:
        total = len(connections)
        healthy = sum(1 for c in connections if c.get("status") == "connected")
        warning = sum(1 for c in connections if c.get("status") == "expired")
        error = sum(1 for c in connections if c.get("status") == "error")
        return {"total": total, "healthy": healthy,
                "warning": warning, "error": error}

    def render(self) -> str:
        """Return a formatted dashboard string for CLI display."""
        overview = self.get_overview()
        lines = []
        lines.append("╔══════════════════════════════════════╗")
        lines.append("║      AetherOS Connect Hub           ║")
        lines.append("╠══════════════════════════════════════╣")
        lines.append(f"║ Connected:    {overview['connected']:<4}                     ║")
        lines.append(f"║ Disconnected: {overview['disconnected']:<4}                     ║")
        lines.append(f"║ Services:     {overview['total_services']:<4}                     ║")
        lines.append("╠══════════════════════════════════════╣")
        for cat in overview["categories"]:
            status = self.get_category_status(
                ServiceCategory(cat["id"]))
            lines.append(f"║ {cat['name']:<25} {status['connected']}/{status['total_services']:<4} ║")
        lines.append("╚══════════════════════════════════════╝")
        return "\n".join(lines)
