from __future__ import annotations

import asyncio
import json
import os
import sys
import signal
import time

from aetheros_orchestrator import create_daemon
from aetheros_orchestrator.logging.setup import get_logger


def run_daemon(config_path: str | None = None):
    asyncio.run(_run_daemon_async(config_path))


async def _run_daemon_async(config_path: str | None = None):
    orchestrator = create_daemon(config_path)
    logger = get_logger("daemon")
    logger.info("AetherOS daemon starting")

    stop_event = asyncio.Event()

    def _signal_handler():
        logger.info("Shutdown signal received")
        stop_event.set()

    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _signal_handler)
        except (ValueError, NotImplementedError):
            pass

    try:
        await orchestrator.start()
        logger.info("AetherOS daemon started successfully")
        await stop_event.wait()
    except Exception as e:
        logger.error("Daemon startup failed: %s", str(e))
        sys.exit(1)
    finally:
        logger.info("AetherOS daemon shutting down")
        await orchestrator.stop()
        logger.info("AetherOS daemon stopped")


def list_status(config_path: str | None = None):
    try:
        import urllib.request
        with urllib.request.urlopen("http://127.0.0.1:8765/", timeout=5) as resp:
            data = json.loads(resp.read())
            print("Daemon status:", json.dumps(data, indent=2))
    except Exception as e:
        print("Daemon not reachable:", e)


def show_health(config_path: str | None = None):
    try:
        import urllib.request
        with urllib.request.urlopen("http://127.0.0.1:8765/health", timeout=5) as resp:
            data = json.loads(resp.read())
            print(json.dumps(data, indent=2))
    except Exception as e:
        print("Health check failed:", e)
