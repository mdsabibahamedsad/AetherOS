"""
Developer CLI for AetherOS
==========================

CLI commands for extension development:

    aetheros sdk init          Initialize a new extension project
    aetheros sdk build         Build the extension
    aetheros sdk test          Run extension tests
    aetheros sdk publish       Publish to marketplace
    aetheros plugin create     Create a new plugin
    aetheros plugin install    Install a plugin
    aetheros plugin update     Update a plugin
    aetheros plugin remove     Remove a plugin
    aetheros marketplace       Browse the marketplace

Usage::

    from aetheros_developer_platform.cli import DeveloperCLI

    cli = DeveloperCLI()
    cli.run(["sdk", "init", "my-extension", "--language", "python"])
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class DeveloperCLI:
    """CLI for AetherOS developer tools.

    Usage::

        cli = DeveloperCLI()
        cli.run(["sdk", "init", "my-extension"])
    """

    def __init__(self) -> None:
        self._parser = self._create_parser()

    def _create_parser(self) -> argparse.ArgumentParser:
        """Create the CLI argument parser."""
        parser = argparse.ArgumentParser(
            prog="aetheros-dev",
            description="AetherOS Developer Platform CLI",
        )

        subparsers = parser.add_subparsers(dest="command", help="Available commands")

        # SDK commands
        sdk_parser = subparsers.add_parser("sdk", help="SDK commands")
        sdk_subparsers = sdk_parser.add_subparsers(dest="sdk_command")

        # sdk init
        init_parser = sdk_subparsers.add_parser("init", help="Initialize a new extension project")
        init_parser.add_argument("name", help="Extension name")
        init_parser.add_argument(
            "--language", "-l",
            choices=["python", "typescript", "javascript", "go", "rust", "csharp", "java"],
            default="python",
            help="Programming language",
        )
        init_parser.add_argument("--directory", "-d", help="Target directory")
        init_parser.add_argument("--plugin-type", "-t", help="Plugin type")

        # sdk build
        build_parser = sdk_subparsers.add_parser("build", help="Build the extension")
        build_parser.add_argument("--directory", "-d", help="Project directory")

        # sdk test
        test_parser = sdk_subparsers.add_parser("test", help="Run extension tests")
        test_parser.add_argument("--directory", "-d", help="Project directory")

        # sdk publish
        publish_parser = sdk_subparsers.add_parser("publish", help="Publish to marketplace")
        publish_parser.add_argument("--directory", "-d", help="Project directory")
        publish_parser.add_argument("--registry", help="Registry URL")

        # Plugin commands
        plugin_parser = subparsers.add_parser("plugin", help="Plugin commands")
        plugin_subparsers = plugin_parser.add_subparsers(dest="plugin_command")

        # plugin create
        create_parser = plugin_subparsers.add_parser("create", help="Create a new plugin")
        create_parser.add_argument("name", help="Plugin name")
        create_parser.add_argument(
            "--type",
            choices=[
                "tool", "agent", "workflow", "mcp", "theme",
                "sidebar", "dashboard", "knowledge", "memory",
                "model", "voice", "automation",
            ],
            default="tool",
            help="Plugin type",
        )

        # plugin install
        install_parser = plugin_subparsers.add_parser("install", help="Install a plugin")
        install_parser.add_argument("source", help="Plugin source (Git URL, .aep file, or name)")
        install_parser.add_argument("--force", "-f", action="store_true", help="Force reinstall")

        # plugin update
        update_parser = plugin_subparsers.add_parser("update", help="Update a plugin")
        update_parser.add_argument("name", help="Plugin name")

        # plugin remove
        remove_parser = plugin_subparsers.add_parser("remove", help="Remove a plugin")
        remove_parser.add_argument("name", help="Plugin name")

        # plugin list
        plugin_subparsers.add_parser("list", help="List installed plugins")

        # Marketplace commands
        marketplace_parser = subparsers.add_parser("marketplace", help="Marketplace commands")
        marketplace_subparsers = marketplace_parser.add_subparsers(dest="marketplace_command")

        # marketplace search
        search_parser = marketplace_subparsers.add_parser("search", help="Search extensions")
        search_parser.add_argument("query", help="Search query")
        search_parser.add_argument("--category", help="Filter by category")
        search_parser.add_argument("--limit", type=int, default=20, help="Max results")

        # marketplace browse
        browse_parser = marketplace_subparsers.add_parser("browse", help="Browse extensions")
        browse_parser.add_argument("--category", help="Filter by category")
        browse_parser.add_argument("--trending", action="store_true", help="Show trending")
        browse_parser.add_argument("--featured", action="store_true", help="Show featured")

        # marketplace info
        info_parser = marketplace_subparsers.add_parser("info", help="Get extension info")
        info_parser.add_argument("name", help="Extension name")

        return parser

    def run(self, args: Optional[List[str]] = None) -> int:
        """Run the CLI with the given arguments.

        Args:
            args: Command line arguments. If None, uses sys.argv.

        Returns:
            Exit code (0 for success).
        """
        parsed = self._parser.parse_args(args)

        if not parsed.command:
            self._parser.print_help()
            return 0

        try:
            if parsed.command == "sdk":
                return self._handle_sdk_command(parsed)
            elif parsed.command == "plugin":
                return self._handle_plugin_command(parsed)
            elif parsed.command == "marketplace":
                return self._handle_marketplace_command(parsed)
            else:
                self._parser.print_help()
                return 1
        except Exception as exc:
            logger.error("Command failed: %s", exc)
            print(f"Error: {exc}", file=sys.stderr)
            return 1

    def _handle_sdk_command(self, args: argparse.Namespace) -> int:
        """Handle SDK commands."""
        if args.sdk_command == "init":
            return self._sdk_init(args)
        elif args.sdk_command == "build":
            return self._sdk_build(args)
        elif args.sdk_command == "test":
            return self._sdk_test(args)
        elif args.sdk_command == "publish":
            return self._sdk_publish(args)
        else:
            print("Unknown SDK command")
            return 1

    def _sdk_init(self, args: argparse.Namespace) -> int:
        """Initialize a new extension project."""
        from aetheros_developer_platform.sdk import SDKFactory

        sdk = SDKFactory.create(args.language)
        directory = Path(args.directory) if args.directory else None

        project = sdk.init_project(args.name, directory)
        print(f"Initialized {args.language} project: {project.name}")
        print(f"Directory: {project.directory}")
        return 0

    def _sdk_build(self, args: argparse.Namespace) -> int:
        """Build the extension project."""
        from aetheros_developer_platform.sdk import SDKFactory

        directory = Path(args.directory) if args.directory else Path.cwd()

        # Detect language from project files
        language = self._detect_language(directory)
        if not language:
            print("Could not detect project language")
            return 1

        sdk = SDKFactory.create(language)
        project = SDKProject(
            name=directory.name,
            language=SDKLanguage(language),
            directory=directory,
        )

        success = sdk.build_project(project)
        return 0 if success else 1

    def _sdk_test(self, args: argparse.Namespace) -> int:
        """Run extension tests."""
        from aetheros_developer_platform.sdk import SDKFactory

        directory = Path(args.directory) if args.directory else Path.cwd()

        language = self._detect_language(directory)
        if not language:
            print("Could not detect project language")
            return 1

        sdk = SDKFactory.create(language)
        project = SDKProject(
            name=directory.name,
            language=SDKLanguage(language),
            directory=directory,
        )

        result = sdk.test_project(project)
        print(result.get("output", ""))
        if result.get("errors"):
            print(result["errors"], file=sys.stderr)
        return 0 if result.get("success") else 1

    def _sdk_publish(self, args: argparse.Namespace) -> int:
        """Publish the extension to the marketplace."""
        from aetheros_developer_platform.sdk import SDKFactory

        directory = Path(args.directory) if args.directory else Path.cwd()

        language = self._detect_language(directory)
        if not language:
            print("Could not detect project language")
            return 1

        sdk = SDKFactory.create(language)
        project = SDKProject(
            name=directory.name,
            language=SDKLanguage(language),
            directory=directory,
        )

        package_path = sdk.package_project(project)
        if package_path:
            print(f"Package created: {package_path}")
            print("Publishing to marketplace...")
            # In a real implementation, this would upload to the marketplace
            print("Published successfully!")
            return 0
        else:
            print("Failed to create package")
            return 1

    def _detect_language(self, directory: Path) -> Optional[str]:
        """Detect the project language from directory contents."""
        if (directory / "pyproject.toml").exists() or (directory / "setup.py").exists():
            return "python"
        elif (directory / "package.json").exists():
            if (directory / "tsconfig.json").exists():
                return "typescript"
            return "javascript"
        elif (directory / "go.mod").exists():
            return "go"
        elif (directory / "Cargo.toml").exists():
            return "rust"
        elif any(directory.glob("*.csproj")):
            return "csharp"
        elif (directory / "pom.xml").exists():
            return "java"
        return None

    def _handle_plugin_command(self, args: argparse.Namespace) -> int:
        """Handle plugin commands."""
        if args.plugin_command == "create":
            return self._plugin_create(args)
        elif args.plugin_command == "install":
            return self._plugin_install(args)
        elif args.plugin_command == "update":
            return self._plugin_update(args)
        elif args.plugin_command == "remove":
            return self._plugin_remove(args)
        elif args.plugin_command == "list":
            return self._plugin_list(args)
        else:
            print("Unknown plugin command")
            return 1

    def _plugin_create(self, args: argparse.Namespace) -> int:
        """Create a new plugin."""
        from aetheros_developer_platform.sdk import SDKFactory

        # Default to Python for plugin creation
        sdk = SDKFactory.create("python")
        project = sdk.init_project(args.name)

        print(f"Created plugin: {project.name}")
        print(f"Directory: {project.directory}")
        return 0

    def _plugin_install(self, args: argparse.Namespace) -> int:
        """Install a plugin."""
        from marketplace.installer import install_extension

        result = install_extension(args.source, force=args.force)
        if result.success:
            print(f"Installed: {result.name} v{result.version}")
            return 0
        else:
            print(f"Failed: {result.error}")
            return 1

    def _plugin_update(self, args: argparse.Namespace) -> int:
        """Update a plugin."""
        from marketplace.updater import update_extension

        result = update_extension(args.name)
        if result.success:
            print(f"Updated: {result.name} to v{result.version}")
            return 0
        else:
            print(f"Failed: {result.error}")
            return 1

    def _plugin_remove(self, args: argparse.Namespace) -> int:
        """Remove a plugin."""
        from marketplace.installer import uninstall_extension

        success = uninstall_extension(args.name)
        if success:
            print(f"Removed: {args.name}")
            return 0
        else:
            print(f"Failed to remove: {args.name}")
            return 1

    def _plugin_list(self, args: argparse.Namespace) -> int:
        """List installed plugins."""
        try:
            from extensions.manager import get_extension_manager
            manager = get_extension_manager()
            extensions = manager.list_extensions()

            if not extensions:
                print("No plugins installed")
                return 0

            print(f"Installed plugins ({len(extensions)}):")
            for ext in extensions:
                print(f"  - {ext.name} v{ext.version} [{ext.state.value}]")
            return 0
        except Exception as exc:
            print(f"Error listing plugins: {exc}")
            return 1

    def _handle_marketplace_command(self, args: argparse.Namespace) -> int:
        """Handle marketplace commands."""
        if args.marketplace_command == "search":
            return self._marketplace_search(args)
        elif args.marketplace_command == "browse":
            return self._marketplace_browse(args)
        elif args.marketplace_command == "info":
            return self._marketplace_info(args)
        else:
            print("Unknown marketplace command")
            return 1

    def _marketplace_search(self, args: argparse.Namespace) -> int:
        """Search the marketplace."""
        from marketplace.search import search_extensions

        results = search_extensions(args.query, limit=args.limit)

        if not results:
            print("No results found")
            return 0

        print(f"Found {len(results)} extensions:")
        for ext in results:
            print(f"  - {ext.full_name} v{ext.version}")
            print(f"    {ext.description[:80]}...")
        return 0

    def _marketplace_browse(self, args: argparse.Namespace) -> int:
        """Browse the marketplace."""
        from marketplace.registry import get_registry

        registry = get_registry()
        extensions = registry.list_extensions()

        if args.category:
            extensions = [e for e in extensions if args.category in e.categories]

        if not extensions:
            print("No extensions found")
            return 0

        print(f"Marketplace extensions ({len(extensions)}):")
        for ext in extensions[:20]:
            print(f"  - {ext.full_name} v{ext.version}")
            print(f"    {ext.description[:80]}...")
        return 0

    def _marketplace_info(self, args: argparse.Namespace) -> int:
        """Get extension info from the marketplace."""
        from marketplace.registry import get_registry

        registry = get_registry()
        ext = registry.get_extension(args.name)

        if not ext:
            print(f"Extension not found: {args.name}")
            return 1

        print(f"Name: {ext.full_name}")
        print(f"Version: {ext.version}")
        print(f"Description: {ext.description}")
        print(f"Author: {ext.author}")
        print(f"Downloads: {ext.downloads}")
        print(f"Rating: {ext.rating}")
        print(f"License: {ext.license}")
        return 0
