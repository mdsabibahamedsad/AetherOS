"""AetherOS Daemon — unified entry point for all subsystems."""

from __future__ import annotations

import argparse
import sys

from aetheros_orchestrator.cli.commands import run_daemon, list_status, show_health
from aetheros_orchestrator.logging.setup import get_logger


def main():
    parser = argparse.ArgumentParser(description="AetherOS Daemon — Integration Layer")
    parser.add_argument("action", nargs="?", default="start", choices=["start", "stop", "restart", "status", "health"],
                        help="Action to perform")
    parser.add_argument("--config", "-c", help="Path to config file (JSON)")
    parser.add_argument("--port", "-p", type=int, help="API port override")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    args = parser.parse_args()
    config_path = args.config

    if args.action == "status":
        list_status(config_path)
    elif args.action == "health":
        show_health(config_path)
    elif args.action == "start":
        run_daemon(config_path)
    elif args.action == "restart":
        run_daemon(config_path)
    elif args.action == "stop":
        print("Use SIGINT/SIGTERM to stop the daemon")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
