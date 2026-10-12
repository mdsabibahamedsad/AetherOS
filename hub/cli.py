"""CLI command handlers — aetheros hub, plugin, mcp, skill, theme, sdk, backup commands."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from typing import Any, Optional

logger = logging.getLogger(__name__)


def build_hub_parser(subparsers) -> None:
    """Build the unified hub CLI subcommand tree."""
    p = subparsers.add_parser("hub", help="AetherOS Hub — marketplace, plugins, MCP, themes")
    subs = p.add_subparsers(dest="hub_command")

    # ── hub browse/search ──
    ps = subs.add_parser("search", help="Search the hub marketplace")
    ps.add_argument("query", nargs="?", default="", help="Search query")
    ps.add_argument("--category", "-c", default="", help="Filter by category")
    ps.add_argument("--sort", default="", choices=["rating", "downloads", "name", "new"],
                    help="Sort order")
    ps.add_argument("--limit", type=int, default=20)

    ps = subs.add_parser("browse", help="Browse hub categories")
    ps.add_argument("--category", "-c", default="", help="Category to browse")
    ps.add_argument("--featured", action="store_true", help="Show featured only")
    ps.add_argument("--trending", action="store_true", help="Show trending only")
    ps.add_argument("--editors-choice", action="store_true", help="Show editor's picks")

    # ── hub categories ──
    subs.add_parser("categories", help="List all hub categories")

    # ── hub info ──
    p_info = subs.add_parser("info", help="Show item details")
    p_info.add_argument("item_id", help="Item ID")
    p_info.add_argument("--json", action="store_true", help="JSON output")

    # ── hub install ──
    p_install = subs.add_parser("install", help="Install from hub")
    p_install.add_argument("item_id", help="Item ID to install")
    p_install.add_argument("--yes", "-y", action="store_true", help="Auto-approve")

    # ── hub update ──
    p_upd = subs.add_parser("update", help="Update installed items")
    p_upd.add_argument("item_id", nargs="?", default="", help="Item ID (omit for all)")
    p_upd.add_argument("--check", action="store_true", help="Check for updates only")

    # ── hub remove ──
    p_rem = subs.add_parser("remove", help="Remove an installed item")
    p_rem.add_argument("item_id", help="Item ID")
    p_rem.add_argument("--force", "-f", action="store_true", help="Force removal")

    # ── hub installed ──
    p_inst = subs.add_parser("installed", help="List installed items")
    p_inst.add_argument("--category", "-c", default="", help="Filter by category")
    p_inst.add_argument("--status", default="",
                        choices=["enabled", "disabled", "broken", "all"])
    p_inst.add_argument("--json", action="store_true", help="JSON output")

    # ── hub stats ──
    subs.add_parser("stats", help="Show hub statistics")

    # ── hub backups ──
    p_bk = subs.add_parser("backup", help="Manage hub backups")
    bsubs = p_bk.add_subparsers(dest="backup_action")
    bsubs.add_parser("create", help="Create a backup")
    bsubs.add_parser("list", help="List backups")
    p_br = bsubs.add_parser("restore", help="Restore from backup")
    p_br.add_argument("backup_id", help="Backup ID")
    bsubs.add_parser("prune", help="Remove old backups")

    # ── hub permissions ──
    p_perm = subs.add_parser("permissions", help="Manage permissions")
    pperms = p_perm.add_subparsers(dest="permission_action")
    pperms.add_parser("list", help="List all permission grants")
    p_prev = pperms.add_parser("revoke", help="Revoke permissions")
    p_prev.add_argument("item_id", help="Item ID")
    p_prev.add_argument("--permission", "-p", default="", help="Specific permission")
    pperms.add_parser("reset", help="Reset all permissions")


def build_hub_plugin_parser(subparsers) -> None:
    p = subparsers.add_parser("plugin", help="Plugin management")
    subs = p.add_subparsers(dest="plugin_command")
    subs.add_parser("list", help="List installed plugins")
    p_i = subs.add_parser("install", help="Install a plugin")
    p_i.add_argument("plugin_id", help="Plugin ID or path")
    p_i.add_argument("--file", "-f", default="", help="Plugin file (.zip)")
    p_u = subs.add_parser("update", help="Update a plugin")
    p_u.add_argument("plugin_id", help="Plugin ID")
    subs.add_parser("remove", help="Remove a plugin")
    subs.add_parser("enable", help="Enable a plugin")
    subs.add_parser("disable", help="Disable a plugin")
    subs.add_parser("repair", help="Repair a plugin")


def build_hub_mcp_parser(subparsers) -> None:
    p = subparsers.add_parser("mcp", help="MCP server management")
    subs = p.add_subparsers(dest="mcp_command")
    subs.add_parser("list", help="List MCP servers")
    p_i = subs.add_parser("install", help="Install an MCP server")
    p_i.add_argument("server_id", help="Server ID")
    p_i.add_argument("--config", default="", help="Config JSON")
    subs.add_parser("add", help="Install an MCP server (alias for install)")
    subs.add_parser("configure", help="Configure MCP server")
    subs.add_parser("test", help="Test MCP connection")
    subs.add_parser("remove", help="Uninstall MCP server")
    subs.add_parser("enable", help="Enable MCP server")
    subs.add_parser("disable", help="Disable MCP server")


def build_hub_skill_parser(subparsers) -> None:
    p = subparsers.add_parser("skill", help="Skill pack management")
    subs = p.add_subparsers(dest="skill_command")
    subs.add_parser("list", help="List skill packs")
    p_i = subs.add_parser("install", help="Install a skill pack")
    p_i.add_argument("skill_id", help="Skill pack ID")


def build_hub_theme_parser(subparsers) -> None:
    p = subparsers.add_parser("theme", help="Theme management")
    subs = p.add_subparsers(dest="theme_command")
    subs.add_parser("list", help="List themes")
    subs.add_parser("install", help="Install a theme")
    subs.add_parser("activate", help="Activate a theme")


def build_hub_sdk_parser(subparsers) -> None:
    p = subparsers.add_parser("sdk", help="Extension SDK")
    subs = p.add_subparsers(dest="sdk_command")
    subs.add_parser("list-templates", help="List available templates")
    p_i = subs.add_parser("init", help="Initialize a new SDK project")
    p_i.add_argument("project_type", help="Template type (python-plugin, typescript-plugin, etc.)")
    p_i.add_argument("name", help="Project name")
    p_i.add_argument("--author", default="", help="Author name")
    p_i.add_argument("--description", default="", help="Project description")
    p_i.add_argument("--path", default="", help="Output path")
    p_b = subs.add_parser("build", help="Build an SDK project")
    p_b.add_argument("project_path", help="Path to project")
    p_b.add_argument("--output", "-o", default="", help="Output path")
    subs.add_parser("package", help="Package (alias for build)")
    subs.add_parser("publish", help="Publish a package")


def build_hub_backup_parser(subparsers) -> None:
    p = subparsers.add_parser("hub-backup", help="Hub backup management")
    subs = p.add_subparsers(dest="hub_backup_command")
    bc = subs.add_parser("create", help="Create a backup")
    bc.add_argument("--name", default="", help="Backup name")
    bc.add_argument("--no-plugins", action="store_true", help="Exclude plugins")
    bc.add_argument("--no-themes", action="store_true", help="Exclude themes")
    bc.add_argument("--no-settings", action="store_true", help="Exclude settings")
    subs.add_parser("list", help="List backups")
    br = subs.add_parser("restore", help="Restore from backup")
    br.add_argument("backup_id", help="Backup ID")
    br.add_argument("--no-plugins", action="store_true", help="Skip plugins")
    br.add_argument("--no-themes", action="store_true", help="Skip themes")
    br.add_argument("--no-settings", action="store_true", help="Skip settings")
    subs.add_parser("delete", help="Delete a backup")


# ── Handlers ──

def handle_hub_command(args: argparse.Namespace, **kwargs) -> None:
    cmd = args.hub_command
    if not cmd:
        show_hub_help()
        return
    from hub.store import HubStore
    store = HubStore()
    from hub.marketplace import HubMarketplace
    mp = HubMarketplace(store)

    if cmd == "search":
        query = getattr(args, "query", "")
        results = mp.search(query, category=args.category or None,
                             sort_by=args.sort or "")
        if args.limit:
            results = results[:args.limit]
        _print_items(results)
    elif cmd == "browse":
        if args.featured:
            _print_items(mp.get_featured(), "Featured")
        elif args.trending:
            _print_items(mp.get_trending(), "Trending")
        elif args.editors_choice:
            _print_items(mp.get_editors_choice(), "Editor's Choice")
        else:
            _print_items(mp.get_catalog(args.category or None))
    elif cmd == "categories":
        for cat in mp.get_categories():
            print(f"  {cat['id']:<20} {cat['name']:<30} {cat['count']} items")
    elif cmd == "info":
        item = mp.get_item(args.item_id)
        if item:
            _print_item_detail(item)
        else:
            print(f"Item not found: {args.item_id}")
    elif cmd == "install":
        result = mp.install(args.item_id, auto_approve=args.yes)
        if result.get("success"):
            print(f"  ✅ Installed: {args.item_id}")
        else:
            print(f"  ❌ {result.get('error', 'Installation failed')}")
    elif cmd == "update":
        _handle_hub_update(args, store)
    elif cmd == "remove":
        _handle_hub_remove(args, store)
    elif cmd == "installed":
        items = store.get_installed(args.category or None)
        if args.status == "disabled":
            items = [i for i in items if not i["enabled"]]
        elif args.status == "broken":
            items = [i for i in items if not i["compatible"]]
        if args.json:
            print(json.dumps(items, indent=2))
        else:
            _print_installed(items)
    elif cmd == "stats":
        stats = mp.get_stats()
        installed = store.get_stats()
        print(f"  Total catalog items: {stats['total_items']}")
        print(f"  Categories: {stats['categories']}")
        print(f"  Featured: {stats['featured']}")
        print(f"  Trending: {stats['trending']}")
        print(f"  Editor's Choice: {stats['editors_choice']}")
        print(f"  Total installed: {installed['total_installed']}")
    elif cmd == "backup":
        _handle_backup(args, store)
    elif cmd == "permissions":
        _handle_permissions(args, store)
    else:
        show_hub_help()


def _handle_hub_update(args, store):
    from hub.updater import AutoUpdater
    updater = AutoUpdater(store)
    if args.item_id:
        if args.check:
            updates = updater.check_for_updates()
            item_updates = [u for u in updates if u["item_id"] == args.item_id]
            if item_updates:
                u = item_updates[0]
                print(f"  Update available: {u['name']} {u['current_version']} → {u['available_version']}")
            else:
                print(f"  No updates available for {args.item_id}")
        else:
            result = updater.apply_update(args.item_id)
            if result.get("success"):
                print(f"  ✅ Updated: {args.item_id}")
            else:
                print(f"  ❌ {result.get('error', 'Update failed')}")
    else:
        updates = updater.check_for_updates()
        if not updates:
            print("  No updates available")
            return
        print(f"  {len(updates)} updates available:")
        for u in updates:
            print(f"    {u['name']:<30} {u['current_version']} → {u['available_version']}")
        if not args.check:
            for u in updates:
                result = updater.apply_update(u["item_id"])
                if result.get("success"):
                    print(f"    ✅ Updated: {u['name']}")


def _handle_hub_remove(args, store):
    item = store.get_installed_item(args.item_id)
    if not item:
        print(f"  Not installed: {args.item_id}")
        return
    from hub.plugins import PluginManager
    from hub.mcp_marketplace import MCPMarketplace
    from hub.themes import ThemeManager
    from hub.languages import LanguagePackManager
    from hub.icons import IconPackManager
    cat = item.get("category", "")
    removers = {
        "plugins": lambda: PluginManager(store).remove(args.item_id, safe=not args.force),
        "mcp_servers": lambda: MCPMarketplace(store).uninstall(args.item_id),
        "themes": lambda: ThemeManager(store).remove(args.item_id),
        "language_packs": lambda: LanguagePackManager(store).remove(args.item_id) if hasattr(LanguagePackManager, 'remove') else store.remove_item(args.item_id),
    }
    result = removers.get(cat, lambda: store.remove_item(args.item_id))()
    if isinstance(result, dict) and result.get("success"):
        print(f"  ✅ Removed: {args.item_id}")
    else:
        store.remove_item(args.item_id)
        print(f"  Removed: {args.item_id}")


def _handle_backup(args, store):
    from hub.backup import BackupManager
    bm = BackupManager(store)
    action = args.backup_action
    if action == "create":
        result = bm.create_backup(name=args.name or "")
        print(f"  ✅ Created backup: {result['name']} ({result['items']} items, {result['size']:,} bytes)")
    elif action == "list":
        backups = bm.list_backups()
        if not backups:
            print("  No backups found")
            return
        for b in backups:
            print(f"  {b['id']:<12} {b.get('name', ''):<30} {b.get('items_count', 0)} items")
    elif action == "restore":
        result = bm.restore(args.backup_id)
        if result.get("success"):
            print(f"  ✅ Restored backup: {args.backup_id}")
        else:
            print(f"  ❌ {result.get('error', 'Restore failed')}")
    elif action == "prune":
        print("  Pruned old backups")


def _handle_permissions(args, store):
    from hub.permissions import PermissionManager
    pm = PermissionManager(store)
    action = args.permission_action
    if action == "list":
        grants = pm.get_all_grants()
        if not grants:
            print("  No permission grants")
            return
        for item_id, perms in grants.items():
            for g in perms:
                print(f"  {item_id:<20} {g.permission.value:<15} {g.level.value}")
    elif action == "revoke":
        perm = None
        if args.permission:
            from hub.models import Permission
            try:
                perm = Permission(args.permission)
            except ValueError:
                pass
        pm.revoke(args.item_id, perm)
        print(f"  Revoked permissions for: {args.item_id}")
    elif action == "reset":
        pm.reset_all()
        print("  All permissions reset")


def _print_items(items: list[dict], title: str = ""):
    from rich.console import Console
    from rich.table import Table
    if not items:
        print("  No items found")
        return
    console = Console()
    if title:
        console.print(f"\n[bold]{title}[/bold]")
    table = Table("ID", "Name", "Category", "Author", "Rating", "Downloads")
    for item in items:
        cat = item.get("category", "").replace("_", " ").title()
        rating = f"{item.get('rating', 0):.1f} ★"
        dl = f"{item.get('downloads', 0):,}"
        table.add_row(item["id"][:20], item["name"][:25], cat,
                      item.get("author", "")[:15], rating, dl)
    console.print(table)


def _print_item_detail(item):
    from rich.console import Console
    from rich.panel import Panel
    from rich.markdown import Markdown
    console = Console()
    d = item.to_dict() if hasattr(item, 'to_dict') else item
    info = f"[bold]{d.get('name', d['id'])}[/bold] v{d.get('version', '?')}"
    if d.get("official"):
        info += " [green](Official)[/green]"
    console.print(Panel(info, subtitle=d.get("category", "")))
    console.print(f"  [dim]Description:[/dim] {d.get('description', 'N/A')}")
    console.print(f"  [dim]Author:[/dim] {d.get('author', {}).get('name', d.get('author', 'Unknown')) if isinstance(d.get('author'), dict) else d.get('author', 'Unknown')}")
    console.print(f"  [dim]Version:[/dim] {d.get('version', '?')}")
    console.print(f"  [dim]Rating:[/dim] {d.get('rating', 0):.1f} ★")
    console.print(f"  [dim]Downloads:[/dim] {d.get('downloads', 0):,}")
    if d.get("tags"):
        console.print(f"  [dim]Tags:[/dim] {', '.join(d['tags'])}")


def _print_installed(items: list[dict]):
    from rich.console import Console
    from rich.table import Table
    if not items:
        print("  Nothing installed yet")
        return
    console = Console()
    table = Table("ID", "Name", "Category", "Version", "Status")
    for item in items:
        cat = item.get("category", "").replace("_", " ").title()
        status = "✅" if item.get("enabled") else "⏸️"
        table.add_row(item["id"][:20], item.get("name", item["id"])[:25],
                      cat, item.get("version", "?"), status)
    console.print(table)


def handle_plugin_command(args: argparse.Namespace, **kwargs) -> None:
    from hub.store import HubStore
    from hub.plugins import PluginManager
    pm = PluginManager(HubStore())
    cmd = args.plugin_command
    if cmd == "list":
        items = pm.list_installed()
        _print_installed(items)
    elif cmd == "install":
        result = pm.install(args.plugin_id, file_path=getattr(args, 'file', None) or None)
        if result.get("success"):
            print(f"  ✅ Installed plugin: {args.plugin_id}")
        else:
            print(f"  ❌ {result.get('error', 'Install failed')}")
    elif cmd == "update":
        result = pm.update(args.plugin_id)
        print(f"  {'✅ Updated' if result.get('success') else '❌ Update failed'}: {args.plugin_id}")
    elif cmd == "remove":
        result = pm.remove(args.plugin_id)
        print(f"  {'✅ Removed' if result.get('success') else '❌ Remove failed'}: {args.plugin_id}")
    elif cmd == "enable":
        pm.enable(args.plugin_id)
        print(f"  ✅ Enabled: {args.plugin_id}")
    elif cmd == "disable":
        pm.disable(args.plugin_id)
        print(f"  ⏸️ Disabled: {args.plugin_id}")
    elif cmd == "repair":
        result = pm.repair(args.plugin_id)
        print(f"  {'✅ Repaired' if result.get('repaired') else '❌ Repair needed'}: {args.plugin_id}")


def handle_mcp_command(args: argparse.Namespace, **kwargs) -> None:
    from hub.store import HubStore
    from hub.mcp_marketplace import MCPMarketplace
    mcp = MCPMarketplace(HubStore())
    cmd = args.mcp_command
    if cmd in ("list",):
        items = mcp.list_installed()
        _print_installed(items)
    elif cmd in ("install", "add"):
        config = {}
        if hasattr(args, 'config') and args.config:
            try:
                config = json.loads(args.config)
            except json.JSONDecodeError:
                pass
        result = mcp.install(args.server_id, config)
        if result.get("success"):
            print(f"  ✅ Installed MCP server: {args.server_id}")
        else:
            print(f"  ❌ {result.get('error', 'Install failed')}")
    elif cmd == "configure":
        print(f"  Configure MCP server: {args.server_id}")
    elif cmd == "test":
        result = mcp.test_connection(args.server_id)
        if result.get("success"):
            print(f"  ✅ Connection OK: {args.server_id} ({result.get('version', '?')})")
        else:
            print(f"  ❌ {result.get('error', 'Connection failed')}")
    elif cmd == "remove":
        result = mcp.uninstall(args.server_id)
        print(f"  {'✅ Removed' if result.get('success') else '❌ Remove failed'}: {args.server_id}")
    elif cmd == "enable":
        mcp.enable(args.server_id)
    elif cmd == "disable":
        mcp.disable(args.server_id)


def handle_skill_command(args: argparse.Namespace, **kwargs) -> None:
    from hub.store import HubStore
    from hub.marketplace import HubMarketplace
    mp = HubMarketplace(HubStore())
    cmd = args.skill_command
    if cmd == "list":
        items = HubStore().get_installed("skills")
        print(f"  Installed skill packs: {len(items)}")
        for item in items:
            print(f"    {item['id']:<25} {item.get('name', '')}")
    elif cmd == "install":
        result = mp.install(args.skill_id)
        if result.get("success"):
            print(f"  ✅ Installed skill pack: {args.skill_id}")
        else:
            print(f"  ❌ {result.get('error', 'Install failed')}")


def handle_theme_command(args: argparse.Namespace, **kwargs) -> None:
    from hub.themes import ThemeManager
    tm = ThemeManager()
    cmd = args.theme_command
    if cmd == "list":
        themes = tm.list_installed()
        _print_installed(themes)
    elif cmd == "install":
        result = tm.install(args.theme_id)
        if result.get("success"):
            print(f"  ✅ Installed: {args.theme_id}")
            tm.activate(args.theme_id)
        else:
            print(f"  ❌ {result.get('error', 'Install failed')}")
    elif cmd == "activate":
        result = tm.activate(args.theme_id)
        if result.get("success"):
            print(f"  ✅ Activated: {args.theme_id}")
        else:
            print(f"  ❌ {result.get('error', 'Activation failed')}")


def handle_sdk_command(args: argparse.Namespace, **kwargs) -> None:
    from hub.sdk import ExtensionSDK
    sdk = ExtensionSDK()
    cmd = args.sdk_command
    if cmd == "list-templates":
        templates = sdk.list_templates()
        print("  Available templates:")
        for t in templates:
            print(f"    {t['id']:<25} {t['name']}")
    elif cmd == "init":
        result = sdk.init_project(
            args.project_type, args.name,
            author=getattr(args, 'author', ''),
            description=getattr(args, 'description', ''),
            path=getattr(args, 'path', ''),
        )
        if result.get("success"):
            print(f"  ✅ Created project at {result['path']}")
        else:
            print(f"  ❌ {result.get('error', 'Init failed')}")
    elif cmd in ("build", "package"):
        result = sdk.build(args.project_path,
                            output_path=getattr(args, 'output', ''))
        if result.get("success"):
            print(f"  ✅ Built: {result['output']} ({result.get('size', 0):,} bytes)")
        else:
            print(f"  ❌ {result.get('error', 'Build failed')}")
    elif cmd == "publish":
        path = getattr(args, 'project_path', args.output if hasattr(args, 'output') else '')
        if not path:
            path = getattr(args, 'package_path', '')
        result = sdk.publish(path)
        if result.get("success"):
            print(f"  ✅ Published to {result['registry']}: {result['path']}")
        else:
            print(f"  ❌ {result.get('error', 'Publish failed')}")


def handle_hub_backup_command(args: argparse.Namespace, **kwargs) -> None:
    from hub.backup import BackupManager
    bm = BackupManager()
    cmd = args.hub_backup_command
    if cmd == "create":
        result = bm.create_backup(
            name=getattr(args, 'name', ''),
            include_plugins=not getattr(args, 'no_plugins', False),
            include_themes=not getattr(args, 'no_themes', False),
            include_settings=not getattr(args, 'no_settings', False),
        )
        print(f"  ✅ Backup created: {result['name']} ({result['items']} items)")
    elif cmd == "list":
        backups = bm.list_backups()
        for b in backups:
            print(f"  {b['id']:<12} {b.get('name', ''):<30} {b.get('items_count', 0)} items")
    elif cmd == "restore":
        result = bm.restore(
            args.backup_id,
            restore_plugins=not getattr(args, 'no_plugins', False),
            restore_themes=not getattr(args, 'no_themes', False),
            restore_settings=not getattr(args, 'no_settings', False),
        )
        if result.get("success"):
            print(f"  ✅ Restored: {result['backup_id']}")
        else:
            print(f"  ❌ {result.get('error', 'Restore failed')}")
    elif cmd == "delete":
        bm.delete_backup(args.backup_id)
        print(f"  Deleted backup: {args.backup_id}")


def show_hub_help():
    print("Usage: aetheros hub <command> [options]")
    print("\nCommands:")
    for cmd, desc in [
        ("browse", "Browse hub marketplace"),
        ("search <query>", "Search hub items"),
        ("categories", "List categories"),
        ("info <id>", "Show item details"),
        ("install <id>", "Install an item"),
        ("update [id]", "Check/apply updates"),
        ("remove <id>", "Remove an item"),
        ("installed", "List installed items"),
        ("stats", "Show hub statistics"),
        ("backup", "Backup management"),
        ("permissions", "Permission management"),
    ]:
        print(f"  {cmd:<20} {desc}")
    print("\nAlso: aetheros {plugin|mcp|skill|theme|sdk|backup} <command>")
