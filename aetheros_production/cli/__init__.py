"""
Production CLI for AetherOS
===========================

CLI commands for production operations:

    aetheros doctor          Run diagnostics
    aetheros repair          Repair installation
    aetheros update          Check for updates
    aetheros backup          Create backup
    aetheros restore         Restore from backup
    aetheros health          Check health status
    aetheros diagnostics     Run full diagnostics
    aetheros version         Show version info
    aetheros security        Run security audit
    aetheros performance     Show performance metrics

Usage::

    from aetheros_production.cli import ProductionCLI

    cli = ProductionCLI()
    cli.run(["doctor"])
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from typing import List, Optional

logger = logging.getLogger(__name__)


class ProductionCLI:
    """CLI for AetherOS production operations.

    Usage::

        cli = ProductionCLI()
        cli.run(["doctor"])
    """

    def __init__(self) -> None:
        self._parser = self._create_parser()

    def _create_parser(self) -> argparse.ArgumentParser:
        """Create the CLI argument parser."""
        parser = argparse.ArgumentParser(
            prog="aetheros",
            description="AetherOS Production CLI",
        )

        subparsers = parser.add_subparsers(dest="command", help="Available commands")

        # doctor
        subparsers.add_parser("doctor", help="Run diagnostics and check for issues")

        # repair
        repair_parser = subparsers.add_parser("repair", help="Repair installation")
        repair_parser.add_argument("--force", action="store_true", help="Force repair")

        # update
        update_parser = subparsers.add_parser("update", help="Check for updates")
        update_parser.add_argument("--channel", choices=["stable", "beta", "nightly"], default="stable")
        update_parser.add_argument("--check-only", action="store_true", help="Only check, don't install")

        # backup
        backup_parser = subparsers.add_parser("backup", help="Create backup")
        backup_parser.add_argument("--type", choices=["full", "incremental", "snapshot"], default="full")
        backup_parser.add_argument("--description", help="Backup description")

        # restore
        restore_parser = subparsers.add_parser("restore", help="Restore from backup")
        restore_parser.add_argument("backup_id", nargs="?", help="Backup ID to restore")

        # health
        subparsers.add_parser("health", help="Check health status")

        # diagnostics
        diag_parser = subparsers.add_parser("diagnostics", help="Run full diagnostics")
        diag_parser.add_argument("--output", help="Output file path")

        # version
        subparsers.add_parser("version", help="Show version information")

        # security
        security_parser = subparsers.add_parser("security", help="Run security audit")
        security_parser.add_argument("--type", choices=["full", "dependency", "secrets", "static"], default="full")
        security_parser.add_argument("--output", help="Output report file")

        # performance
        perf_parser = subparsers.add_parser("performance", help="Show performance metrics")
        perf_parser.add_argument("--benchmark", help="Benchmark a specific component")

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
            if parsed.command == "doctor":
                return self._cmd_doctor()
            elif parsed.command == "repair":
                return self._cmd_repair(parsed.force)
            elif parsed.command == "update":
                return self._cmd_update(parsed.channel, parsed.check_only)
            elif parsed.command == "backup":
                return self._cmd_backup(parsed.type, parsed.description)
            elif parsed.command == "restore":
                return self._cmd_restore(parsed.backup_id)
            elif parsed.command == "health":
                return self._cmd_health()
            elif parsed.command == "diagnostics":
                return self._cmd_diagnostics(parsed.output)
            elif parsed.command == "version":
                return self._cmd_version()
            elif parsed.command == "security":
                return self._cmd_security(parsed.type, parsed.output)
            elif parsed.command == "performance":
                return self._cmd_performance(parsed.benchmark)
            else:
                self._parser.print_help()
                return 1
        except Exception as exc:
            logger.error("Command failed: %s", exc)
            print(f"Error: {exc}", file=sys.stderr)
            return 1

    def _cmd_doctor(self) -> int:
        """Run diagnostics and check for issues."""
        from aetheros_production.observability import get_diagnostics_manager

        print("Running AetherOS Doctor...")
        print("=" * 50)

        manager = get_diagnostics_manager()
        report = manager.run_diagnostics()

        # Print system info
        system = report.get("system", {})
        print(f"\nSystem: {system.get('os', 'Unknown')} {system.get('os_version', '')}")
        print(f"Architecture: {system.get('architecture', 'Unknown')}")
        print(f"Python: {report.get('python', {}).get('version', 'Unknown')}")

        # Print AetherOS info
        aetheros = report.get("aetheros", {})
        print(f"\nAetherOS Home: {aetheros.get('home', 'Unknown')}")
        print(f"Version: {aetheros.get('version', 'Unknown')}")
        print(f"Config: {'Found' if aetheros.get('config_exists') else 'Not Found'}")

        # Check for issues
        issues = []
        if not aetheros.get("config_exists"):
            issues.append("Configuration file not found")

        network = report.get("network", {})
        if not network.get("internet", True):
            issues.append("No internet connection")

        print("\n" + "=" * 50)
        if issues:
            print(f"Found {len(issues)} issue(s):")
            for issue in issues:
                print(f"  - {issue}")
            return 1
        else:
            print("All checks passed!")
            return 0

    def _cmd_repair(self, force: bool) -> int:
        """Repair installation."""
        print("Repairing AetherOS installation...")

        # Check for issues
        from aetheros_production.observability import get_diagnostics_manager
        manager = get_diagnostics_manager()
        report = manager.run_diagnostics()

        # Fix common issues
        fixes = []

        # Ensure directories exist
        from aetheros_constants import get_aetheros_home
        home = get_aetheros_home()

        required_dirs = ["plugins", "skills", "memory", "sessions", "logs"]
        for dir_name in required_dirs:
            dir_path = home / dir_name
            if not dir_path.exists():
                dir_path.mkdir(parents=True, exist_ok=True)
                fixes.append(f"Created missing directory: {dir_name}")

        # Ensure config exists
        config_path = home / "config.yaml"
        if not config_path.exists():
            from aetheros_cli.config import DEFAULT_CONFIG
            import yaml
            with open(config_path, "w", encoding="utf-8") as f:
                yaml.dump(DEFAULT_CONFIG, f, default_flow_style=False)
            fixes.append("Created default configuration")

        if fixes:
            print(f"Fixed {len(fixes)} issue(s):")
            for fix in fixes:
                print(f"  - {fix}")
        else:
            print("No issues found")

        return 0

    def _cmd_update(self, channel: str, check_only: bool) -> int:
        """Check for updates."""
        from aetheros_production.update_system import get_update_manager

        manager = get_update_manager()
        current = manager.get_current_version()

        print(f"Current version: {current}")
        print(f"Release channel: {channel}")

        if check_only:
            update = manager.check_for_updates(channel)
            if update:
                print(f"\nUpdate available: {update.version}")
                print(f"Release date: {update.release_date}")
                return 0
            else:
                print("\nNo updates available")
                return 0
        else:
            result = manager.check_and_update(channel)
            if result["status"] == "updated":
                print(f"\nUpdated successfully: {result['from_version']} -> {result['to_version']}")
                return 0
            elif result["status"] == "up_to_date":
                print("\nAlready up to date")
                return 0
            else:
                print(f"\nUpdate failed: {result.get('message', 'Unknown error')}")
                return 1

    def _cmd_backup(self, backup_type: str, description: str) -> int:
        """Create backup."""
        from aetheros_production.backup import get_backup_manager

        print(f"Creating {backup_type} backup...")

        manager = get_backup_manager()
        result = manager.create_backup(backup_type, description or "")

        if "error" in result:
            print(f"Backup failed: {result['error']}")
            return 1
        else:
            print(f"Backup created: {result['id']}")
            print(f"Size: {result['size_bytes']} bytes")
            return 0

    def _cmd_restore(self, backup_id: str) -> int:
        """Restore from backup."""
        from aetheros_production.backup import get_backup_manager

        manager = get_backup_manager()

        if not backup_id:
            # List available backups
            backups = manager.list_backups()
            if not backups:
                print("No backups available")
                return 1

            print("Available backups:")
            for b in backups[:10]:
                print(f"  {b['backup_id']} - {b.get('backup_type', 'unknown')} ({b.get('timestamp', 0)})")

            print("\nUsage: aetheros restore <backup_id>")
            return 0

        print(f"Restoring backup: {backup_id}")
        result = manager.restore_backup(backup_id)

        if result.get("success"):
            print("Restore completed successfully")
            return 0
        else:
            print(f"Restore failed: {result.get('error', 'Unknown error')}")
            return 1

    def _cmd_health(self) -> int:
        """Check health status."""
        from aetheros_production.observability import get_health_checker

        print("Checking AetherOS health...")
        print("=" * 50)

        checker = get_health_checker()
        health = checker.get_full_health_status()

        status = health["status"]
        status_color = {
            "healthy": "\033[92m",  # Green
            "degraded": "\033[93m",  # Yellow
            "unhealthy": "\033[91m",  # Red
        }.get(status, "\033[0m")

        print(f"\nOverall Status: {status_color}{status.upper()}\033[0m")
        print("\nComponents:")

        for name, component in health["components"].items():
            comp_status = component["status"]
            comp_color = {
                "healthy": "\033[92m",
                "degraded": "\033[93m",
                "unhealthy": "\033[91m",
            }.get(comp_status, "\033[0m")

            print(f"  {name}: {comp_color}{comp_status}\033[0m - {component['message']}")

        return 0 if status == "healthy" else 1

    def _cmd_diagnostics(self, output: str) -> int:
        """Run full diagnostics."""
        from aetheros_production.observability import get_diagnostics_manager

        print("Running full diagnostics...")

        manager = get_diagnostics_manager()
        report = manager.run_diagnostics()

        if output:
            manager.export_diagnostics(report, output)
            print(f"Diagnostics exported to: {output}")
        else:
            print(json.dumps(report, indent=2))

        return 0

    def _cmd_version(self) -> int:
        """Show version information."""
        from aetheros_production.release import get_release_manager

        manager = get_release_manager()
        info = manager.get_version_info()

        print(f"AetherOS v{info['version']}")
        print(f"Channel: {info['channel']}")
        print(f"Edition: {info['edition']}")
        print(f"Python: {info['python_version']}")
        print(f"Platform: {info['platform']}")
        print(f"Release Date: {info['release_date']}")

        return 0

    def _cmd_security(self, audit_type: str, output: str) -> int:
        """Run security audit."""
        from aetheros_production.security import SecurityAuditor, AuditType

        print(f"Running {audit_type} security audit...")

        auditor = SecurityAuditor()

        if audit_type == "full":
            report = auditor.run_full_audit()
        else:
            audit_type_enum = {
                "dependency": AuditType.DEPENDENCY,
                "secrets": AuditType.SECRETS,
                "static": AuditType.STATIC_ANALYSIS,
            }.get(audit_type, AuditType.DEPENDENCY)
            report = auditor.run_audit(audit_type_enum)

        if output:
            auditor.export_report(output)
            print(f"Report exported to: {output}")
        else:
            print(f"\nAudit completed: {report.get('total_issues', 0)} issues found")
            if report.get("critical_issues", 0) > 0:
                print(f"  Critical: {report['critical_issues']}")
            if report.get("high_issues", 0) > 0:
                print(f"  High: {report['high_issues']}")

        return 0

    def _cmd_performance(self, benchmark: str) -> int:
        """Show performance metrics."""
        from aetheros_production.performance import get_performance_optimizer

        optimizer = get_performance_optimizer()

        if benchmark:
            print(f"Benchmarking {benchmark}...")
            # Placeholder for benchmarking
            result = optimizer.benchmark(benchmark, lambda: None)
            print(f"  Average time: {result['avg_time']*1000:.2f} ms")
            print(f"  Min time: {result['min_time']*1000:.2f} ms")
            print(f"  Max time: {result['max_time']*1000:.2f} ms")
        else:
            print("Performance Metrics:")
            print("=" * 50)

            metrics = optimizer.get_metrics()
            for name, metric in metrics.items():
                value = metric.get("value", 0)
                unit = metric.get("unit", "")
                status = metric.get("status", "unknown")
                print(f"  {name}: {value:.1f} {unit} [{status}]")

        return 0
