"""Main entry point for AetherOS performance benchmarks (Master 71)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Import all benchmark modules to register them
from benchmarks.desktop import startup  # noqa: F401
from benchmarks.agent import runtime  # noqa: F401
from benchmarks.ipc import latency  # noqa: F401
from benchmarks.database import sqlite  # noqa: F401
from benchmarks.browser import automation  # noqa: F401
from benchmarks.memory import retrieval  # noqa: F401
from benchmarks.swarm import coordination  # noqa: F401
from benchmarks.mcp import protocol  # noqa: F401
from benchmarks.cli import startup as cli_startup  # noqa: F401
from benchmarks.load import load_test, memory_leak  # noqa: F401
from benchmarks.web import bundle  # noqa: F401

from benchmarks.core.runner import main as runner_main


def main():
    """Main entry point."""
    return runner_main()


if __name__ == "__main__":
    sys.exit(main())