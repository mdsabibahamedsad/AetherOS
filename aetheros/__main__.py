#!/usr/bin/env python3
"""AetherOS - python -m aetheros entry point."""
import sys
import os

try:
    import aetheros_bootstrap
except ModuleNotFoundError:
    pass

_proj_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if _proj_root not in sys.path:
    sys.path.insert(0, _proj_root)

if __name__ == "__main__":
    from aetheros_cli.main import main
    main()
