"""
CLI command handlers for ``aetheros sdk`` and ``aetheros marketplace`` subcommands.

These handlers are injected into the argparse tree by ``main.py``.
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def cmd_sdk(args) -> None:
    """Dispatch ``aetheros sdk`` subcommands."""
    action = getattr(args, "sdk_action", None)

    if action == "init":
        _sdk_init(args)
    elif action == "build" or action == "package":
        _sdk_build(args)
    elif action == "validate":
        _sdk_validate(args)
    elif action == "sign":
        _sdk_sign(args)
    elif action == "verify":
        _sdk_verify(args)
    elif action in ("templates", "list-templates"):
        _sdk_templates()
    elif action == "publish":
        _sdk_publish(args)
    else:
        from rich.console import Console
        Console().print("[yellow]Usage:[/yellow] aetheros sdk <command>")
        Console().print("  init       Scaffold a new plugin from a template")
        Console().print("  build      Build and package a plugin into a .aep file")
        Console().print("  validate   Validate a plugin manifest")
        Console().print("  sign       Sign a plugin package")
        Console().print("  verify     Verify a plugin package signature")
        Console().print("  templates  List available plugin templates")
        Console().print("  publish    Publish a plugin to the marketplace")
        sys.exit(0)


def _sdk_init(args) -> None:
    """Scaffold a new plugin from a template."""
    from sdk.templates import scaffold_plugin, list_templates

    name = args.name
    template_type = getattr(args, "type", "tool")
    description = getattr(args, "description", "")
    author = getattr(args, "author", "")
    output_dir = Path(getattr(args, "output", "") or Path.cwd())

    available = list_templates()
    if template_type not in available:
        print(f"Unknown template type: '{template_type}'.")
        print(f"Available: {', '.join(available)}")
        sys.exit(1)

    try:
        created = scaffold_plugin(
            template_type, output_dir, name,
            description=description,
            author=author,
        )
        from rich.console import Console
        console = Console()
        console.print(f"\n[green]✓[/green] Scaffolded {template_type} plugin [bold]{name}[/bold]")
        console.print(f"  Location: {output_dir / name}")
        console.print(f"  Files created:")
        for f in created:
            console.print(f"    {f.relative_to(output_dir / name)}")
        console.print()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


def _sdk_build(args) -> None:
    """Build and package a plugin."""
    from sdk.packaging import pack_plugin

    source_dir = Path(getattr(args, "directory", ".")).resolve()
    output_path = getattr(args, "output", "") or None
    if output_path:
        output_path = Path(output_path)

    from rich.console import Console
    console = Console()

    try:
        console.print(f"[dim]Packaging plugin from {source_dir}...[/dim]")
        pkg = pack_plugin(source_dir, output_path=output_path)
        console.print(
            f"\n[green]✓[/green] Package created: [bold]{pkg.package_path}[/bold]"
        )
        console.print(f"  Size: {_format_size(pkg.file_size)}")
        console.print(f"  Hash: {pkg.file_hash[:16]}...")
        console.print()
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)


def _sdk_validate(args) -> None:
    """Validate a plugin manifest."""
    from sdk.validator import validate_plugin_manifest, validate_extension_manifest
    import yaml

    path = Path(getattr(args, "path", ".")).resolve()
    if path.is_dir():
        manifest_file = path / "manifest.yaml"
        if not manifest_file.exists():
            manifest_file = path / "plugin.yaml"
    else:
        manifest_file = path

    if not manifest_file.exists():
        print(f"Manifest not found: {manifest_file}")
        sys.exit(1)

    from rich.console import Console
    console = Console()

    try:
        data = yaml.safe_load(manifest_file.read_text(encoding="utf-8")) or {}
        errors = validate_plugin_manifest(data)

        if not errors:
            name = data.get("name", manifest_file.stem)
            version = data.get("version", "?")
            console.print(
                f"\n[green]✓[/green] [bold]{name}[/bold] v{version}: "
                f"manifest is valid"
            )
        else:
            console.print(
                f"\n[red]✗[/red] Validation failed ({len(errors)} error(s)):"
            )
            for e in errors:
                console.print(f"  • {e}")
            sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)


def _sdk_sign(args) -> None:
    """Sign a plugin package."""
    from sdk.packaging import PluginPackage
    from sdk.signing import sign_package

    package = PluginPackage(package_path=Path(args.package))
    key_path = Path(args.key)
    key_id = args.key_id

    if not package.package_path.exists():
        print(f"Package not found: {args.package}")
        sys.exit(1)

    if not key_path.exists():
        print(f"Key file not found: {key_path}")
        sys.exit(1)

    from rich.console import Console
    console = Console()

    try:
        private_key = key_path.read_text(encoding="utf-8")
        signature = sign_package(package, private_key, key_id)
        console.print(
            f"\n[green]✓[/green] Package signed: [bold]{package.package_path}[/bold]"
        )
        console.print(f"  Key ID: {key_id}")
        console.print(f"  Signature: {signature[:32]}...")
        console.print()
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)


def _sdk_verify(args) -> None:
    """Verify a plugin package signature."""
    from sdk.packaging import PluginPackage
    from sdk.signing import verify_signature, PublisherKey

    package = PluginPackage(package_path=Path(args.package))
    key_path = Path(args.key)

    from rich.console import Console
    console = Console()

    try:
        public_key = key_path.read_text(encoding="utf-8")
        pub_key = PublisherKey(
            key_id=key_path.stem,
            public_key=public_key,
        )
        valid = verify_signature(package, pub_key)
        if valid:
            console.print(
                f"\n[green]✓[/green] Signature verified: "
                f"[bold]{package.package_path}[/bold]"
            )
        else:
            console.print(
                f"\n[red]✗[/red] Signature invalid for "
                f"[bold]{package.package_path}[/bold]"
            )
            sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)


def _sdk_templates() -> None:
    """List available plugin templates."""
    from sdk.templates import list_templates

    from rich.console import Console
    from rich.table import Table

    templates = list_templates()
    if not templates:
        print("No templates available.")
        return

    table = Table(title="Plugin Templates")
    table.add_column("Type", style="bold")
    table.add_column("Description")

    type_descriptions = {
        "tool": "Tool plugin — register new tools",
        "agent": "Agent plugin — hook into agent lifecycle",
        "workflow": "Workflow plugin — compose multi-step workflows",
        "memory": "Memory provider — pluggable memory backend",
        "model": "Model provider — register inference backends",
        "voice": "Voice/TTS provider — text-to-speech",
        "notification": "Notification adapter — send alerts",
        "enterprise": "Enterprise integration — SSO, audit, compliance",
    }

    for t in templates:
        desc = type_descriptions.get(t, "")
        table.add_row(t, desc)

    Console().print(table)


def _sdk_publish(args) -> None:
    """Publish a plugin to the marketplace."""
    from sdk.packaging import PluginPackage, get_package_metadata

    pkg_path = Path(args.package)
    if not pkg_path.exists():
        print(f"Package not found: {pkg_path}")
        sys.exit(1)

    metadata = get_package_metadata(pkg_path)
    if metadata is None:
        print("Could not read package metadata")
        sys.exit(1)

    from rich.console import Console
    console = Console()

    registry_url = getattr(args, "registry", "") or "https://marketplace.aetheros.dev/api/v1"
    api_key = getattr(args, "api_key", "") or ""

    name = metadata.get("name", pkg_path.stem)
    version = metadata.get("version", "0.0.0")

    console.print(f"\n[dim]Publishing [bold]{name}[/bold] v{version} to {registry_url}...[/dim]")

    # Upload the package
    try:
        import urllib.request
        import json as _json

        data = pkg_path.read_bytes()
        boundary = "----AetherosFormBoundary"
        body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="package"; filename="{pkg_path.name}"\r\n'
            f"Content-Type: application/octet-stream\r\n\r\n"
        ).encode("utf-8") + data + f"\r\n--{boundary}--\r\n".encode("utf-8")

        req = urllib.request.Request(
            f"{registry_url.rstrip('/')}/publish",
            data=body,
            headers={
                "Content-Type": f"multipart/form-data; boundary={boundary}",
                "User-Agent": "AetherosSDK/1.0",
            },
        )
        if api_key:
            req.add_header("Authorization", f"Bearer {api_key}")

        resp = urllib.request.urlopen(req, timeout=30)
        result = _json.loads(resp.read().decode("utf-8"))
        extension_id = result.get("id", name)

        console.print(f"[green]✓[/green] Published! Extension ID: {extension_id}")
    except Exception as e:
        console.print(f"[red]Error:[/red] Could not publish: {e}")
        console.print("[dim]The package was built but could not be uploaded.[/dim]")
        console.print(f"[dim]Package: {pkg_path}[/dim]")
        sys.exit(1)


# ===========================================================================
# Marketplace commands
# ===========================================================================


def cmd_marketplace(args) -> None:
    """Dispatch ``aetheros marketplace`` subcommands."""
    action = getattr(args, "marketplace_action", None)

    if action == "search":
        _marketplace_search(args)
    elif action == "install":
        _marketplace_install(args)
    elif action == "update":
        _marketplace_update(args)
    elif action in ("remove", "rm", "uninstall"):
        _marketplace_remove(args)
    elif action in ("list", "ls"):
        _marketplace_list(args)
    elif action == "info":
        _marketplace_info(args)
    elif action == "popular":
        _marketplace_popular(args)
    elif action == "top-rated":
        _marketplace_top_rated(args)
    elif action == "sources":
        _marketplace_sources()
    elif action == "refresh":
        _marketplace_refresh()
    else:
        _marketplace_help()


def _marketplace_search(args) -> None:
    """Search the marketplace."""
    from marketplace.search import search_extensions

    query = getattr(args, "query", "")
    kind = getattr(args, "kind", None)
    category = getattr(args, "category", None)
    publisher = getattr(args, "publisher", None)
    verified = getattr(args, "verified", False)
    sort_by = getattr(args, "sort", "relevance")
    limit = getattr(args, "limit", 20)
    as_json = getattr(args, "json", False)

    from rich.console import Console
    console = Console()

    result = search_extensions(
        query=query or None,
        kind=kind, category=category, publisher=publisher,
        verified_only=verified, sort_by=sort_by, limit=limit,
    )

    if as_json:
        data = [
            {
                "id": e.id, "name": e.name, "version": e.version,
                "description": e.description, "publisher": e.publisher,
                "kind": e.kind, "rating": e.rating, "downloads": e.downloads,
                "verified": e.verified,
            }
            for e in result.results
        ]
        print(json.dumps(data, indent=2))
        return

    if not result.results:
        console.print("[dim]No extensions found matching your search.[/dim]")
        return

    from rich.table import Table
    table = Table(title=f"Extensions ({result.total} found)")
    table.add_column("Name", style="bold")
    table.add_column("Version")
    table.add_column("Kind")
    table.add_column("Publisher")
    table.add_column("Rating")
    table.add_column("Downloads")

    for ext in result.results:
        verified_mark = " ✓" if ext.verified else ""
        table.add_row(
            f"{ext.name}{verified_mark}",
            ext.version,
            ext.kind,
            ext.publisher or "-",
            f"{ext.rating:.1f}" if ext.rating > 0 else "-",
            f"{ext.downloads:,}" if ext.downloads > 0 else "-",
        )

    console.print()
    console.print(table)
    if result.has_more:
        console.print(f"[dim]... and {result.total - limit} more. Use --limit to show more.[/dim]")
    console.print()


def _marketplace_install(args) -> None:
    """Install an extension."""
    from marketplace.installer import install_extension

    from rich.console import Console
    console = Console()

    source = args.source
    force = getattr(args, "force", False)

    console.print(f"[dim]Installing {source}...[/dim]")

    try:
        result = install_extension(source, force=force)
        if result.success:
            console.print(
                f"\n[green]✓[/green] Installed [bold]{result.name}[/bold] "
                f"v{result.version}"
            )
            if result.target_dir:
                console.print(f"  Location: {result.target_dir}")
        else:
            if result.status.value == "already_installed":
                console.print(f"[yellow]•[/yellow] {result.error}")
            else:
                console.print(f"[red]Error:[/red] {result.error}")
                sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)


def _marketplace_update(args) -> None:
    """Update extensions."""
    from marketplace.updater import check_for_updates, update_extension

    from rich.console import Console
    console = Console()

    name = getattr(args, "name", "")

    if name:
        console.print(f"[dim]Updating {name}...[/dim]")
        result = update_extension(name)
        if result.success:
            console.print(
                f"\n[green]✓[/green] Updated [bold]{result.name}[/bold]: "
                f"{result.old_version} → {result.new_version}"
            )
        else:
            console.print(f"[red]Error:[/red] {result.error}")
            sys.exit(1)
    else:
        console.print("[dim]Checking for updates...[/dim]")
        updates = check_for_updates()
        if not updates:
            console.print("[green]✓[/green] All extensions are up to date.")
            return

        for update in updates:
            console.print(
                f"  [yellow]•[/yellow] [bold]{update.name}[/bold]: "
                f"{update.old_version} → {update.new_version}"
            )
        console.print("\nRun 'aetheros marketplace update <name>' to update a specific extension.")


def _marketplace_remove(args) -> None:
    """Remove an extension."""
    from marketplace.installer import uninstall_extension

    from rich.console import Console
    console = Console()

    name = args.name
    console.print(f"[dim]Removing {name}...[/dim]")

    if uninstall_extension(name):
        console.print(f"\n[yellow]✗[/yellow] Removed [bold]{name}[/bold]")
    else:
        console.print(f"[red]Error:[/red] Could not remove '{name}'")
        sys.exit(1)


def _marketplace_list(args) -> None:
    """List installed extensions."""
    from extensions.manager import get_extension_manager

    from rich.console import Console
    from rich.table import Table

    mgr = get_extension_manager()
    mgr.discover()
    extensions = mgr.list_extensions()

    as_json = getattr(args, "json", False)

    if as_json:
        data = [
            {
                "name": e.name, "version": e.version,
                "state": e.state.value,
                "error": e.error,
            }
            for e in extensions
        ]
        print(json.dumps(data, indent=2))
        return

    if not extensions:
        Console().print("[dim]No extensions installed.[/dim]")
        return

    table = Table(title="Installed Extensions")
    table.add_column("Name", style="bold")
    table.add_column("Version")
    table.add_column("State")
    table.add_column("Error")

    for ext in extensions:
        state_colors = {
            "enabled": "[green]enabled[/green]",
            "disabled": "[yellow]disabled[/yellow]",
            "error": "[red]error[/red]",
        }
        state_str = state_colors.get(ext.state.value, ext.state.value)

        table.add_row(
            ext.name,
            ext.version,
            state_str,
            ext.error or "",
        )

    Console().print()
    Console().print(table)

    health = mgr.get_health_summary()
    Console().print(
        f"[dim]{health['healthy']}/{health['total']} healthy, "
        f"{health['error']} with errors[/dim]"
    )
    Console().print()


def _marketplace_info(args) -> None:
    """Show extension info."""
    from marketplace.registry import get_registry

    from rich.console import Console
    from rich.panel import Panel

    name = args.name
    registry = get_registry()
    entry = registry.get_extension(name)

    as_json = getattr(args, "json", False)

    if entry is None:
        # Check local
        from extensions.manager import get_extension_manager
        mgr = get_extension_manager()
        ext = mgr.get_extension(name)
        if ext:
            if as_json:
                print(json.dumps({
                    "name": ext.name, "version": ext.version,
                    "state": ext.state.value,
                }, indent=2))
                return
            from rich.table import Table
            table = Table(title=f"Extension: {ext.name}")
            table.add_column("Property")
            table.add_column("Value")
            table.add_row("Name", ext.name)
            table.add_row("Version", ext.version)
            table.add_row("State", ext.state.value)
            if ext.error:
                table.add_row("Error", ext.error)
            Console().print(table)
            return

        Console().print(f"[red]Extension '{name}' not found.[/red]")
        sys.exit(1)

    if as_json:
        print(json.dumps({
            "id": entry.id, "name": entry.name, "version": entry.version,
            "description": entry.description, "publisher": entry.publisher,
            "kind": entry.kind, "rating": entry.rating,
            "downloads": entry.downloads,
            "verified": entry.verified,
            "categories": entry.categories,
            "tags": entry.tags,
            "license": entry.license,
        }, indent=2))
        return

    from rich.table import Table
    table = Table(title=f"Extension: {entry.name}")
    table.add_column("Property")
    table.add_column("Value")
    table.add_row("ID", entry.id)
    table.add_row("Version", entry.version)
    table.add_row("Description", entry.description)
    table.add_row("Publisher", entry.publisher)
    table.add_row("Kind", entry.kind)
    table.add_row("Rating", f"{entry.rating:.1f}" if entry.rating > 0 else "-")
    table.add_row("Downloads", f"{entry.downloads:,}" if entry.downloads > 0 else "-")
    table.add_row("Verified", "✓" if entry.verified else "✗")
    table.add_row("License", entry.license or "-")
    if entry.categories:
        table.add_row("Categories", ", ".join(entry.categories))
    if entry.tags:
        table.add_row("Tags", ", ".join(entry.tags))

    Console().print()
    Console().print(table)
    Console().print()


def _marketplace_popular(args) -> None:
    """List popular extensions."""
    from marketplace.discovery import get_popular_extensions

    from rich.console import Console
    from rich.table import Table

    limit = getattr(args, "limit", 10)
    extensions = get_popular_extensions(limit=limit)

    table = Table(title=f"Popular Extensions")
    table.add_column("Name", style="bold")
    table.add_column("Publisher")
    table.add_column("Downloads")
    table.add_column("Rating")

    for ext in extensions:
        table.add_row(
            ext.name, ext.publisher or "-",
            f"{ext.downloads:,}" if ext.downloads > 0 else "-",
            f"{ext.rating:.1f}" if ext.rating > 0 else "-",
        )

    Console().print()
    Console().print(table)
    Console().print()


def _marketplace_top_rated(args) -> None:
    """List top-rated extensions."""
    from marketplace.discovery import get_top_rated_extensions

    from rich.console import Console
    from rich.table import Table

    limit = getattr(args, "limit", 10)
    extensions = get_top_rated_extensions(limit=limit)

    table = Table(title="Top-Rated Extensions")
    table.add_column("Name", style="bold")
    table.add_column("Publisher")
    table.add_column("Rating")
    table.add_column("Downloads")

    for ext in extensions:
        table.add_row(
            ext.name, ext.publisher or "-",
            f"{ext.rating:.1f}" if ext.rating > 0 else "-",
            f"{ext.downloads:,}" if ext.downloads > 0 else "-",
        )

    Console().print()
    Console().print(table)
    Console().print()


def _marketplace_sources() -> None:
    """List configured marketplace sources."""
    from marketplace.registry import get_registry

    from rich.console import Console
    from rich.table import Table

    registry = get_registry()
    sources = registry.list_sources()

    if not sources:
        Console().print("[dim]No marketplace sources configured.[/dim]")
        return

    table = Table(title="Marketplace Sources")
    table.add_column("Name")
    table.add_column("Type")
    table.add_column("URL")
    table.add_column("Enabled")

    for src in sources:
        table.add_row(
            src.name,
            src.source.value,
            src.url,
            "[green]✓[/green]" if src.enabled else "[red]✗[/red]",
        )

    Console().print()
    Console().print(table)
    Console().print()


def _marketplace_refresh() -> None:
    """Refresh the marketplace cache."""
    from marketplace.registry import get_registry

    from rich.console import Console

    registry = get_registry()
    count = registry.refresh()
    Console().print(f"[green]✓[/green] Refreshed: {count} extensions available")


def _marketplace_help() -> None:
    """Show marketplace help."""
    from rich.console import Console
    console = Console()
    console.print("[yellow]Usage:[/yellow] aetheros marketplace <command>")
    console.print()
    console.print("  search     Search the marketplace")
    console.print("  install    Install an extension")
    console.print("  update     Update extensions")
    console.print("  remove     Remove an extension")
    console.print("  list       List installed extensions")
    console.print("  info       Show extension details")
    console.print("  popular    Show popular extensions")
    console.print("  top-rated  Show top-rated extensions")
    console.print("  sources    List configured sources")
    console.print("  refresh    Refresh the extension cache")
    console.print()


def _format_size(size: int) -> str:
    """Format a file size in human-readable form."""
    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size / (1024 * 1024):.1f} MB"
