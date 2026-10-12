"""CLI command handlers — aetheros connect <subcommand> for managing connections."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from typing import Optional

logger = logging.getLogger(__name__)


def build_connect_parser(subparsers) -> None:
    p = subparsers.add_parser("connect", help="Connect Hub — manage service connections")
    subs = p.add_subparsers(dest="connect_command")

    subs.add_parser("dashboard", help="Show connection dashboard")
    subs.add_parser("list", help="List all connections")
    subs.add_parser("services", help="List all available services")
    subs.add_parser("categories", help="List service categories")
    subs.add_parser("discover", help="Auto-discover local services")

    p_search = subs.add_parser("search", help="Search services")
    p_search.add_argument("query", help="Search query")
    p_search.add_argument("--category", "-c", default="", help="Filter by category")

    p_add = subs.add_parser("add", help="Connect a new service")
    p_add.add_argument("service_id", help="Service ID to connect")
    p_add.add_argument("--label", default="", help="Display label")
    p_add.add_argument("--config", default="", help="Config JSON")
    p_add.add_argument("--key", default="", help="API key or token")

    p_remove = subs.add_parser("remove", help="Remove a connection")
    p_remove.add_argument("connection_id", help="Connection ID")

    p_health = subs.add_parser("health", help="Check connection health")
    p_health.add_argument("connection_id", nargs="?", default="", help="Connection ID")
    p_health.add_argument("--all", action="store_true", help="Check all")

    p_logs = subs.add_parser("logs", help="Show activity logs")
    p_logs.add_argument("--connection", default="", help="Connection ID")
    p_logs.add_argument("--limit", type=int, default=20)

    p_sync = subs.add_parser("sync", help="Sync a connection")
    p_sync.add_argument("connection_id", nargs="?", default="", help="Connection ID")
    p_sync.add_argument("--all", action="store_true", help="Sync all")
    p_sync.add_argument("--category", default="", help="Sync category")

    p_info = subs.add_parser("info", help="Show connection details")
    p_info.add_argument("connection_id", help="Connection ID")
    p_info.add_argument("--json", action="store_true", help="JSON output")

    p_reconnect = subs.add_parser("reconnect", help="Reconnect a service")
    p_reconnect.add_argument("connection_id", help="Connection ID")

    p_config = subs.add_parser("config", help="Update connection config")
    p_config.add_argument("connection_id", help="Connection ID")
    p_config.add_argument("--set", default="", help="Config JSON")
    p_config.add_argument("--key", default="", help="Update API key")

    subs.add_parser("stats", help="Show connection statistics")


def handle_connect_command(args: argparse.Namespace, **kwargs) -> None:
    cmd = args.connect_command
    if not cmd:
        show_connect_help()
        return

    handlers = {
        "dashboard": _cmd_dashboard,
        "list": _cmd_list,
        "services": _cmd_services,
        "categories": _cmd_categories,
        "discover": _cmd_discover,
        "search": _cmd_search,
        "add": _cmd_add,
        "remove": _cmd_remove,
        "health": _cmd_health,
        "logs": _cmd_logs,
        "sync": _cmd_sync,
        "info": _cmd_info,
        "reconnect": _cmd_reconnect,
        "config": _cmd_config,
        "stats": _cmd_stats,
    }
    handler = handlers.get(cmd)
    if handler:
        handler(args)


def _get_store():
    from connect.store import ConnectStore
    return ConnectStore()


def _cmd_dashboard(args):
    from connect.dashboard import ConnectDashboard
    dash = ConnectDashboard(_get_store())
    print(dash.render())


def _cmd_list(args):
    store = _get_store()
    connections = store.list_connections()
    from rich.console import Console
    from rich.table import Table
    console = Console()
    if not connections:
        console.print("[yellow]No connections yet. Use 'aetheros connect add <service_id>'[/yellow]")
        return
    table = Table("ID", "Service", "Category", "Status")
    for c in connections:
        cat = c.get("category", "").replace("_", " ").title()
        status = c.get("status", "?")
        table.add_row(c["id"][:16] + "...", c.get("service_name", c["id"])[:20],
                      cat[:20], status)
    console.print(table)


def _cmd_services(args):
    from connect.registry import get_all_services, get_categories
    from rich.console import Console
    from rich.table import Table
    console = Console()
    for cat in get_categories():
        table = Table(f"{cat['name']} ({cat['count']})", "ID", "Auth", "Sync")
        for s in get_all_services():
            if s.category.value == cat["id"]:
                table.add_row(s.name, s.id, s.auth_type,
                              "Yes" if s.supports_sync else "No")
        console.print(table)
        console.print()


def _cmd_categories(args):
    from connect.registry import get_categories
    for cat in get_categories():
        print(f"  {cat['id']:<30} {cat['name']:<25} {cat['count']} services")


def _cmd_discover(args):
    async def _run():
        from connect.discovery import DiscoveryService
        d = DiscoveryService(_get_store())
        results = await d.discover_all()
        discovered = [r for r in results if r.detected]
        if discovered:
            print(f"  Discovered {len(discovered)} services:")
            for r in discovered:
                print(f"    ✅ {r.service_name:<20} {r.version or r.status}")
        else:
            print("  No local services discovered")
    asyncio.run(_run())


def _cmd_search(args):
    from connect.dashboard import ConnectDashboard
    results = ConnectDashboard(_get_store()).search_services(
        args.query, args.category or None)
    if not results:
        print(f"  No services found for '{args.query}'")
        return
    for r in results:
        status = "✅" if r["connected"] else "○"
        print(f"  {status} {r['name']:<25} {r['category']:<20} {r['id']}")


def _cmd_add(args):
    async def _run():
        from connect.models import ServiceConnection, ConnectionStatus, SyncMode, ServiceCategory
        from connect.registry import get_service
        from connect.connectors.communication import CONNECTOR_MAP as comm_map
        from connect.connectors.email import CONNECTOR_MAP as email_map
        from connect.connectors.development import CONNECTOR_MAP as dev_map
        from connect.connectors.productivity import CONNECTOR_MAP as prod_map
        from connect.connectors.ai_providers import CONNECTOR_MAP as ai_map
        from uuid import uuid4

        service = get_service(args.service_id)
        if not service:
            print(f"  Service not found: {args.service_id}")
            return

        conn_id = str(uuid4())[:12]
        config = {}
        if args.config:
            try:
                config = json.loads(args.config)
            except json.JSONDecodeError:
                pass

        conn = ServiceConnection(
            id=conn_id, service_id=args.service_id,
            service_name=service.name, category=service.category,
            status=ConnectionStatus.CONNECTING, label=args.label or service.name,
            config=config, sync_mode=SyncMode.MANUAL,
        )

        store = _get_store()
        store.save_connection(conn)

        all_maps = {**comm_map, **email_map, **dev_map, **prod_map, **ai_map}
        connector_cls = all_maps.get(args.service_id)

        credentials = {}
        if args.key:
            credentials["api_key"] = args.key
            credentials["token"] = args.key

        if connector_cls:
            connector = connector_cls(store)
            result = await connector.connect(conn, credentials)
            if result.success:
                store.set_status(conn_id, "connected")
                store.save_connection(conn)
                if credentials:
                    from connect.auth import CredentialManager
                    CredentialManager(store).save_credentials(
                        conn_id, args.service_id, credentials)
                print(f"  ✅ Connected to {service.name}: {result.message}")
            else:
                store.set_status(conn_id, result.status.value, result.error)
                store.save_connection(conn)
                print(f"  ❌ Failed: {result.error}")
        else:
            store.set_status(conn_id, "connected")
            print(f"  ✅ Registered {service.name} (no connector)")

    asyncio.run(_run())


def _cmd_remove(args):
    store = _get_store()
    conn = store.get_connection(args.connection_id)
    if not conn:
        print(f"  Connection not found: {args.connection_id}")
        return
    name = conn.get("service_name", conn["id"])
    from connect.auth import CredentialManager
    CredentialManager(store).delete_credentials(args.connection_id)
    store.delete_connection(args.connection_id)
    print(f"  Removed: {name}")


def _cmd_health(args):
    async def _run():
        from connect.health import HealthMonitor
        hm = HealthMonitor(_get_store())
        if args.all:
            results = await hm.check_all()
            for r in results:
                icon = "✅" if r.status.value == "connected" else "❌"
                print(f"  {icon} {r.service_id:<20} {r.status.value:<15} {r.latency_ms:.0f}ms")
        elif args.connection_id:
            conn = _get_store().get_connection(args.connection_id)
            if conn:
                result = await hm.check_connection(conn)
                print(f"  Status: {result.status.value}")
                print(f"  API Available: {result.api_available}")
                print(f"  Auth Valid: {result.auth_valid}")
                print(f"  Latency: {result.latency_ms:.0f}ms")
                if result.last_error:
                    print(f"  Error: {result.last_error}")
            else:
                print(f"  Connection not found: {args.connection_id}")
        else:
            summary = hm.get_summary()
            for s in summary:
                icon = "✅" if s["status"] == "connected" else "❌"
                print(f"  {icon} {s['service_name']:<25} {s['status']:<12} {s['latency_ms']:.0f}ms")
    asyncio.run(_run())


def _cmd_logs(args):
    store = _get_store()
    if args.connection:
        logs = store.get_activity(connection_id=args.connection, limit=args.limit)
    else:
        logs = store.get_activity(limit=args.limit)
    for entry in logs:
        ts = entry.get("timestamp", "")[:19] if entry.get("timestamp") else ""
        action = entry.get("action", "").ljust(20)
        msg = entry.get("message", "")
        print(f"  {ts} [{action}] {msg}")


def _cmd_sync(args):
    async def _run():
        from connect.sync import SyncEngine
        se = SyncEngine(_get_store())
        if args.all:
            results = await se.sync_all()
            print(f"  Synced {len(results)} connections")
        elif args.category:
            results = await se.sync_category(args.category)
            print(f"  Synced {len(results)} connections in {args.category}")
        elif args.connection_id:
            conn = _get_store().get_connection(args.connection_id)
            if conn:
                result = await se.sync_connection(conn)
                if result.get("success"):
                    print(f"  ✅ Synced: {result.get('message', '')}")
                else:
                    print(f"  ❌ {result.get('error', 'Sync failed')}")
            else:
                print(f"  Connection not found: {args.connection_id}")
        else:
            print("  Specify --connection, --all, or --category")
    asyncio.run(_run())


def _cmd_info(args):
    conn = _get_store().get_connection(args.connection_id)
    if not conn:
        print(f"  Connection not found: {args.connection_id}")
        return
    if args.json:
        print(json.dumps(conn, indent=2))
        return
    print(f"  Service: {conn.get('service_name', '?')} ({conn.get('service_id', '?')})")
    print(f"  Status: {conn.get('status', '?')}")
    print(f"  Label: {conn.get('label', '')}")
    print(f"  Category: {conn.get('category', '?')}")
    print(f"  Connected: {conn.get('connected_at', 'never')}")
    print(f"  Last Sync: {conn.get('last_sync', 'never')}")
    print(f"  Sync Mode: {conn.get('sync_mode', 'manual')}")
    if conn.get("error_message"):
        print(f"  Error: {conn.get('error_message')}")
    from connect.auth import CredentialManager
    creds = CredentialManager(_get_store()).get_key_hint(args.connection_id)
    if creds:
        print(f"  Credentials: {creds}")


def _cmd_reconnect(args):
    async def _run():
        store = _get_store()
        conn = store.get_connection(args.connection_id)
        if not conn:
            print(f"  Connection not found: {args.connection_id}")
            return
        from connect.connectors.communication import CONNECTOR_MAP as cm
        from connect.connectors.email import CONNECTOR_MAP as em
        from connect.connectors.development import CONNECTOR_MAP as dm
        from connect.connectors.productivity import CONNECTOR_MAP as pm
        from connect.connectors.ai_providers import CONNECTOR_MAP as am
        all_maps = {**cm, **em, **dm, **pm, **am}
        cls = all_maps.get(conn.get("service_id", ""))
        if cls:
            connector = cls(store)
            from connect.auth import CredentialManager
            creds = CredentialManager(store).get_credentials(args.connection_id)
            from connect.models import ServiceConnection, ConnectionStatus, SyncMode, ServiceCategory
            sc = ServiceConnection(
                id=conn["id"], service_id=conn.get("service_id", ""),
                service_name=conn.get("service_name", ""),
                category=ServiceCategory(conn.get("category", "local")),
                status=ConnectionStatus(conn.get("status", "disconnected")),
                config=conn.get("config", {}),
                sync_mode=SyncMode(conn.get("sync_mode", "manual")),
            )
            result = await connector.connect(sc, creds or {})
            if result.success:
                store.set_status(args.connection_id, "connected")
                print(f"  ✅ Reconnected: {conn.get('service_name', '')}")
            else:
                store.set_status(args.connection_id, result.status.value, result.error)
                print(f"  ❌ {result.error}")
        else:
            store.set_status(args.connection_id, "connected")
            print(f"  Reconnected: {conn.get('service_name', '')}")
    asyncio.run(_run())


def _cmd_config(args):
    store = _get_store()
    conn = store.get_connection(args.connection_id)
    if not conn:
        print(f"  Connection not found: {args.connection_id}")
        return
    from connect.models import ServiceConnection, ConnectionStatus, SyncMode, ServiceCategory
    config = dict(conn.get("config", {}))
    if args.set:
        try:
            new_config = json.loads(args.set)
            config.update(new_config)
        except json.JSONDecodeError:
            print("  Invalid JSON config")
            return
    if args.key:
        from connect.auth import CredentialManager
        CredentialManager(store).save_credentials(
            args.connection_id, conn.get("service_id", ""),
            {"api_key": args.key, "token": args.key})
    from connect.models import ServiceConnection
    sc = ServiceConnection(
        id=conn["id"], service_id=conn.get("service_id", ""),
        service_name=conn.get("service_name", ""),
        category=ServiceCategory(conn.get("category", "local")),
        status=ConnectionStatus(conn.get("status", "disconnected")),
        config=config, sync_mode=SyncMode(conn.get("sync_mode", "manual")),
    )
    store.save_connection(sc)
    print(f"  Config updated")


def _cmd_stats(args):
    store = _get_store()
    stats = store.get_stats()
    print(f"  Total connections: {stats['total']}")
    print(f"  Connected: {stats['connected']}")
    print(f"  Disconnected: {stats['disconnected']}")
    print(f"\n  By Category:")
    for cat, count in stats.get("by_category", {}).items():
        print(f"    {cat.replace('_', ' ').title():<25} {count}")


def show_connect_help():
    print("Usage: aetheros connect <command> [options]")
    print("\nCommands:")
    for cmd, desc in [
        ("dashboard", "Show connection dashboard"),
        ("list", "List all connections"),
        ("services", "List available services"),
        ("categories", "List service categories"),
        ("discover", "Auto-discover local services"),
        ("search <query>", "Search services"),
        ("add <service_id>", "Connect a new service"),
        ("remove <connection_id>", "Remove a connection"),
        ("health [id]", "Check connection health"),
        ("logs", "Show activity logs"),
        ("sync [id]", "Sync a connection"),
        ("info <id>", "Show connection details"),
        ("reconnect <id>", "Reconnect a service"),
        ("config <id>", "Update connection config"),
        ("stats", "Show statistics"),
    ]:
        print(f"  {cmd:<22} {desc}")
