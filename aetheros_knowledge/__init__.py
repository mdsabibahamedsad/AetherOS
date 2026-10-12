"""Knowledge OS — persistent knowledge layer for AetherOS.

Knowledge Center, Memory Engine, RAG Studio, Vector DB, Search, Sharing.
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)

_initialized = False


def init_knowledge() -> None:
    global _initialized
    if _initialized:
        return
    logger.info("Initializing Knowledge OS...")
    _initialized = True
    logger.info("Knowledge OS initialized")


__all__ = ["init_knowledge"]
