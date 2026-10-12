from __future__ import annotations

import os
import sys
import json
import time
import signal
import logging
import threading
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def start_jarvis_server(host: str = "127.0.0.1", port: int = 9789,
                        storage_dir: Optional[str] = None, daemon: bool = False,
                        web: bool = True):
    from core.jarvis.websocket_server import run_jarvis_server
    server = run_jarvis_server(host=host, port=port, storage_dir=storage_dir)

    if web:
        from core.jarvis.websocket_server import start_web_dashboard
        try:
            start_web_dashboard(server.engine, host=host, port=port + 1)
        except Exception as e:
            logger.warning(f"Could not start web dashboard: {e}")

    print(f"\n  Jarvis Engine running at ws://{host}:{port}")
    print(f"  API available at http://{host}:{port}/api/jarvis/health\n")

    def shutdown(sig, frame):
        print("\n  Shutting down Jarvis Engine...")
        server.stop()
        from core.jarvis.startup import shutdown_engine
        shutdown_engine()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    if daemon:
        return server

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        shutdown(None, None)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Jarvis Engine Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind")
    parser.add_argument("--port", type=int, default=9789, help="Port to bind")
    parser.add_argument("--storage", help="Storage directory")
    parser.add_argument("--daemon", action="store_true", help="Run as daemon")
    parser.add_argument("--no-web", action="store_true", help="Disable web dashboard")
    args = parser.parse_args()

    start_jarvis_server(
        host=args.host,
        port=args.port,
        storage_dir=args.storage,
        daemon=args.daemon,
        web=not args.no_web,
    )


if __name__ == "__main__":
    main()
